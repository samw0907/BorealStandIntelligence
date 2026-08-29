# boreal-stand-intelligence/fi_forest_data/io.py
"""Output writing, run metadata and attribution.

Writes cloud-optimised GeoTIFFs with an embedded attribution tag, and assembles
the run_metadata.json record. CC BY 4.0 attribution is required on every output
derived from Metsakeskus, Luke, NLS or SYKE data; the strings live here so they
are consistent across figures and reports.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np
import rasterio

ATTRIBUTION = {
    "metsakeskus": "Contains data from the Finnish Forest Centre, licensed CC BY 4.0",
    "luke": "Contains Natural Resources Institute Finland MS-NFI data, CC BY 4.0",
    "nls": "Contains data from the National Land Survey of Finland, CC BY 4.0",
    "copernicus": "Contains modified Copernicus Sentinel data",
    "fmi": "Contains Finnish Meteorological Institute open data, CC BY 4.0",
    "syke": "Contains data from the Finnish Environment Institute (SYKE), CC BY 4.0",
}

_TRACKED_PACKAGES = (
    "rasterio", "geopandas", "shapely", "pyproj", "numpy", "pandas", "scipy",
    "rasterstats", "pystac-client", "statsmodels", "scikit-learn",
)


def attribution_for(sources: list[str]) -> str:
    """Join the attribution strings for the given source keys, in a stable order."""
    seen = [s for s in ATTRIBUTION if s in set(sources)]
    return " | ".join(ATTRIBUTION[s] for s in seen)


def _git_short_sha() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        return out.stdout.strip() or None
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None


def run_id(when: datetime | None = None) -> str:
    """`{YYYYMMDD}_{HHMMSS}_{git_short_sha}` per the output convention."""
    when = when or datetime.now(timezone.utc)
    sha = _git_short_sha() or "nogit"
    return f"{when:%Y%m%d}_{when:%H%M%S}_{sha}"


def _package_versions() -> dict:
    out = {"python": _python_version()}
    for name in _TRACKED_PACKAGES:
        try:
            out[name] = version(name)
        except PackageNotFoundError:
            out[name] = None
    return out


def _python_version() -> str:
    import platform

    return platform.python_version()


def run_metadata(config: dict, fetch_dates: dict, *, aoi_bbox: tuple | None = None) -> dict:
    """Assemble the run_metadata.json record.

    config      -- the loaded pipeline config (hashed, not stored verbatim)
    fetch_dates -- {source_key: {"fetched": iso-date, "endpoint_version": str, ...}}
    aoi_bbox    -- the EPSG:3067 bbox actually processed
    """
    config_bytes = json.dumps(config, sort_keys=True, default=str).encode("utf-8")
    return {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": run_id(),
        "git_short_sha": _git_short_sha(),
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "aoi_bbox_3067": list(aoi_bbox) if aoi_bbox is not None else None,
        "sources": fetch_dates,
        "packages": _package_versions(),
    }


def write_cog(
    array: np.ndarray,
    profile: dict,
    path: str | Path,
    attribution: str,
    *,
    nodata=None,
    overview_resampling: str = "nearest",
) -> None:
    """Write `array` as a DEFLATE cloud-optimised GeoTIFF with an attribution tag.

    array   -- 2D (single band) or 3D (bands, rows, cols)
    profile -- a rasterio profile carrying at least crs, transform, dtype
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if array.ndim == 2:
        array = array[np.newaxis, :, :]
    count, height, width = array.shape

    prof = dict(profile)
    prof.update(
        driver="COG",
        count=count,
        height=height,
        width=width,
        dtype=array.dtype,
        compress="deflate",
        overview_resampling=overview_resampling,
    )
    if nodata is not None:
        prof["nodata"] = nodata

    with rasterio.open(path, "w", **prof) as dst:
        dst.write(array)
        dst.update_tags(
            attribution=attribution,
            created_utc=datetime.now(timezone.utc).isoformat(),
        )
