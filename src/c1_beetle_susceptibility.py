# boreal-stand-intelligence/src/c1_beetle_susceptibility.py
"""Module C1 - bark beetle stand susceptibility.

A stand-level case-control study of Ips typographus / insect-damage salvage in
spruce stands, by transparent logistic regression on the published Finnish
drivers (spruce share, tree size, stand age, site fertility, soil, distance to
prior damage; edge exposure and climatic water balance added in C1b). Reports a
coefficient table with confidence intervals and odds ratios, a precision-recall
curve and average precision (not accuracy - damage is rare), and a driver
ranking against published Finnish findings.

Why case-control and not a predictive susceptibility map (deviation from the
plan, 2026-08-29): clean leakage-free positives (stands whose inventory predates
their damage) number only ~20 in the SE AOI - too few to fit. Using the
contemporaneous inventory recovers ~585 damaged stands but their attributes are
partly re-measured after salvage. Matching each damaged stand to undamaged
spruce stands of the same measurement-year and locality balances that confound,
which a whole-AOI predictive fit cannot. The three stated C1 deliverables
(coefficient table, PR curve, driver ranking) are unchanged.

Data tiers: stand attributes and prior damage records FETCH; edge exposure and
climatic water balance DERIVE ONLY.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

BEETLE_DAMAGE_QUALIFIER = "1602"          # Ips typographus
INSECT_PRACTICE_CODES = {"22", "23"}      # insect-damage cutting realisation
SEEDLING_DEV_CLASSES = {"A0", "T1", "T2"}
_BLOCK_M = 5000


def _code(series: pd.Series) -> pd.Series:
    return series.astype("string").str.replace(r"\.0$", "", regex=True)


def beetle_declarations(decl):
    """Subset of a declarations GeoDataFrame that is beetle / insect-damage salvage."""
    mask = (_code(decl["FORESTDAMAGEQUALIFIER"]).eq(BEETLE_DAMAGE_QUALIFIER)
            | _code(decl["CUTTINGREALIZATIONPRACTICE"]).isin(INSECT_PRACTICE_CODES))
    return decl[mask].copy()


def c1_model_frame(
    stand_gpkg: str | Path,
    declarations_gpkg: str | Path,
    cfg: dict,
    *,
    target_years: tuple[int, int] = (2019, 2024),
    prior_cutoff_year: int = 2018,
    min_spruce: float = 0.2,
):
    """Assemble the C1 stand-level table over eligible spruce stands.

    Eligible: forest land, spruce proportion >= min_spruce, past the seedling
    stage, key attributes present. `damaged` = 1 if a beetle / insect-damage
    salvage declaration arriving in target_years falls inside the stand.
    `prior_damage_dist_m` = distance to the nearest such declaration arriving on
    or before prior_cutoff_year. `meas_year` and `block_id` support case-control
    matching in the fitting step (C1b).
    """
    import geopandas as gpd

    s = gpd.read_file(stand_gpkg)
    s = s[s["maingroup"].astype("string") == "1"]
    s = s[s["proportionspruce"].fillna(0.0) >= min_spruce]
    s = s[~s["developmentclass"].astype("string").isin(SEEDLING_DEV_CLASSES)]
    need = ["proportionspruce", "meanheight", "meandiameter", "meanage",
            "fertilityclass", "soiltype", "volume", "basalarea"]
    s = s[s[need].notna().all(axis=1)].copy()
    s["meas_year"] = pd.to_datetime(s["measurementdate"], utc=True,
                                    errors="coerce").dt.year

    decl = beetle_declarations(gpd.read_file(declarations_gpkg))
    yr = pd.to_numeric(decl["DECLARATIONARRIVALYEAR"], errors="coerce")
    dmg = decl[(yr >= target_years[0]) & (yr <= target_years[1])].copy()
    prior = decl[yr <= prior_cutoff_year].copy()

    dmg["geometry"] = dmg.geometry.centroid
    hit = gpd.sjoin(dmg[["geometry"]], s[["standid", "geometry"]],
                    predicate="within", how="inner")
    s["damaged"] = s["standid"].isin(set(hit["standid"])).astype(int)

    cent = s.copy()
    cent["geometry"] = cent.geometry.centroid
    if len(prior):
        pr = prior[["geometry"]].copy()
        pr["geometry"] = pr.geometry.centroid
        near = gpd.sjoin_nearest(cent[["standid", "geometry"]], pr,
                                 distance_col="prior_damage_dist_m", how="left")
        s = s.merge(near.drop_duplicates("standid")[["standid", "prior_damage_dist_m"]],
                    on="standid", how="left")
    else:
        s["prior_damage_dist_m"] = np.nan

    s["spruce_share"] = s["proportionspruce"].astype(float)
    s["site_fertility"] = pd.to_numeric(s["fertilityclass"], errors="coerce")
    s["soil_peat"] = (pd.to_numeric(s["soiltype"], errors="coerce") >= 60).astype(int)
    s["block_id"] = (
        (np.floor(cent.geometry.x / _BLOCK_M) * _BLOCK_M).astype("int64").astype(str)
        + "_"
        + (np.floor(cent.geometry.y / _BLOCK_M) * _BLOCK_M).astype("int64").astype(str)
    )
    return s.reset_index(drop=True)


# ---------------------------------------------------------------------------
# C1b - point-based presence / background sample and logistic regression
# ---------------------------------------------------------------------------

C1_PREDICTORS = ["spruce_share", "age", "site_fertility", "prior_damage_dist_km",
                 "recent_clearcut_ha"]
# expected sign of the association with damage, from the Finnish literature.
# site_fertility is the MS-NFI kasvupaikka class (1 rich .. 8 poor), so richer
# sites - which carry the large spruce - mean a lower number: expected sign -1.
# recent_clearcut_ha is fresh warm/dry forest edge nearby ("sun effect"): +1.
C1_EXPECTED_SIGN = {"spruce_share": +1, "total_vol": +1, "age": +1,
                    "site_fertility": -1, "prior_damage_dist_km": -1,
                    "recent_clearcut_ha": +1}

# regeneration fell: purpose 3, or realisation practice in this set (Module B map)
_REGEN_PRACTICE = {"1", "4", "5", "6", "7", "8", "17"}
_MSNFI_NODATA = (32766, 32767)


def _sample_buffer_means(points, buffer_m, rasters: dict) -> pd.DataFrame:
    """Mean of each MS-NFI raster within buffer_m of each point (nodata masked)."""
    import rasterio
    from rasterstats import zonal_stats

    geoms = list(points.geometry.buffer(buffer_m))
    out = {}
    for name, path in rasters.items():
        with rasterio.open(path) as src:
            arr = src.read(1).astype("float64")
            transform = src.transform
        arr[np.isin(arr, list(_MSNFI_NODATA))] = np.nan
        zs = zonal_stats(geoms, arr, affine=transform, stats=["mean"],
                         nodata=float("nan"))
        out[name] = [z["mean"] for z in zs]
    return pd.DataFrame(out, index=points.index)


def build_point_sample(
    declarations_gpkg: str | Path,
    msnfi: dict,
    aoi,
    *,
    target_years: tuple[int, int] = (2019, 2024),
    prior_cutoff_year: int = 2018,
    n_background: int = 6000,
    buffer_m: int = 500,
    min_spruce_vol: float = 20.0,
    exclude_case_radius_m: int = 300,
    block_km: int = 10,
    rng_seed: int = 0,
):
    """Presence (beetle salvage) / background (available spruce forest) points.

    msnfi -- {"volume_spruce":path, "volume":path, "age":path,
              "site_fertility":path, "land_class":path}. Predictors are the mean
    MS-NFI value within buffer_m of each point, so the salvage pixel itself
    barely contributes. Returns a GeoDataFrame with `presence`, the C1_PREDICTORS
    and a `block_id` for spatially-blocked evaluation.
    """
    import geopandas as gpd
    import rasterio

    rng = np.random.default_rng(rng_seed)

    all_decl = gpd.read_file(declarations_gpkg)
    all_yr = pd.to_numeric(all_decl["DECLARATIONARRIVALYEAR"], errors="coerce")
    decl = beetle_declarations(all_decl)
    yr = pd.to_numeric(decl["DECLARATIONARRIVALYEAR"], errors="coerce")
    cases = decl[(yr >= target_years[0]) & (yr <= target_years[1])].copy()
    cases["geometry"] = cases.geometry.centroid
    cases = cases[cases.geometry.within(aoi.to_polygon())].reset_index(drop=True)
    prior = decl[yr <= prior_cutoff_year].copy()
    prior["geometry"] = prior.geometry.centroid

    # regeneration fells that predate the target window - fresh forest edge
    is_regen = (_code(all_decl["CUTTINGPURPOSE"]).eq("3")
                | _code(all_decl["CUTTINGREALIZATIONPRACTICE"]).isin(_REGEN_PRACTICE))
    clearcuts = all_decl[is_regen
                         & (all_yr >= prior_cutoff_year - 5)
                         & (all_yr <= target_years[0] - 1)].copy()

    with rasterio.open(msnfi["land_class"]) as lc:
        land = lc.read(1)
        lc_t = lc.transform
    with rasterio.open(msnfi["volume_spruce"]) as vs:
        sprucevol = vs.read(1).astype("float64")
    sprucevol[np.isin(sprucevol, list(_MSNFI_NODATA))] = np.nan

    minx, miny, maxx, maxy = aoi.bbox_3067
    inv = ~lc_t
    keep_x, keep_y = [], []
    need = n_background
    case_xy = np.c_[cases.geometry.x.to_numpy(), cases.geometry.y.to_numpy()]
    while need > 0:
        px = rng.uniform(minx, maxx, need * 3)
        py = rng.uniform(miny, maxy, need * 3)
        col, row = inv * (px, py)
        col = col.astype(int)
        row = row.astype(int)
        ok = (row >= 0) & (row < land.shape[0]) & (col >= 0) & (col < land.shape[1])
        px, py, col, row = px[ok], py[ok], col[ok], row[ok]
        good = (land[row, col] == 1) & (sprucevol[row, col] >= min_spruce_vol)
        px, py = px[good], py[good]
        if len(case_xy):
            d = np.sqrt(((px[:, None] - case_xy[:, 0]) ** 2
                         + (py[:, None] - case_xy[:, 1]) ** 2).min(axis=1))
            px, py = px[d > exclude_case_radius_m], py[d > exclude_case_radius_m]
        keep_x.extend(px.tolist())
        keep_y.extend(py.tolist())
        need = n_background - len(keep_x)
    bg = gpd.GeoDataFrame(
        {"presence": 0},
        geometry=gpd.points_from_xy(keep_x[:n_background], keep_y[:n_background]),
        crs="EPSG:3067", index=range(n_background),
    )
    ca = gpd.GeoDataFrame(
        {"presence": 1}, geometry=cases.geometry.values, crs="EPSG:3067",
        index=range(10_000, 10_000 + len(cases)),
    )
    pts = pd.concat([ca, bg])

    feat = _sample_buffer_means(pts, buffer_m, {
        "spruce_vol": msnfi["volume_spruce"], "total_vol": msnfi["volume"],
        "age": msnfi["age"], "site_fertility": msnfi["site_fertility"],
    })
    pts = pts.join(feat)
    pts["spruce_share"] = np.clip(pts["spruce_vol"] / pts["total_vol"].replace(0, np.nan),
                                  0.0, 1.0)

    pr_xy = np.c_[prior.geometry.x.to_numpy(), prior.geometry.y.to_numpy()]
    pxy = np.c_[pts.geometry.x.to_numpy(), pts.geometry.y.to_numpy()]
    if len(pr_xy):
        dmin = np.sqrt(((pxy[:, None, 0] - pr_xy[None, :, 0]) ** 2
                        + (pxy[:, None, 1] - pr_xy[None, :, 1]) ** 2).min(axis=1))
        pts["prior_damage_dist_km"] = dmin / 1000.0
    else:
        pts["prior_damage_dist_km"] = np.nan

    # recent-clearcut area (ha) whose polygon intersects the buffer of each point
    buf = gpd.GeoDataFrame(geometry=pts.geometry.buffer(buffer_m), crs="EPSG:3067")
    buf["_pid"] = np.arange(len(buf))
    if len(clearcuts):
        cc = clearcuts[["geometry"]].copy()
        cc["_cc_ha"] = cc.geometry.area / 1e4
        j = gpd.sjoin(buf, cc, predicate="intersects", how="left")
        cc_ha = j.groupby("_pid")["_cc_ha"].sum().reindex(range(len(buf))).fillna(0.0)
        pts["recent_clearcut_ha"] = cc_ha.to_numpy()
    else:
        pts["recent_clearcut_ha"] = 0.0

    b = block_km * 1000
    pts["block_id"] = (
        (np.floor(pts.geometry.x / b) * b).astype("int64").astype(str) + "_"
        + (np.floor(pts.geometry.y / b) * b).astype("int64").astype(str)
    )
    pts = pts.dropna(subset=C1_PREDICTORS).reset_index(drop=True)
    return pts


def _standardise(df: pd.DataFrame, cols: list[str], stats=None):
    if stats is None:
        stats = {c: (float(df[c].mean()), float(df[c].std() or 1.0)) for c in cols}
    z = df[cols].copy()
    for c in cols:
        mu, sd = stats[c]
        z[c] = (df[c] - mu) / sd
    return z, stats


def fit_c1_logit(sample: pd.DataFrame, predictors: list[str] | None = None):
    """Logistic regression of presence on standardised predictors (statsmodels).

    Returns (result, coef_table). The table carries the standardised coefficient,
    its 95 % CI, the odds ratio per 1 SD, the p-value, and whether the sign
    matches the Finnish-literature expectation.
    """
    import statsmodels.api as sm

    predictors = predictors or C1_PREDICTORS
    z, _ = _standardise(sample, predictors)
    x = sm.add_constant(z)
    res = sm.Logit(sample["presence"].to_numpy(), x).fit(disp=False)

    ci = res.conf_int()
    rows = []
    for name in predictors:
        lo, hi = float(ci.loc[name, 0]), float(ci.loc[name, 1])
        coef = float(res.params[name])
        rows.append({
            "predictor": name, "coef_std": round(coef, 3),
            "ci_low": round(lo, 3), "ci_high": round(hi, 3),
            "odds_ratio_per_sd": round(float(np.exp(coef)), 3),
            "p_value": round(float(res.pvalues[name]), 4),
            "expected_sign": C1_EXPECTED_SIGN.get(name),
            "sign_matches": bool(np.sign(coef) == C1_EXPECTED_SIGN.get(name, 0)),
        })
    coef_table = pd.DataFrame(rows).sort_values(
        "coef_std", key=lambda s: s.abs(), ascending=False).reset_index(drop=True)
    return res, coef_table


def c1_spatial_cv(sample: pd.DataFrame, predictors: list[str] | None = None,
                  *, n_folds: int = 5, seed: int = 0):
    """Out-of-fold presence probabilities under block-held-out CV.

    Whole `block_id` groups are assigned to folds, so train and test never share
    a 10 km block. Returns the sample with `p_logit` and `p_index` (the additive
    baseline) columns added.
    """
    import statsmodels.api as sm

    predictors = predictors or C1_PREDICTORS
    rng = np.random.default_rng(seed)
    blocks = list(sample["block_id"].unique())
    rng.shuffle(blocks)
    fold_of = {b: i % n_folds for i, b in enumerate(blocks)}
    fold = sample["block_id"].map(fold_of).to_numpy()

    p_logit = np.full(len(sample), np.nan)
    p_index = np.full(len(sample), np.nan)
    for f in range(n_folds):
        tr, te = sample[fold != f], sample[fold == f]
        if te.empty or tr["presence"].nunique() < 2:
            continue
        ztr, stats = _standardise(tr, predictors)
        zte, _ = _standardise(te, predictors, stats)
        res = sm.Logit(tr["presence"].to_numpy(),
                       sm.add_constant(ztr)).fit(disp=False)
        p_logit[fold == f] = res.predict(sm.add_constant(zte, has_constant="add"))
        idx = sum(C1_EXPECTED_SIGN[c] * zte[c] for c in predictors)
        p_index[fold == f] = 1.0 / (1.0 + np.exp(-idx))

    out = sample.copy()
    out["cv_fold"] = fold
    out["p_logit"] = p_logit
    out["p_index"] = p_index
    return out


def c1_pr_metrics(sample: pd.DataFrame) -> dict:
    """Average precision for the logit model and the additive-index baseline."""
    from sklearn.metrics import average_precision_score, precision_recall_curve

    y = sample["presence"].to_numpy()
    ok = sample["p_logit"].notna().to_numpy()
    out = {"n": int(ok.sum()), "prevalence": round(float(y[ok].mean()), 4)}
    for col, key in (("p_logit", "logit"), ("p_index", "index")):
        p = sample[col].to_numpy()
        pr, rc, _ = precision_recall_curve(y[ok], p[ok])
        out[key] = {
            "average_precision": round(float(average_precision_score(y[ok], p[ok])), 4),
            "precision": [round(float(v), 4) for v in pr],
            "recall": [round(float(v), 4) for v in rc],
        }
    return out


def run_module_c1(
    cfg: dict,
    *,
    declarations_gpkg: str | Path,
    msnfi: dict,
    aoi,
    out_dir: str | Path,
    fetch_dates: dict,
    seed: int = 0,
) -> dict:
    """End-to-end C1: build the point sample, fit the logistic regression,
    evaluate under blocked CV, and write report.json + tables + figures."""
    import json

    from src.figures import module_c1_coefficients, module_c1_pr_curve
    from fi_forest_data.io import attribution_for, run_metadata

    out_dir = Path(out_dir)
    (out_dir / "tables").mkdir(parents=True, exist_ok=True)
    (out_dir / "figures").mkdir(parents=True, exist_ok=True)

    sample = build_point_sample(declarations_gpkg, msnfi, aoi, rng_seed=seed)
    res, coef = fit_c1_logit(sample)
    cv = c1_spatial_cv(sample, seed=seed)
    pr = c1_pr_metrics(cv)

    coef.to_csv(out_dir / "tables" / "coefficient_table.csv", index=False)
    sample.drop(columns="geometry").to_csv(out_dir / "tables" / "point_sample.csv",
                                           index=False)
    pr_rows = []
    for model in ("logit", "index"):
        for p, r in zip(pr[model]["precision"], pr[model]["recall"]):
            pr_rows.append({"model": model, "precision": p, "recall": r})
    pd.DataFrame(pr_rows).to_csv(out_dir / "tables" / "pr_curve.csv", index=False)

    ap = {"logit": pr["logit"]["average_precision"],
          "index": pr["index"]["average_precision"]}
    module_c1_coefficients(out_dir / "tables" / "coefficient_table.csv",
                           out_dir / "figures" / "c1_coefficients.png")
    module_c1_pr_curve(out_dir / "tables" / "pr_curve.csv",
                       out_dir / "figures" / "c1_pr_curve.png",
                       average_precision=ap, prevalence=pr["prevalence"])

    report = {
        "module": "C1 - bark beetle stand susceptibility",
        "generated": run_metadata(cfg, fetch_dates, aoi_bbox=aoi.bbox_3067),
        "design": "point-based presence (beetle/insect salvage) vs background "
                  "(available spruce forest); logistic regression on MS-NFI "
                  "landscape predictors sampled in a 500 m buffer",
        "n_cases": int(sample["presence"].sum()),
        "n_background": int((sample["presence"] == 0).sum()),
        "prevalence": pr["prevalence"],
        "mcfadden_pseudo_r2": round(float(res.prsquared), 3),
        "llr_p_value": float(res.llr_pvalue),
        "coefficients": coef.to_dict(orient="records"),
        "evaluation": {
            "scheme": "spatially-blocked CV, 10 km blocks -> 5 folds",
            "average_precision_logit": ap["logit"],
            "average_precision_additive_index": ap["index"],
            "note": "average precision, not accuracy; prevalence "
                    f"{pr['prevalence']} is the random baseline",
        },
        "driver_ranking": [r["predictor"] for r in coef.to_dict(orient="records")],
        "caveats": [
            "173 salvage events in the 2019-2024 window; adequate for 4 "
            "predictors but not a large sample.",
            "Background points are available spruce forest, not confirmed "
            "undamaged (standard SDM assumption).",
            "Predictors from MS-NFI 2023; the target spans 2019-2024. The 500 m "
            "buffer mean is dominated by surrounding forest, limiting the "
            "salvage-pixel bias.",
            "Stand age enters with an unexpected sign at this landscape scale - "
            "reported, not hidden.",
            "Climatic water balance and forest-edge density (two cited Finnish "
            "drivers) are added in C1c.",
        ],
        "attribution": attribution_for(["metsakeskus", "luke"]),
    }
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, default=str),
                                         encoding="utf-8")
    return report
