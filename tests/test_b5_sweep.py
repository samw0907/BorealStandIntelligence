# boreal-stand-intelligence/tests/test_b5_sweep.py
"""Tests for the B5 machinery: felling class mapping, zonal mean, threshold sweep."""

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box
import geopandas as gpd

from src.b_harvest_detection import area_class, felling_class, threshold_sweep, zonal_mean

CFG = {
    "module_b_harvest_detection": {
        "threshold_sweep": {"min": 0.1, "max": 0.4, "step": 0.1},
        "felling_types_scored": ["regeneration", "thinning", "salvage"],
    }
}


def test_felling_class_mapping():
    assert felling_class(3, 5) == "regeneration"       # regeneration purpose
    assert felling_class(1, 3) == "thinning"           # thinning purpose + practice
    assert felling_class(6, None) == "salvage"         # forest-damage purpose
    assert felling_class(1, 22) == "salvage"           # insect-damage practice wins
    assert felling_class(4, 99) == "other"


def test_area_class_bins():
    assert area_class(0.7) == "0.5-1ha"
    assert area_class(3.0) == "2-5ha"
    assert area_class(25.0) == ">10ha"


def test_zonal_mean_assigns_by_centroid(tmp_path):
    arr = np.zeros((10, 10), dtype="float32")
    arr[2:5, 2:5] = 0.5                 # a bright block
    tif = tmp_path / "c.tif"
    with rasterio.open(tif, "w", driver="GTiff", crs="EPSG:3067",
                       transform=from_origin(0, 100, 10, 10), width=10, height=10,
                       count=1, dtype="float32", nodata=np.nan) as dst:
        dst.write(arr, 1)
    # polygon over the bright block (world coords: x 20-50, y down from 100)
    g1 = box(20, 50, 50, 80)           # covers arr[2:5, 2:5]
    g2 = box(60, 10, 90, 40)           # covers a zero region
    gdf = gpd.GeoDataFrame(geometry=[g1, g2], crs="EPSG:3067")
    means, counts = zonal_mean(gdf, tif)
    assert np.isclose(means[0], 0.5) and counts[0] == 9
    assert np.isclose(means[1], 0.0) and counts[1] == 9


def test_threshold_sweep_recall_and_precision():
    # 10 regeneration declarations, 6 detected at 0.3; 5 negative controls, none detected
    rows = []
    for i in range(10):
        rows.append(dict(unit="declaration", felling_class="regeneration", cohort_executed=True,
                         AREA=2.0, area_class="2-5ha", dnbr=0.5 if i < 6 else 0.05, npix=20))
    for i in range(5):
        rows.append(dict(unit="negative_control", felling_class="none", cohort_executed=False,
                         AREA=2.0, area_class="2-5ha", dnbr=0.02, npix=20))
    frame = pd.DataFrame(rows)
    frame.attrs["n_non_declared_total"] = 5
    frame.attrs["n_negative_sample"] = 5

    sw = threshold_sweep(frame, CFG)
    row = sw[(sw.cohort == "executed_in_window") & (sw.group == "type:regeneration")
             & np.isclose(sw.threshold, 0.3)].iloc[0]
    assert row["recall"] == 0.6          # 6 of 10
    assert row["precision"] == 1.0       # no false positives
    assert 0.7 < row["f1"] < 0.76
