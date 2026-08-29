# boreal-stand-intelligence/src/b_harvest_detection.py
"""Module B - harvest change detection validated against forest use declarations.

Detects fellings between two Sentinel-2 composite epochs, scores the detections
against forest use declarations by felling type (regeneration, thinning,
salvage), and calibrates the change threshold by an F1 sweep. Produces the
per-stand `inventory_stale` flag consumed by Module A.

Data tiers: Sentinel-2 DERIVE ONLY; forest use declarations and stand
boundaries FETCH; forest mask FETCH.

Built step by step:
- B3  compute_change_surfaces  -> dNBR, dNDMI rasters (+ forest mask raster)
- B5  build_evaluation_frame + threshold_sweep  -> precision/recall/F1
- B6  outputs: inventory_stale flag, mismatch sets, AOI harvest map, report.json

Key honesty point (B5): a forest use declaration is a *permit* to cut, not a
record that the cut happened or when. So scoring uses two cohorts of the same
declarations:
- full register:        all declarations in the arrival window, register as-is
- executed-in-window:   declarations filed early enough to be cut before the post
                        image (a first-principles temporal filter)
The gap between the two recalls quantifies register noise vs sensor performance.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize

from fi_forest_data.io import attribution_for
from src.indices import ndmi, nbr

_CHANGE_SIGN = "pre_minus_post: positive = vegetation loss"

# forest use declaration coded values -> Module B felling class
# CuttingPurposeType: 1/2 thinning, 3 regeneration, 6 forest-damage (salvage)
# CuttingRealizationPracticeType: 20-25 = storm/insect/other damage fellings
_REGEN_PRACTICE = {1, 4, 5, 6, 7, 8, 17}
_THIN_PRACTICE = {2, 3, 12}
_SALVAGE_PRACTICE = {20, 21, 22, 23, 24, 25}

AREA_CLASSES_HA = [(0.5, 1), (1, 2), (2, 5), (5, 10), (10, 1e6)]


def felling_class(purpose, practice) -> str:
    """Map CUTTINGPURPOSE / CUTTINGREALIZATIONPRACTICE to regeneration|thinning|salvage|other."""
    if purpose == 6 or practice in _SALVAGE_PRACTICE:
        return "salvage"
    if purpose == 3 or practice in _REGEN_PRACTICE:
        return "regeneration"
    if purpose in (1, 2) or practice in _THIN_PRACTICE:
        return "thinning"
    return "other"


def area_class(area_ha: float) -> str:
    for lo, hi in AREA_CLASSES_HA:
        if lo <= area_ha < hi:
            return f"{lo:g}-{hi:g}ha" if hi < 1e5 else f">{lo:g}ha"
    return "<0.5ha"


# ---------------------------------------------------------------------------
# B3 - change surfaces
# ---------------------------------------------------------------------------

def _read_composite(path: str | Path):
    with rasterio.open(path) as src:
        bands = {name: src.read(i + 1).astype("float32") for i, name in enumerate(src.descriptions)}
        profile = src.profile
    return bands, profile


def _write_cog(array, profile, path: Path, *, description, attribution, tags=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    prof = dict(profile)
    prof.update(driver="COG", count=1, dtype="float32", nodata=np.nan, compress="deflate")
    for k in ("blockxsize", "blockysize", "tiled"):
        prof.pop(k, None)
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(array.astype("float32"), 1)
        dst.set_band_description(1, description)
        dst.update_tags(attribution=attribution, **(tags or {}))


def _rasterize_forest_mask(gpkg, profile) -> np.ndarray:
    gdf = gpd.read_file(gpkg)
    if gdf.crs is None or gdf.crs.to_epsg() != 3067:
        gdf = gdf.to_crs(3067)
    shapes = ((g, 1) for g in gdf.geometry if g is not None and not g.is_empty)
    return rasterize(shapes, out_shape=(profile["height"], profile["width"]),
                     transform=profile["transform"], fill=0, dtype="uint8", all_touched=False)


def compute_change_surfaces(pre_tif, post_tif, out_dir, *, forestmask_gpkg=None) -> dict:
    """dNBR and dNDMI (pre - post; positive = canopy loss) as COGs, plus a forest mask raster."""
    out_dir = Path(out_dir)
    rasters = out_dir / "rasters"
    pre, profile = _read_composite(pre_tif)
    post, _ = _read_composite(post_tif)

    attr = attribution_for(["copernicus"])
    dnbr = nbr(pre["nir"], pre["swir22"]) - nbr(post["nir"], post["swir22"])
    dndmi = ndmi(pre["nir"], pre["swir16"]) - ndmi(post["nir"], post["swir16"])

    _write_cog(dnbr, profile, rasters / "dnbr.tif",
               description="dNBR (pre-post); positive = vegetation loss",
               attribution=attr, tags={"change_sign": _CHANGE_SIGN})
    _write_cog(dndmi, profile, rasters / "dndmi.tif",
               description="dNDMI (pre-post); positive = moisture/canopy loss",
               attribution=attr, tags={"change_sign": _CHANGE_SIGN})

    forest_mask_path, forest_frac = None, None
    if forestmask_gpkg is not None:
        fmask = _rasterize_forest_mask(forestmask_gpkg, profile)
        forest_mask_path = str(rasters / "forest_mask.tif")
        _write_cog(fmask.astype("float32"), profile, rasters / "forest_mask.tif",
                   description="forest mask (1 = Metsakeskus metsamaski)",
                   attribution=attribution_for(["metsakeskus"]))
        forest_frac = float(fmask.mean())

    def _stats(a):
        v = a[np.isfinite(a)]
        return {"median": round(float(np.median(v)), 4),
                "p1": round(float(np.percentile(v, 1)), 4),
                "p99": round(float(np.percentile(v, 99)), 4),
                "frac_gt_0p2": round(float((v > 0.2).mean()), 4),
                "frac_gt_0p3": round(float((v > 0.3).mean()), 4),
                "valid_frac": round(float(np.isfinite(a).mean()), 4)}

    meta = {"step": "B3_change_surfaces", "pre_tif": str(pre_tif), "post_tif": str(post_tif),
            "change_sign": _CHANGE_SIGN, "crs": str(profile["crs"]),
            "shape": [int(profile["height"]), int(profile["width"])],
            "dnbr": _stats(dnbr), "dndmi": _stats(dndmi), "forest_mask": forest_mask_path,
            "forest_fraction_of_aoi": None if forest_frac is None else round(forest_frac, 4),
            "attribution": attr, "created": date.today().isoformat()}
    (out_dir / "change_surfaces.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"dnbr": str(rasters / "dnbr.tif"), "dndmi": str(rasters / "dndmi.tif"),
            "forest_mask": forest_mask_path, "stats": meta}


# ---------------------------------------------------------------------------
# B5 - zonal change per declaration + threshold sweep
# ---------------------------------------------------------------------------

def zonal_mean(gdf: gpd.GeoDataFrame, change_tif: str | Path):
    """Mean and valid-pixel count of `change_tif` per feature, in gdf order.

    Each feature is scored independently (correct where polygons overlap - which
    declaration polygons do). Pixels are included when their centroid falls in the
    polygon (all_touched=False). NaN is excluded from both the mean and the count.
    """
    from rasterstats import zonal_stats

    with rasterio.open(change_tif) as src:
        arr = src.read(1)
        transform = src.transform
    stats = zonal_stats(list(gdf.geometry), arr, affine=transform,
                        stats=["mean", "count"], nodata=np.nan, all_touched=False)
    means = np.array([s["mean"] if s["mean"] is not None else np.nan for s in stats], dtype="float32")
    counts = np.array([s["count"] for s in stats], dtype="int32")
    return means, counts


def _load_declarations(declarations_gpkg) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(declarations_gpkg, columns=[
        "FORESTUSEDECLARATIONNUMBER", "CUTTINGPURPOSE", "CUTTINGREALIZATIONPRACTICE",
        "FORESTDAMAGEQUALIFIER", "DECLARATIONARRIVALDATE", "AREA", "geometry"])
    if gdf.crs is None or gdf.crs.to_epsg() != 3067:
        gdf = gdf.to_crs(3067)
    gdf["arrival"] = pd.to_datetime(gdf["DECLARATIONARRIVALDATE"], errors="coerce", utc=True)
    gdf["felling_class"] = [felling_class(p, pr) for p, pr in
                            zip(gdf["CUTTINGPURPOSE"], gdf["CUTTINGREALIZATIONPRACTICE"])]
    return gdf


def build_evaluation_frame(declarations_gpkg, stands_gpkg, change_tif, cfg: dict) -> pd.DataFrame:
    """Assemble the B5 scoring frame: scored declarations (positives, both cohorts) +
    a random sample of non-declared stands (negatives), each with its zonal change value.
    """
    b = cfg["module_b_harvest_detection"]
    min_area = float(b["min_stand_area_ha"])
    min_pix = int(b["min_valid_pixels"])
    types = list(b["felling_types_scored"])
    gt = b["ground_truth"]
    full = gt["full_register_arrival"]
    exe = gt["executed_in_window_arrival"]

    decl = _load_declarations(declarations_gpkg)
    in_full = decl["arrival"].between(
        pd.Timestamp(full["start"], tz="UTC"), pd.Timestamp(full["end"], tz="UTC"), inclusive="left")
    pos = decl[in_full & (decl["AREA"] >= min_area) & decl["felling_class"].isin(types)].copy()
    pos["dnbr"], pos["npix"] = zonal_mean(pos, change_tif)
    pos = pos[pos["npix"] >= min_pix].copy()
    pos["cohort_executed"] = pos["arrival"].between(
        pd.Timestamp(exe["start"], tz="UTC"), pd.Timestamp(exe["end"], tz="UTC"), inclusive="left")
    pos["area_class"] = pos["AREA"].map(area_class)
    pos["unit"] = "declaration"

    # negatives: stands with no declaration overlap in the full-register window
    stands = gpd.read_file(stands_gpkg, columns=["standid", "area", "geometry"])
    if stands.crs is None or stands.crs.to_epsg() != 3067:
        stands = stands.to_crs(3067)
    stands = stands[stands["area"] >= min_area].reset_index(drop=True)
    joined = gpd.sjoin(stands, pos[["geometry"]], how="left", predicate="intersects")
    non_declared_idx = sorted(set(joined[joined["index_right"].isna()].index))
    n_non_declared = len(non_declared_idx)
    n_sample = min(int(b["negative_control_n"]), n_non_declared)
    neg = stands.loc[non_declared_idx].sample(n_sample, random_state=1).reset_index(drop=True)
    neg["dnbr"], neg["npix"] = zonal_mean(neg, change_tif)
    neg = neg[neg["npix"] >= min_pix].copy()
    neg["felling_class"] = "none"
    neg["cohort_executed"] = False
    neg["AREA"] = neg["area"]
    neg["area_class"] = neg["AREA"].map(area_class)
    neg["unit"] = "negative_control"
    neg["n_non_declared_total"] = n_non_declared  # for FP scaling

    cols = ["unit", "felling_class", "cohort_executed", "AREA", "area_class", "dnbr", "npix"]
    frame = pd.concat([pos[cols], neg[cols + ["n_non_declared_total"]]], ignore_index=True)
    frame.attrs["n_non_declared_total"] = n_non_declared
    frame.attrs["n_negative_sample"] = int((frame["unit"] == "negative_control").sum())
    return frame


def threshold_sweep(frame: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Sweep the change threshold; precision/recall/F1 overall, by felling type and area class.

    Positives are declarations; false positives are estimated from the non-declared
    stand sample, scaled to the full non-declared population.
    """
    b = cfg["module_b_harvest_detection"]
    sw = b["threshold_sweep"]
    thresholds = np.round(np.arange(sw["min"], sw["max"] + 1e-9, sw["step"]), 4)
    types = list(b["felling_types_scored"])

    neg = frame[frame["unit"] == "negative_control"]
    n_neg_sample = max(len(neg), 1)
    n_neg_total = int(frame.attrs.get("n_non_declared_total", n_neg_sample))

    rows = []
    for coh_name, coh_mask in (("full_register", frame["cohort_executed"].notna()),
                               ("executed_in_window", frame["cohort_executed"] == True)):  # noqa: E712
        pos = frame[(frame["unit"] == "declaration") & coh_mask]
        for t in thresholds:
            fp_rate = float((neg["dnbr"] > t).mean())
            fp_est = fp_rate * n_neg_total

            def _pr(sub, fp):
                tp = int((sub["dnbr"] > t).sum())
                n = len(sub)
                recall = tp / n if n else np.nan
                precision = tp / (tp + fp) if (tp + fp) else np.nan
                f1 = (2 * precision * recall / (precision + recall)
                      if precision and recall and (precision + recall) else 0.0)
                return dict(tp=tp, n=n, precision=round(precision, 4) if n else None,
                            recall=round(recall, 4) if n else None, f1=round(f1, 4))

            rows.append(dict(cohort=coh_name, threshold=float(t), group="overall",
                             fp_rate_neg_control=round(fp_rate, 5), fp_estimated=round(fp_est, 1),
                             **_pr(pos, fp_est)))
            for ft in types:
                ftp = pos[pos["felling_class"] == ft]
                rows.append(dict(cohort=coh_name, threshold=float(t), group=f"type:{ft}",
                                 fp_rate_neg_control=round(fp_rate, 5), fp_estimated=round(fp_est, 1),
                                 **_pr(ftp, fp_est)))
                for ac in sorted(ftp["area_class"].unique()):
                    rows.append(dict(cohort=coh_name, threshold=float(t), group=f"area:{ft}:{ac}",
                                     fp_rate_neg_control=round(fp_rate, 5), fp_estimated=round(fp_est, 1),
                                     **_pr(ftp[ftp["area_class"] == ac], fp_est)))
    return pd.DataFrame(rows)


def run_b5(declarations_gpkg, stands_gpkg, change_tif, out_dir, cfg: dict) -> dict:
    """Build the evaluation frame, sweep the threshold, write sweep CSV + summary JSON."""
    out_dir = Path(out_dir)
    frame = build_evaluation_frame(declarations_gpkg, stands_gpkg, change_tif, cfg)
    sweep = threshold_sweep(frame, cfg)

    (out_dir / "tables").mkdir(parents=True, exist_ok=True)
    sweep.to_csv(out_dir / "tables" / "threshold_sweep.csv", index=False)
    frame.drop(columns=[c for c in ("n_non_declared_total",) if c in frame]).to_csv(
        out_dir / "tables" / "evaluation_frame.csv", index=False)

    types = list(cfg["module_b_harvest_detection"]["felling_types_scored"])

    def _row(cohort, group, thr):
        r = sweep[(sweep["cohort"] == cohort) & (sweep["group"] == group)
                  & np.isclose(sweep["threshold"], thr)]
        return None if r.empty else {k: (None if pd.isna(r.iloc[0][k]) else float(r.iloc[0][k]))
                                     for k in ("precision", "recall", "f1", "tp", "n")}

    # a threshold is calibrated PER felling type on the executed-in-window cohort,
    # because clearcut and thinning have very different detectability. Two views:
    #  - max F1 (can drift toward the noise floor when precision degrades slowly)
    #  - the threshold that first reaches precision >= 0.90 (operational: few false alarms)
    prec_floor = 0.90
    per_type = {}
    for ft in types:
        d = sweep[(sweep["cohort"] == "executed_in_window")
                  & (sweep["group"] == f"type:{ft}")].sort_values("threshold")
        bt = float(d.loc[d["f1"].idxmax(), "threshold"]) if d["f1"].notna().any() else None
        ok = d[d["precision"].fillna(0) >= prec_floor]
        pt = float(ok["threshold"].min()) if not ok.empty else None
        per_type[ft] = {
            "max_f1": {
                "threshold": bt,
                "executed_in_window": _row("executed_in_window", f"type:{ft}", bt) if bt is not None else None,
                "full_register": _row("full_register", f"type:{ft}", bt) if bt is not None else None,
            },
            f"precision_ge_{prec_floor:g}": {
                "threshold": pt,
                "executed_in_window": _row("executed_in_window", f"type:{ft}", pt) if pt is not None else None,
                "full_register": _row("full_register", f"type:{ft}", pt) if pt is not None else None,
            },
        }

    # recall by stand area class, restricted to regeneration (where detection works),
    # at regeneration's own optimal threshold
    regen_thr = per_type.get("regeneration", {}).get("max_f1", {}).get("threshold")
    area_recall = {}
    if regen_thr is not None:
        for r in sweep[(sweep["cohort"] == "executed_in_window")
                       & sweep["group"].str.startswith("area:regeneration:")
                       & np.isclose(sweep["threshold"], regen_thr)].itertuples():
            area_recall[r.group.split(":", 2)[2]] = {
                "recall": None if pd.isna(r.recall) else float(r.recall), "n": int(r.n)}

    summary = {
        "step": "B5_threshold_sweep",
        "change_tif": str(change_tif),
        "n_positives_full": int((frame["unit"] == "declaration").sum()),
        "n_positives_executed_in_window": int(((frame["unit"] == "declaration")
                                               & frame["cohort_executed"]).sum()),
        "n_negative_sample": int(frame.attrs["n_negative_sample"]),
        "n_non_declared_total": int(frame.attrs["n_non_declared_total"]),
        "per_type": per_type,
        "area_class_recall_regeneration": area_recall,
        "note": ("thresholds are calibrated per felling type; a declaration is a permit, so "
                 "recall is reported for both the full register and the executed-in-window cohort"),
        "created": date.today().isoformat(),
    }
    (out_dir / "b5_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {"sweep_csv": str(out_dir / "tables" / "threshold_sweep.csv"),
            "summary": summary, "frame": frame, "sweep": sweep}


# ---------------------------------------------------------------------------
# B6 - deliverables: inventory_stale flag, mismatch sets, harvest map, report
# ---------------------------------------------------------------------------

def _load_stands(stands_gpkg):
    g = gpd.read_file(stands_gpkg, columns=[
        "standid", "area", "maintreespecies", "developmentclass",
        "measurementdate", "treestanddatasource", "volume", "geometry"])
    if g.crs is None or g.crs.to_epsg() != 3067:
        g = g.to_crs(3067)
    g["measurementdate"] = pd.to_datetime(g["measurementdate"], errors="coerce", utc=True)
    return g


def flag_inventory_stale(stands_gpkg, change_tif, cfg, *, regen_threshold, post_end="2024-06-01"):
    """Per-stand `inventory_stale`: a detected canopy loss postdating the last inventory scan.

    inventory_stale = zonal dNBR over the stand exceeds the regeneration threshold
    AND the stand's measurementdate is before the post composite. Such a stand's
    attributes were measured before the cut, so they are modelled, not observed -
    Module A must handle it separately.
    """
    g = _load_stands(stands_gpkg).reset_index(drop=True)
    g["dnbr"], g["npix"] = zonal_mean(g, change_tif)
    post = pd.Timestamp(post_end, tz="UTC")
    detected = g["dnbr"] > regen_threshold
    pre_scan = g["measurementdate"] < post
    g["inventory_stale"] = (detected & pre_scan).fillna(False)
    g["stale_reason"] = np.where(
        g["inventory_stale"], "detected canopy loss postdates measurementdate", "")
    return g[["standid", "area", "measurementdate", "treestanddatasource",
              "dnbr", "npix", "inventory_stale", "stale_reason", "geometry"]]


def mismatch_sets(stands_gpkg, declarations_gpkg, change_tif, cfg, *, regen_threshold):
    """declared-but-not-detected and detected-but-not-declared, over the full AOI.

    Unit is the stand polygon. A stand is 'declared' if a scored declaration in the
    full-register window overlaps it; 'detected' if its zonal dNBR exceeds the
    regeneration threshold. Returns two GeoDataFrames plus counts/areas.
    """
    b = cfg["module_b_harvest_detection"]
    min_area = float(b["min_stand_area_ha"])
    gt = b["ground_truth"]["full_register_arrival"]

    stands = _load_stands(stands_gpkg)
    stands = stands[stands["area"] >= min_area].reset_index(drop=True)
    stands["dnbr"], stands["npix"] = zonal_mean(stands, change_tif)
    stands = stands[stands["npix"] >= int(b["min_valid_pixels"])].copy()
    stands["detected"] = stands["dnbr"] > regen_threshold

    decl = _load_declarations(declarations_gpkg)
    decl = decl[decl["arrival"].between(
        pd.Timestamp(gt["start"], tz="UTC"), pd.Timestamp(gt["end"], tz="UTC"), inclusive="left")
        & decl["felling_class"].isin(list(b["felling_types_scored"]))]
    # a stand's declaration class = the strongest overlapping (regeneration > salvage > thinning)
    order = {"thinning": 1, "salvage": 2, "regeneration": 3}
    j = gpd.sjoin(stands[["standid", "geometry"]], decl[["felling_class", "geometry"]],
                  how="inner", predicate="intersects")
    j["rank"] = j["felling_class"].map(order)
    best = (j.sort_values("rank").drop_duplicates("standid", keep="last")[["standid", "felling_class"]]
            .rename(columns={"felling_class": "declared_class"}))
    stands = stands.merge(best, on="standid", how="left")
    stands["declared"] = stands["declared_class"].notna()

    dnd = stands[stands["declared"] & ~stands["detected"]]        # declared, not detected
    dtn = stands[stands["detected"] & ~stands["declared"]]        # detected, not declared

    def _summ(sub, by=None):
        out = {"n": int(len(sub)), "area_ha": round(float(sub["area"].sum()), 1)}
        if by is not None and len(sub):
            out["by_" + by] = {k: {"n": int(v), "area_ha": round(float(sub.loc[sub[by] == k, "area"].sum()), 1)}
                               for k, v in sub[by].value_counts().items()}
        return out

    return {
        "declared_not_detected": dnd, "detected_not_declared": dtn,
        "n_stands_scored": int(len(stands)),
        "declared_not_detected_summary": _summ(dnd, "declared_class"),
        "detected_not_declared_summary": _summ(dtn),
        "detected_total": int(stands["detected"].sum()),
        "declared_total": int(stands["declared"].sum()),
    }


def write_module_b_report(out_dir, *, b5_summary, mismatch, cfg, fetch_dates,
                          inventory_stale_summary=None):
    """report.json (headline numbers) + run_metadata.json for Module B."""
    from fi_forest_data.io import run_metadata

    out_dir = Path(out_dir)
    b = cfg["module_b_harvest_detection"]
    area_rec = b5_summary.get("area_class_recall_regeneration", {})
    # minimum reliably detectable clearcut size = smallest class with recall >= 0.75
    min_size = None
    for k, v in area_rec.items():
        if v.get("recall") is not None and v["recall"] >= 0.75:
            min_size = k
            break

    report = {
        "module": "B_harvest_detection",
        "change_metric": b["change_metric"],
        "per_type_calibration": b5_summary["per_type"],
        "cohort_note": b5_summary["note"],
        "register_vs_executed_recall": {
            "regeneration_full_register":
                b5_summary["per_type"]["regeneration"]["max_f1"]["full_register"]["recall"],
            "regeneration_executed_in_window":
                b5_summary["per_type"]["regeneration"]["max_f1"]["executed_in_window"]["recall"],
        },
        "area_class_recall_regeneration": area_rec,
        "minimum_reliably_detectable_clearcut": min_size,
        "thinning": "not reliably detectable with two-epoch optical dNBR (see MODULE_B_NOTES.md 4.2)",
        "salvage": "partial only; see MODULE_B_NOTES.md 4.3",
        "declared_not_detected_full_register": {
            **mismatch["declared_not_detected_summary"],
            "meaning": ("stands with a felling permit on file 2019-2024 that the 2021->2024 change "
                        "surface does not confirm as cut. Dominated by undetectable thinnings and "
                        "permits exercised outside the observation window. NOT a count of missed "
                        "detections - the missed-detection figure is 1 - recall on the "
                        "executed-in-window cohort (regeneration ~21%)."),
        },
        "detected_not_declared": {
            **mismatch["detected_not_declared_summary"],
            "meaning": ("stands showing strong canopy loss with no felling permit 2019-2024: "
                        "undeclared cutting, natural disturbance, or noise. Small - undeclared "
                        "cutting appears rare."),
        },
        "stands_scored": mismatch["n_stands_scored"],
        "inventory_stale": inventory_stale_summary,
        "created": date.today().isoformat(),
    }
    (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out_dir / "run_metadata.json").write_text(
        json.dumps(run_metadata(cfg, fetch_dates), indent=2), encoding="utf-8")
    return report
