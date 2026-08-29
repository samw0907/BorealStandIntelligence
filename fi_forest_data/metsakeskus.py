# boreal-stand-intelligence/fi_forest_data/metsakeskus.py
"""Metsakeskus (Finnish Forest Centre) open forest and nature data.

GeoServer WFS 2.0.0, one feature type per URL path, EPSG:3067 native. This module
fetches vector layers (stands, forest use declarations, forest mask, habitat, grid
cells) as GeoDataFrames, with startIndex/count paging and a local GeoPackage cache
in data/raw/. Each fetch writes a .meta.json sidecar recording the endpoint,
typeName, WFS version and fetch date.

Routes and field notes: docs/DATA_SOURCES.md section 1. Coded values decode via
the KOOD V35 workbook (see docs/DATA_SOURCES.md).
"""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

import geopandas as gpd
import requests

BASE = "https://avoin.metsakeskus.fi/rajapinnat"
WFS_VERSION = "2.0.0"
CRS = "EPSG:3067"
_SRS_URI = "urn:ogc:def:crs:EPSG::3067"
_PAGE = 10000  # GeoServer CountDefault for this service
_TIMEOUT = 180
_RETRIES = 3
_UA = "finnish-forest-analytics/0.1 (portfolio pipeline; contact via github.com/samw0907)"

# layer_key -> (url path segment, WFS typeName)
LAYERS = {
    "stand": ("v2/stand", "v2:stand"),
    "forestusedeclaration": ("v1/forestusedeclaration", "forestusedeclaration"),
    "forestmask": ("v2/forestmask", "v2:forestmask"),
    "habitat": ("v2/habitat", "v2:habitat"),
    "gridcell": ("v2/gridcell", "v2:gridcell"),
}


def _bbox_param(bbox_3067) -> str:
    minx, miny, maxx, maxy = bbox_3067
    return f"{minx},{miny},{maxx},{maxy},{_SRS_URI}"


def _get_json(session: requests.Session, url: str, params: dict) -> dict:
    last_exc = None
    for attempt in range(1, _RETRIES + 1):
        try:
            resp = session.get(url, params=params, timeout=_TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()
            if isinstance(payload, dict) and payload.get("type") == "ExceptionReport":
                raise RuntimeError(f"WFS exception: {json.dumps(payload)[:400]}")
            return payload
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            last_exc = exc
            if attempt < _RETRIES:
                time.sleep(2 * attempt)
    raise RuntimeError(f"Metsakeskus WFS request failed after {_RETRIES} tries: {last_exc}")


def _paged_features(session: requests.Session, url: str, base_params: dict, page: int = _PAGE):
    """Yield GeoJSON feature dicts across startIndex/count pages."""
    start = 0
    while True:
        params = dict(base_params, count=page, startIndex=start)
        fc = _get_json(session, url, params)
        feats = fc.get("features", [])
        yield from feats
        if len(feats) < page:
            return
        start += page


def _cache_paths(cache_dir: Path, layer_key: str, aoi_name: str):
    stem = cache_dir / "metsakeskus" / f"{layer_key}__{aoi_name}"
    return stem.with_suffix(".gpkg"), stem.with_suffix(".meta.json")


def fetch_layer(
    layer_key: str,
    aoi,
    *,
    cache_dir: str | Path = "data/raw",
    force: bool = False,
    session: requests.Session | None = None,
) -> gpd.GeoDataFrame:
    """Fetch a Metsakeskus WFS vector layer for the AOI as an EPSG:3067 GeoDataFrame.

    Caches to {cache_dir}/metsakeskus/{layer_key}__{aoi.name}.gpkg and returns the
    cache on repeat calls unless force=True.
    """
    if layer_key not in LAYERS:
        raise KeyError(f"unknown layer_key {layer_key!r}; known: {sorted(LAYERS)}")
    path_seg, type_name = LAYERS[layer_key]
    cache_dir = Path(cache_dir)
    gpkg, meta = _cache_paths(cache_dir, layer_key, aoi.name)

    if gpkg.exists() and not force:
        return gpd.read_file(gpkg)

    url = f"{BASE}/{path_seg}/ows"
    base_params = {
        "service": "WFS",
        "version": WFS_VERSION,
        "request": "GetFeature",
        "typeNames": type_name,
        "srsName": _SRS_URI,
        "bbox": _bbox_param(aoi.bbox_3067),
        "outputFormat": "application/json",
    }
    own_session = session is None
    session = session or requests.Session()
    if own_session:
        session.headers.update({"User-Agent": _UA})

    try:
        feats = list(_paged_features(session, url, base_params))
    finally:
        if own_session:
            session.close()

    if not feats:
        gdf = gpd.GeoDataFrame(geometry=[], crs=CRS)
    else:
        gdf = gpd.GeoDataFrame.from_features(feats, crs=CRS)
        if gdf.crs is None or gdf.crs.to_epsg() != 3067:
            gdf = gdf.set_crs(CRS, allow_override=True)

    gpkg.parent.mkdir(parents=True, exist_ok=True)
    if len(gdf):
        gdf.to_file(gpkg, driver="GPKG")
    meta.write_text(
        json.dumps(
            {
                "source": "metsakeskus",
                "endpoint": url,
                "typeName": type_name,
                "wfs_version": WFS_VERSION,
                "crs": CRS,
                "aoi_name": aoi.name,
                "aoi_bbox_3067": list(aoi.bbox_3067),
                "feature_count": int(len(gdf)),
                "fetch_date": date.today().isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return gdf


def fetch_raster(layer_key: str, aoi, version: str) -> str:
    """Path to a COG for a Metsakeskus WCS raster layer. Built when first needed
    (CHM download for Module A; korjuukelpoisuus / flow products for Project 2)."""
    raise NotImplementedError("Metsakeskus raster fetch is implemented when a module first needs it")
