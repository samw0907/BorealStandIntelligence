# boreal-stand-intelligence/src/b_harvest_detection.py
"""Module B - harvest change detection validated against forest use declarations.

Detects fellings between two Sentinel-2 composite epochs, scores the detections
against forest use declarations by felling type (regeneration, thinning,
salvage), and calibrates the change threshold by an F1 sweep. Produces the
per-stand `inventory_stale` flag consumed by Module A.

Data tiers: Sentinel-2 DERIVE ONLY; forest use declarations and stand
boundaries FETCH; forest mask FETCH.

This file is built step by step:
- B3  compute_change_surfaces  -> dNBR, dNDMI rasters (+ forest mask raster)
- B4  Sentinel-1 log-ratio cross-check
- B5  zonal stats per declaration + F1 threshold sweep
- B6  outputs: inventory_stale flag, mismatch sets, AOI harvest map, report.json
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize

from fi_forest_data.io import attribution_for
from src.indices import nbr, ndmi

# change is defined pre - post, so POSITIVE = index dropped = canopy loss / harvest
_CHANGE_SIGN = "pre_minus_post: positive = vegetation loss"


def _read_composite(path: str | Path):
    """Return (dict of band_name -> float32 array, rasterio profile)."""
    with rasterio.open(path) as src:
        bands = {name: src.read(i + 1).astype("float32") for i, name in enumerate(src.descriptions)}
        profile = src.profile
    return bands, profile


def _write_cog(array: np.ndarray, profile: dict, path: Path, *, description: str, attribution: str,
               tags: dict | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    prof = dict(profile)
    prof.update(driver="COG", count=1, dtype="float32", nodata=np.nan, compress="deflate")
    prof.pop("blockxsize", None)
    prof.pop("blockysize", None)
    prof.pop("tiled", None)
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(array.astype("float32"), 1)
        dst.set_band_description(1, description)
        dst.update_tags(attribution=attribution, **(tags or {}))


def _rasterize_forest_mask(gpkg: str | Path, profile: dict) -> np.ndarray:
    gdf = gpd.read_file(gpkg)
    if gdf.crs is None or gdf.crs.to_epsg() != 3067:
        gdf = gdf.to_crs(3067)
    shapes = ((geom, 1) for geom in gdf.geometry if geom is not None and not geom.is_empty)
    mask = rasterize(
        shapes,
        out_shape=(profile["height"], profile["width"]),
        transform=profile["transform"],
        fill=0,
        dtype="uint8",
        all_touched=False,
    )
    return mask


def compute_change_surfaces(
    pre_tif: str | Path,
    post_tif: str | Path,
    out_dir: str | Path,
    *,
    forestmask_gpkg: str | Path | None = None,
) -> dict:
    """Compute dNBR and dNDMI from the two composites and write them as COGs.

    Change is pre - post: positive means the index fell, i.e. canopy was removed.
    Writes {out_dir}/rasters/{dnbr,dndmi}.tif, optionally a forest_mask.tif, and
    a change_surfaces.meta.json sidecar. Returns paths and summary stats.
    """
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

    forest_mask_path = None
    forest_frac = None
    if forestmask_gpkg is not None:
        fmask = _rasterize_forest_mask(forestmask_gpkg, profile)
        forest_mask_path = str(rasters / "forest_mask.tif")
        _write_cog(fmask.astype("float32"), profile, rasters / "forest_mask.tif",
                   description="forest mask (1 = Metsakeskus metsamaski)",
                   attribution=attribution_for(["metsakeskus"]))
        forest_frac = float(fmask.mean())

    def _stats(a: np.ndarray) -> dict:
        v = a[np.isfinite(a)]
        return {
            "median": round(float(np.median(v)), 4),
            "p1": round(float(np.percentile(v, 1)), 4),
            "p99": round(float(np.percentile(v, 99)), 4),
            "frac_gt_0p2": round(float((v > 0.2).mean()), 4),
            "frac_gt_0p3": round(float((v > 0.3).mean()), 4),
            "valid_frac": round(float(np.isfinite(a).mean()), 4),
        }

    meta = {
        "step": "B3_change_surfaces",
        "pre_tif": str(pre_tif),
        "post_tif": str(post_tif),
        "change_sign": _CHANGE_SIGN,
        "crs": str(profile["crs"]),
        "shape": [int(profile["height"]), int(profile["width"])],
        "dnbr": _stats(dnbr),
        "dndmi": _stats(dndmi),
        "forest_mask": forest_mask_path,
        "forest_fraction_of_aoi": None if forest_frac is None else round(forest_frac, 4),
        "attribution": attr,
        "created": date.today().isoformat(),
    }
    (out_dir / "change_surfaces.meta.json").parent.mkdir(parents=True, exist_ok=True)
    (out_dir / "change_surfaces.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return {
        "dnbr": str(rasters / "dnbr.tif"),
        "dndmi": str(rasters / "dndmi.tif"),
        "forest_mask": forest_mask_path,
        "stats": meta,
    }
