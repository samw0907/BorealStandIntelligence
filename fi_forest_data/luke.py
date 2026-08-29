# boreal-stand-intelligence/fi_forest_data/luke.py
"""Luke (Natural Resources Institute Finland) data.

MS-NFI (multi-source national forest inventory) rasters: 16 m, EPSG:3067, UInt16,
one whole-Finland GeoTIFF per theme on the Funet mirror. Nodata 32766 (forestry
land without satellite cover) and 32767 (not forestry land or outside country)
have different meanings and must not be collapsed.

    fetch_msnfi(theme, aoi, year=2023) -> str   # path to a windowed COG for the AOI

DTW depth-to-water (fetch_dtw) is scaffold only, used by the companion repo.
Routes confirmed in TASK 00, docs/DATA_SOURCES.md sections 2-3.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import from_bounds

_BASE = "https://www.nic.funet.fi/index/geodata/luke/vmi"
_SUFFIX = {2023: "1923"}          # plot-year span baked into the 2023 product filenames

# friendly name -> Funet theme stem
THEMES = {
    "volume": "tilavuus",
    "volume_pine": "manty",
    "volume_spruce": "kuusi",
    "volume_birch": "koivu",
    "volume_other": "muulp",
    "mean_height": "keskipituus",     # decimetres
    "mean_diameter": "keskilapimitta",  # centimetres
    "basal_area": "ppa",              # m2/ha
    "age": "ika",                     # years
    "land_class": "maaluokka",        # 1 forest land, 2 scrub, ...
    "site_fertility": "kasvupaikka",  # site fertility class 1 (rich) .. 8 (poor)
    "canopy_cover": "latvuspeitto",   # %
}

MSNFI_NODATA = (32766, 32767)


def _theme_url(theme: str, year: int) -> str:
    if theme not in THEMES:
        raise KeyError(f"unknown MS-NFI theme {theme!r}; known: {sorted(THEMES)}")
    if year not in _SUFFIX:
        raise KeyError(f"no MS-NFI filename suffix recorded for year {year}")
    return f"{_BASE}/{year}/{THEMES[theme]}_vmi1x_{_SUFFIX[year]}.tif"


def fetch_msnfi(
    theme: str,
    aoi,
    *,
    year: int = 2023,
    cache_dir: str | Path = "data/raw",
    force: bool = False,
) -> str:
    """Window the whole-Finland MS-NFI theme raster to the AOI and cache it as a COG.

    The two nodata codes are preserved (written as 32767 nodata, the 32766 cells
    left in place); callers mask both. Returns the local COG path.
    """
    cache_dir = Path(cache_dir)
    out = cache_dir / "luke" / f"msnfi_{theme}_{year}__{aoi.name}.tif"
    meta = out.with_suffix(".meta.json")
    if out.exists() and not force:
        return str(out)

    url = _theme_url(theme, year)
    minx, miny, maxx, maxy = aoi.bbox_3067
    with rasterio.open(f"/vsicurl/{url}") as src:
        win = from_bounds(minx, miny, maxx, maxy, transform=src.transform)
        arr = src.read(1, window=win)
        wt = src.window_transform(win)
        src_nodata = src.nodata

    profile = {
        "driver": "COG", "crs": "EPSG:3067", "transform": wt,
        "width": arr.shape[1], "height": arr.shape[0], "count": 1,
        "dtype": "uint16", "nodata": 32767, "compress": "deflate",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out, "w", **profile) as dst:
        dst.write(arr, 1)
        dst.update_tags(
            attribution="Contains Natural Resources Institute Finland MS-NFI data, CC BY 4.0",
            theme=theme, source_url=url, year=str(year),
        )

    valid = arr[~np.isin(arr, MSNFI_NODATA)]
    meta.write_text(json.dumps({
        "theme": theme, "funet_stem": THEMES[theme], "year": year,
        "source_url": url, "crs": "EPSG:3067", "resolution_m": 16,
        "source_nodata": src_nodata, "nodata_codes": list(MSNFI_NODATA),
        "aoi": aoi.name, "aoi_bbox_3067": [minx, miny, maxx, maxy],
        "shape": list(arr.shape),
        "valid_pixel_stats": {
            "n": int(valid.size),
            "min": int(valid.min()) if valid.size else None,
            "median": float(np.median(valid)) if valid.size else None,
            "max": int(valid.max()) if valid.size else None,
        },
        "fetch_date": date.today().isoformat(),
    }, indent=2), encoding="utf-8")
    return str(out)


def fetch_dtw(threshold_ha: float, aoi):  # pragma: no cover - companion repo
    raise NotImplementedError("DTW fetch lives in the regenerative-harvest-planning repo")
