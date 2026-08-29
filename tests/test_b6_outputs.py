# boreal-stand-intelligence/tests/test_b6_outputs.py
"""Tests for B6 deliverables on synthetic data."""

import numpy as np
import geopandas as gpd
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

from src.b_harvest_detection import flag_inventory_stale, mismatch_sets

CFG = {
    "module_b_harvest_detection": {
        "min_stand_area_ha": 0.5,
        "min_valid_pixels": 3,
        "felling_types_scored": ["regeneration", "thinning", "salvage"],
        "ground_truth": {"full_register_arrival": {"start": "2019-01-01", "end": "2024-06-01"}},
    }
}


def _dnbr_tif(path, arr):
    h, w = arr.shape
    with rasterio.open(path, "w", driver="GTiff", crs="EPSG:3067",
                       transform=from_origin(0, 1000, 10, 10), width=w, height=h,
                       count=1, dtype="float32", nodata=np.nan) as dst:
        dst.write(arr.astype("float32"), 1)


def _stands_gpkg(path, geoms, **cols):
    n = len(geoms)
    data = {"standid": list(range(1, n + 1)), "area": cols.get("area", [2.0] * n),
            "maintreespecies": [1] * n, "developmentclass": ["03"] * n,
            "measurementdate": cols.get("measurementdate", ["2020-06-01"] * n),
            "treestanddatasource": ["4"] * n, "volume": [150.0] * n}
    gpd.GeoDataFrame(data, geometry=geoms, crs="EPSG:3067").to_file(path, driver="GPKG")


def test_flag_inventory_stale(tmp_path):
    arr = np.full((20, 20), -0.03, dtype="float32")
    arr[2:6, 2:6] = 0.4                       # one clearcut-like patch
    tif = tmp_path / "dnbr.tif"
    _dnbr_tif(tif, arr)
    stands = tmp_path / "stands.gpkg"
    _stands_gpkg(stands,
                 [box(20, 940, 60, 980),      # over the bright patch, old scan -> stale
                  box(120, 500, 160, 540),    # quiet, old scan -> not stale
                  box(20, 940, 60, 980)],     # over bright patch but scanned 2025 -> not stale
                 measurementdate=["2020-06-01", "2020-06-01", "2025-01-01"])

    g = flag_inventory_stale(stands, tif, CFG, regen_threshold=0.08)
    assert bool(g.loc[0, "inventory_stale"]) is True
    assert bool(g.loc[1, "inventory_stale"]) is False
    assert bool(g.loc[2, "inventory_stale"]) is False


def test_mismatch_sets(tmp_path):
    arr = np.full((30, 30), -0.03, dtype="float32")
    arr[2:6, 2:6] = 0.4                        # bright patch A, world x[20,60] y[940,980]
    arr[20:24, 20:24] = 0.4                    # bright patch B, world x[200,240] y[760,800]
    tif = tmp_path / "dnbr.tif"
    _dnbr_tif(tif, arr)

    bright = box(20, 940, 60, 980)             # over patch A
    quiet_a = box(120, 900, 160, 940)
    _stands_gpkg(tmp_path / "st.gpkg", [
        bright,                       # stand 1: detected + declared   -> in neither set
        quiet_a,                      # stand 2: declared, not detected -> declared_not_detected
        box(120, 800, 160, 840),     # stand 3: quiet, undeclared      -> neither
        box(200, 760, 240, 800),     # stand 4: detected, undeclared   -> detected_not_declared
    ])
    decls = gpd.GeoDataFrame(
        {"FORESTUSEDECLARATIONNUMBER": ["a", "b"], "CUTTINGPURPOSE": [3, 3],
         "CUTTINGREALIZATIONPRACTICE": [5, 5], "FORESTDAMAGEQUALIFIER": [None, None],
         "DECLARATIONARRIVALDATE": ["2022-03-01T00:00:00+02:00", "2022-03-01T00:00:00+02:00"],
         "AREA": [2.0, 2.0]},
        geometry=[bright, quiet_a], crs="EPSG:3067")
    decls.to_file(tmp_path / "decl.gpkg", driver="GPKG")

    mm = mismatch_sets(tmp_path / "st.gpkg", tmp_path / "decl.gpkg", tif, CFG, regen_threshold=0.08)
    assert mm["declared_not_detected_summary"]["n"] == 1     # stand 2
    assert mm["detected_not_declared_summary"]["n"] == 1     # stand 4
