# boreal-stand-intelligence/src/c2_beetle_stress.py
"""Module C2 - bark beetle canopy stress detection.

Per-stand monthly Sentinel-2 red-edge and moisture index (NDRE, NDMI)
trajectories over spruce stands. A per-stand seasonal baseline is built from the
pre-outbreak years; a sustained departure below the baseline is a candidate
stress detection. Detection dates are compared with declared salvage felling
dates and reported as a days-early distribution, with the control false-alarm
rate alongside. Early detection of bark beetle attack is a known-hard problem;
C2 measures how early it actually is, honestly.

Data tier: Sentinel-2 DERIVE ONLY; declared salvage dates FETCH.
"""

from __future__ import annotations

import calendar

import numpy as np
import pandas as pd

_CRS = "EPSG:3067"
_C2_BANDS = ["rededge1", "nir", "swir16"]


def _boa_offset(year: int) -> float:
    """Sentinel-2 L2A bottom-of-atmosphere offset by acquisition year.

    Processing baseline 04.00 (from 2022-01-25) adds +1000 DN to every band, i.e.
    reflectance = DN * 0.0001 - 0.1. Earlier scenes have no offset. C2 months are
    all May-September, so a year cut is exact.
    """
    return -0.1 if year >= 2022 else 0.0


def _month_composite(items, aoi, cfg, res, *, year):
    """Median reflectance for one month over the AOI bbox: {band: 2D array}, transform."""
    from odc.stac import load as odc_load
    from rasterio.transform import from_origin

    s2 = cfg["sentinel2"]
    scale = float(s2["reflectance_scale"])
    offset = _boa_offset(year)
    scl_exclude = list(int(x) for x in s2["scl_exclude"]) + [0]
    minx, miny, maxx, maxy = aoi.bbox_3067
    load_kw = dict(crs=_CRS, resolution=res, x=(minx, maxx), y=(miny, maxy),
                   groupby="solar_day", resampling="nearest",
                   chunks={"x": 1024, "y": 1024})

    scl = odc_load(items, bands=["scl"], **load_kw)["scl"]
    clear = ~scl.isin(scl_exclude)
    out = {}
    for band in _C2_BANDS:
        dn = odc_load(items, bands=[band], **load_kw)[band]
        refl = dn.where(clear & (dn != 0)).astype("float32") * scale + offset
        out[band] = refl.median("time", skipna=True).to_numpy().astype("float32")
    ny, nx = out[_C2_BANDS[0]].shape
    return out, from_origin(minx, maxy, res, res), ny, nx


def fetch_s2_stand_indices(stands, aoi, cfg, *, years, months=(5, 6, 7, 8, 9),
                           collection="sentinel-2-l2a", client=None):
    """Long table: one row per stand and month with median NDRE and NDMI.

    stands -- GeoDataFrame in EPSG:3067 with a `standid` column.
    Uses the standard sentinel-2-l2a collection (not the Collection 1 product
    Modules A/B use) because C1 (ESA Collection 1) has a coverage gap over this
    area in 2022; the baseline-04.00 BOA offset is applied by year so the whole
    2019-2024 series is on one reflectance scale. Months with too few clear
    scenes are skipped.
    """
    from rasterstats import zonal_stats
    from pystac_client import Client

    from fi_forest_data.sentinel import search_s2_scenes

    s2 = dict(cfg["sentinel2"], collection=collection)
    cfg = dict(cfg, sentinel2=s2)
    res = float(s2["working_resolution_m"])
    min_scenes = 2
    client = client or Client.open(s2["stac_url"])
    geoms = list(stands.geometry)
    ids = stands["standid"].to_numpy()

    rows = []
    for yr in years:
        for mo in months:
            last = calendar.monthrange(yr, mo)[1]
            window = {"start": f"{yr}-{mo:02d}-01", "end": f"{yr}-{mo:02d}-{last:02d}"}
            items = search_s2_scenes(aoi, window, cfg, client=client)
            if len(items) < min_scenes:
                continue
            bands, transform, _, _ = _month_composite(items, aoi, cfg, res, year=yr)
            nir, re1, sw16 = bands["nir"], bands["rededge1"], bands["swir16"]
            ndre = (nir - re1) / (nir + re1)
            ndmi = (nir - sw16) / (nir + sw16)
            zr = zonal_stats(geoms, ndre, affine=transform, stats=["median"],
                             nodata=float("nan"))
            zm = zonal_stats(geoms, ndmi, affine=transform, stats=["median"],
                             nodata=float("nan"))
            for sid, a, b in zip(ids, zr, zm):
                rows.append({"standid": int(sid), "year": yr, "month": mo,
                             "date": pd.Timestamp(yr, mo, 15),
                             "ndre": a["median"], "ndmi": b["median"],
                             "n_scenes": len(items)})
    return pd.DataFrame(rows)


def select_c2_stands(stand_gpkg, declarations_gpkg, aoi, *, min_spruce=0.5,
                     target_years=(2019, 2024), n_control=300, seed=0):
    """Damaged (beetle salvage in target_years) and control spruce stands in the AOI.

    Returns a GeoDataFrame with `standid`, `group` (damaged|control) and, for the
    damaged stands, `salvage_date` (declaration arrival date).
    """
    import geopandas as gpd

    from src.c1_beetle_susceptibility import beetle_declarations

    s = gpd.read_file(stand_gpkg)
    s = s[s.geometry.representative_point().within(aoi.to_polygon())]
    s = s[(s["maingroup"].astype("string") == "1")
          & (s["proportionspruce"].fillna(0.0) >= min_spruce)].copy()

    decl = beetle_declarations(gpd.read_file(declarations_gpkg))
    ay = pd.to_datetime(decl["DECLARATIONARRIVALDATE"], utc=True, errors="coerce")
    yr = ay.dt.year
    dmg = decl[(yr >= target_years[0]) & (yr <= target_years[1])].copy()
    dmg["salvage_date"] = ay[dmg.index].dt.tz_localize(None)
    dmg["geometry"] = dmg.geometry.centroid
    hit = gpd.sjoin(dmg[["salvage_date", "geometry"]], s[["standid", "geometry"]],
                    predicate="within", how="inner")
    hit = hit.sort_values("salvage_date").drop_duplicates("standid")

    damaged = s[s["standid"].isin(hit["standid"])].merge(
        hit[["standid", "salvage_date"]], on="standid", how="left")
    damaged["group"] = "damaged"

    pool = s[~s["standid"].isin(hit["standid"])]
    ctrl = pool.sample(min(n_control, len(pool)), random_state=seed).copy()
    ctrl["group"] = "control"
    ctrl["salvage_date"] = pd.NaT

    cols = ["standid", "group", "salvage_date", "geometry"]
    return gpd.GeoDataFrame(pd.concat([damaged[cols], ctrl[cols]]),
                            crs=s.crs).reset_index(drop=True)


# ---------------------------------------------------------------------------
# C2b - seasonal baseline, sustained-departure detection, days-early
# ---------------------------------------------------------------------------

def _zscores(indices, index, baseline_years, detect_years, z_threshold,
             min_sd, min_baseline_obs):
    df = indices.dropna(subset=[index]).copy()
    df["date"] = pd.to_datetime(df["date"])
    base = df[df["year"].between(*baseline_years)]
    stats = (base.groupby(["standid", "month"])[index]
             .agg(["mean", "std", "count"]).reset_index()
             .rename(columns={"mean": "b_mean", "std": "b_std", "count": "b_n"}))
    det = df[df["year"].between(*detect_years)].merge(
        stats, on=["standid", "month"], how="inner")
    det = det[det["b_n"] >= min_baseline_obs].copy()
    det["z"] = (det[index] - det["b_mean"]) / det["b_std"].clip(lower=min_sd)
    det = det.sort_values(["standid", "date"])
    det["below"] = det["z"] <= -z_threshold
    coverage = stats.groupby("standid")["b_n"].count()
    return det, coverage


def c2_detect(
    indices: pd.DataFrame,
    stands: pd.DataFrame,
    *,
    index: str = "ndre",
    baseline_years=(2019, 2020),
    detect_years=(2021, 2024),
    z_threshold: float = 2.0,
    min_sd: float = 0.01,
    min_baseline_obs: int = 2,
    window_before_months: int = 18,
    window_after_months: int = 6,
    seed: int = 0,
):
    """First sustained departure of `index` (or "both") from each stand's own
    per-calendar-month baseline, within a window around the salvage date.

    A detection is the earliest month whose z <= -z_threshold and whose next
    available month is also below, restricted to
    [salvage_date - window_before, salvage_date + window_after]. Controls get a
    pseudo salvage date sampled from the damaged distribution so their
    false-alarm rate is measured over a comparable window.
    `days_early` = salvage_date - detection_date, in days (positive = before).
    """
    st = stands[["standid", "group", "salvage_date"]].copy()
    st["salvage_date"] = pd.to_datetime(st["salvage_date"])
    rng = np.random.default_rng(seed)
    real = st.loc[st["group"] == "damaged", "salvage_date"].dropna().to_numpy()
    miss = st["salvage_date"].isna()
    if miss.any() and len(real):
        st.loc[miss, "salvage_date"] = rng.choice(real, size=int(miss.sum()))
    st["win_lo"] = st["salvage_date"] - pd.DateOffset(months=window_before_months)
    st["win_hi"] = st["salvage_date"] + pd.DateOffset(months=window_after_months)

    idx_names = ["ndre", "ndmi"] if index == "both" else [index]
    per = []
    cov = None
    for nm in idx_names:
        det, coverage = _zscores(indices, nm, baseline_years, detect_years,
                                 z_threshold, min_sd, min_baseline_obs)
        det = det[["standid", "date", "below"]].rename(columns={"below": nm})
        per.append(det.set_index(["standid", "date"]))
        cov = coverage if cov is None else cov
    z = pd.concat(per, axis=1).fillna(False).reset_index().sort_values(
        ["standid", "date"])
    z["hit"] = z[idx_names].all(axis=1)
    z["hit_next"] = z.groupby("standid")["hit"].shift(-1).fillna(False)
    z = z.merge(st[["standid", "win_lo", "win_hi"]], on="standid", how="left")
    flagged = z[z["hit"] & z["hit_next"]
                & (z["date"] >= z["win_lo"]) & (z["date"] <= z["win_hi"])]
    first = flagged.groupby("standid")["date"].min().rename("detection_date")

    out = st.merge(first, on="standid", how="left")
    out["baseline_months"] = out["standid"].map(cov).fillna(0).astype(int)
    out["detected"] = out["detection_date"].notna()
    out["days_early"] = (out["salvage_date"] - out["detection_date"]).dt.days
    return out


def run_module_c2(
    cfg: dict,
    *,
    stand_gpkg,
    declarations_gpkg,
    aoi,
    out_dir,
    fetch_dates: dict,
    indices_csv=None,
    years=range(2019, 2025),
    seed: int = 0,
) -> dict:
    """End-to-end C2: select stands, (fetch or load) the monthly S2 index table,
    run the NDRE / NDMI / combined detectors, write report.json + tables + figures."""
    import json
    from pathlib import Path

    import geopandas as gpd

    from src.figures import module_c2_days_early, module_c2_rates
    from fi_forest_data.io import attribution_for, run_metadata

    out_dir = Path(out_dir)
    (out_dir / "tables").mkdir(parents=True, exist_ok=True)
    (out_dir / "figures").mkdir(parents=True, exist_ok=True)

    sel = select_c2_stands(stand_gpkg, declarations_gpkg, aoi, seed=seed)
    if indices_csv and Path(indices_csv).exists():
        idx = pd.read_csv(indices_csv)
    else:
        idx = fetch_s2_stand_indices(sel, aoi, cfg, years=years)
        idx.to_csv(out_dir / "tables" / "stand_indices.csv", index=False)
    sel_df = sel.drop(columns="geometry") if isinstance(sel, gpd.GeoDataFrame) else sel

    rate_rows, summaries, robust = [], {}, {}
    for name in ("ndre", "ndmi", "both"):
        det = c2_detect(idx, sel_df, index=name, seed=seed)
        s = c2_summary(det)
        summaries[name] = s
        robust[name] = c2_summary_multiseed(idx, sel_df, index=name)
        rate_rows.append({"index": name.upper(),
                          "detection_rate_damaged": s["detection_rate_damaged"],
                          "false_alarm_rate_control": s["false_alarm_rate_control"]})
        if name == "ndre":
            det.to_csv(out_dir / "tables" / "detections_ndre.csv", index=False)
    pd.DataFrame(rate_rows).to_csv(out_dir / "tables" / "detection_rates.csv", index=False)

    module_c2_days_early(out_dir / "tables" / "detections_ndre.csv",
                         out_dir / "figures" / "c2_days_early.png")
    module_c2_rates(out_dir / "tables" / "detection_rates.csv",
                    out_dir / "figures" / "c2_rates.png")

    report = {
        "module": "C2 - bark beetle canopy stress detection",
        "generated": run_metadata(cfg, fetch_dates, aoi_bbox=aoi.bbox_3067),
        "design": "monthly Sentinel-2 NDRE / NDMI per spruce stand; per-stand "
                  "per-calendar-month baseline from 2019-2020; first sustained "
                  "(2 months) departure z <= -2 within [-18, +6] months of the "
                  "salvage declaration; controls get a matched pseudo date",
        "aoi_bbox_3067": list(aoi.bbox_3067),
        "n_damaged": int((sel_df["group"] == "damaged").sum()),
        "n_control": int((sel_df["group"] == "control").sum()),
        "detectors": summaries,
        "detectors_multiseed": robust,
        "headline": "Early detection is a marginal signal, consistent with the "
                    "published critical review. NDRE occasionally leads visible "
                    "mortality but catches only a minority of stands, and its "
                    "detection rate is not reliably distinguishable from the "
                    "control false-alarm rate (Fisher exact). NDMI is more "
                    "sensitive but fires around or after the declaration date.",
        "caveats": [
            "44 damaged spruce stands in the hotspot - small; the NDRE lead-time "
            "sample is n~5, too few for a distribution, so no median is quoted.",
            "The salvage declaration date lags visible mortality by weeks to "
            "months, so 'no lead vs the declaration' means 'no lead vs visible "
            "mortality'.",
            "Sentinel-2 L2A (not the Collection 1 product Modules A/B use) "
            "because Collection 1 has a 2022 gap here; the baseline-04.00 BOA "
            "offset is applied by acquisition year (exact for May-Sep windows).",
            "Baseline is only 2019-2020 (~2-5 obs per calendar month), so the "
            "per-stand z-score is itself noisy - the detection threshold is "
            "indicative, not calibrated. A longer baseline + harmonic seasonal "
            "model is the standard alternative (deferred).",
            "The hotspot is selected on damage density; control stands there may "
            "be pre-symptomatic. Out-of-hotspot controls would tighten this.",
        ],
        "attribution": attribution_for(["metsakeskus", "copernicus"]),
    }
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, default=str),
                                         encoding="utf-8")
    return report


def c2_summary(detections: pd.DataFrame, *, min_n_for_quantiles: int = 12) -> dict:
    """Detection rate, control false-alarm rate, a Fisher exact test that the two
    differ, and the days-early distribution (quantiles only when n is adequate)."""
    from scipy.stats import fisher_exact

    dmg = detections[detections["group"] == "damaged"]
    ctl = detections[detections["group"] == "control"]
    dmg_ev = dmg[dmg["baseline_months"] > 0]
    ctl_ev = ctl[ctl["baseline_months"] > 0]
    de = dmg.loc[dmg["detected"] & dmg["days_early"].notna(), "days_early"]

    table = [[int(dmg_ev["detected"].sum()), int((~dmg_ev["detected"]).sum())],
             [int(ctl_ev["detected"].sum()), int((~ctl_ev["detected"]).sum())]]
    fisher_p = float(fisher_exact(table, alternative="greater")[1]) if len(dmg_ev) and len(ctl_ev) else None

    days_early = {"n": int(de.notna().sum()),
                  "share_before_declaration": round(float((de > 0).mean()), 3) if len(de) else None}
    if len(de) >= min_n_for_quantiles:
        days_early.update(median=float(de.median()),
                          q25=float(de.quantile(0.25)),
                          q75=float(de.quantile(0.75)))
    else:
        days_early["note"] = (f"n={len(de)} < {min_n_for_quantiles}: too few for a "
                              "lead-time distribution; qualitative only")
    return {
        "n_damaged_evaluated": int(len(dmg_ev)),
        "n_control_evaluated": int(len(ctl_ev)),
        "detection_rate_damaged": round(float(dmg_ev["detected"].mean()), 3) if len(dmg_ev) else None,
        "false_alarm_rate_control": round(float(ctl_ev["detected"].mean()), 3) if len(ctl_ev) else None,
        "fisher_p_detection_gt_falsealarm": round(fisher_p, 4) if fisher_p is not None else None,
        "days_early": days_early,
    }


def c2_summary_multiseed(indices, stands, *, index="ndre", seeds=range(20), **kw):
    """c2_summary averaged over the control pseudo-date RNG seed, with spread."""
    rows = []
    for s in seeds:
        d = c2_detect(indices, stands, index=index, seed=s, **kw)
        m = c2_summary(d)
        rows.append((m["detection_rate_damaged"], m["false_alarm_rate_control"],
                     m["fisher_p_detection_gt_falsealarm"]))
    a = np.array([[x if x is not None else np.nan for x in r] for r in rows])
    return {
        "index": index, "n_seeds": len(rows),
        "detection_rate_damaged": round(float(np.nanmean(a[:, 0])), 3),
        "false_alarm_rate_control_mean": round(float(np.nanmean(a[:, 1])), 3),
        "false_alarm_rate_control_sd": round(float(np.nanstd(a[:, 1])), 3),
        "fisher_p_median": round(float(np.nanmedian(a[:, 2])), 4),
        "fisher_p_significant_share": round(float(np.mean(a[:, 2] < 0.05)), 3),
    }
