# boreal-stand-intelligence/fi_forest_data/sentinel.py
"""Copernicus Sentinel access.

Sentinel-2 L2A from AWS Earth Search, collection sentinel-2-c1-l2a (ESA
Collection 1 - one harmonised processing baseline across the whole archive, so
the DN->reflectance correction is a single rule for every scene). Public COGs,
no credentials. Sentinel-1 GRD comes later (Module B4).

fetch_s2_composite builds a per-pixel median reflectance composite over a date
window: STAC search -> SCL cloud mask -> DN * scale + offset -> median of the
clear observations. All Sentinel use is DERIVE ONLY and Project 1 only.
See docs/DATA_SOURCES.md section 6.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import rasterio
from odc.stac import load as odc_load
from pystac_client import Client
from rasterio.transform import from_origin

from fi_forest_data.io import ATTRIBUTION

CRS = "EPSG:3067"
_SCL_NODATA = 0


def _s2cfg(cfg: dict) -> dict:
    s2 = cfg.get("sentinel2")
    if not isinstance(s2, dict):
        raise KeyError("config has no 'sentinel2' block")
    return s2


def search_s2_scenes(aoi, window: dict, cfg: dict, *, client: Client | None = None) -> list:
    """STAC items for the AOI and window, filtered to < max_cloud_scene_pct cloud."""
    s2 = _s2cfg(cfg)
    client = client or Client.open(s2["stac_url"])
    search = client.search(
        collections=[s2["collection"]],
        bbox=list(aoi.bbox_wgs84()),
        datetime=f"{window['start']}/{window['end']}",
        query={"eo:cloud_cover": {"lt": s2["max_cloud_scene_pct"]}},
    )
    items = list(search.items())
    items.sort(key=lambda it: it.properties["datetime"])
    return items


def _assert_scale_offset(items: list, bands: list, scale: float, offset: float) -> None:
    """Every band asset must declare the expected raster:bands scale/offset."""
    for it in items:
        for band in bands:
            asset = it.assets.get(band)
            if asset is None:
                raise RuntimeError(f"{it.id}: missing asset {band!r}")
            rb = (asset.extra_fields.get("raster:bands") or [{}])[0]
            got_scale = rb.get("scale", 0.0001)
            got_offset = rb.get("offset", 0.0)
            if not (np.isclose(got_scale, scale) and np.isclose(got_offset, offset)):
                raise RuntimeError(
                    f"{it.id} band {band}: raster:bands scale/offset "
                    f"({got_scale}, {got_offset}) != config ({scale}, {offset}). "
                    "Refusing to composite across an unexpected radiometric baseline."
                )


def _cache_paths(cache_dir: Path, window_name: str, aoi_name: str):
    stem = cache_dir / "sentinel2" / f"s2_{window_name}__{aoi_name}"
    return stem.with_suffix(".tif"), stem.with_suffix(".meta.json")


def fetch_s2_composite(
    aoi,
    window_name: str,
    cfg: dict,
    *,
    cache_dir: str | Path = "data/raw",
    force: bool = False,
    client: Client | None = None,
) -> str:
    """Build (or return cached) the median reflectance composite COG for a window.

    window_name -- key into cfg['sentinel2']['composite_windows'] (e.g. 'pre', 'post')
    Returns the path to a multi-band float32 COG in EPSG:3067 at working_resolution_m.
    """
    s2 = _s2cfg(cfg)
    window = s2["composite_windows"][window_name]
    bands = list(s2["bands"])
    scale = float(s2["reflectance_scale"])
    offset = float(s2["reflectance_offset"])
    res = float(s2["working_resolution_m"])
    scl_exclude = set(int(x) for x in s2["scl_exclude"])
    min_scenes = int(s2["min_scenes_per_composite"])
    min_obs = int(s2["min_clear_obs_per_pixel"])

    cache_dir = Path(cache_dir)
    tif, meta = _cache_paths(cache_dir, window_name, aoi.name)
    if tif.exists() and not force:
        return str(tif)

    items = search_s2_scenes(aoi, window, cfg, client=client)
    if len(items) < min_scenes:
        raise RuntimeError(
            f"window {window_name}: {len(items)} scenes < min_scenes_per_composite {min_scenes}"
        )
    _assert_scale_offset(items, bands, scale, offset)

    minx, miny, maxx, maxy = aoi.bbox_3067
    load_kw = dict(
        crs=CRS, resolution=res, x=(minx, maxx), y=(miny, maxy),
        chunks={"x": 1024, "y": 1024}, groupby="solar_day", resampling="nearest",
    )

    # SCL once; clear = not an excluded class and not SCL nodata
    scl = odc_load(items, bands=["scl"], **load_kw)["scl"]
    clear = ~scl.isin(list(scl_exclude) + [_SCL_NODATA])
    n_clear = clear.sum("time").compute()
    keep = (n_clear >= min_obs).to_numpy()
    n_clear_arr = n_clear.to_numpy().astype("int16")

    # band by band to keep memory to one band's time stack at a time
    ny, nx = keep.shape
    arr = np.full((len(bands), ny, nx), np.nan, dtype="float32")
    for bi, band in enumerate(bands):
        dn = odc_load(items, bands=[band], **load_kw)[band]
        refl = dn.where(clear & (dn != 0)).astype("float32") * scale + offset
        med = refl.median("time", skipna=True).to_numpy().astype("float32")
        med[~keep] = np.nan
        arr[bi] = med

    transform = from_origin(minx, maxy, res, res)
    height, width = arr.shape[1], arr.shape[2]
    profile = {
        "driver": "COG", "crs": CRS, "transform": transform,
        "width": width, "height": height, "count": len(bands),
        "dtype": "float32", "nodata": np.nan, "compress": "deflate",
    }
    tif.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(tif, "w", **profile) as dst:
        dst.write(arr)
        for i, band in enumerate(bands, start=1):
            dst.set_band_description(i, band)
        dst.update_tags(
            attribution=ATTRIBUTION["copernicus"] + f" {window['start'][:4]}",
            window=f"{window['start']}/{window['end']}",
            n_scenes=str(len(items)),
        )

    meta.write_text(json.dumps({
        "source": "aws_earthsearch",
        "collection": s2["collection"],
        "stac_url": s2["stac_url"],
        "window_name": window_name,
        "window": window,
        "crs": CRS,
        "resolution_m": res,
        "bands": bands,
        "reflectance_scale": scale,
        "reflectance_offset": offset,
        "scl_exclude": sorted(scl_exclude),
        "min_clear_obs_per_pixel": min_obs,
        "n_scenes": len(items),
        "clear_obs_per_pixel": {
            "min": int(n_clear_arr.min()), "median": int(np.median(n_clear_arr)),
            "max": int(n_clear_arr.max()),
        },
        "scenes": [
            {"id": it.id, "datetime": it.properties["datetime"],
             "cloud_cover": it.properties.get("eo:cloud_cover"),
             "baseline": it.properties.get("s2:processing_baseline")}
            for it in items
        ],
        "fetch_date": date.today().isoformat(),
    }, indent=2), encoding="utf-8")
    return str(tif)
