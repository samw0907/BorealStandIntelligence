# boreal-stand-intelligence/tests/test_a_als_metrics.py
"""Test src.a_stand_estimation.als_cell_metrics on a synthetic point cloud + DEM."""

import numpy as np
import laspy
import rasterio
from rasterio.transform import from_origin

from src.a_stand_estimation import als_cell_metrics

CFG = {
    "module_a_stand_estimation": {
        "als": {"percentiles": [50, 90], "canopy_threshold_m": 2.0, "min_points_per_cell": 20}
    }
}


def _write_dem(path, x0, y0):
    # flat DEM at 100 m, 2 m pixels, with generous margin around the test cell
    arr = np.full((100, 100), 100.0, dtype="float32")
    with rasterio.open(path, "w", driver="GTiff", crs="EPSG:3067",
                       transform=from_origin(x0 - 40, y0 + 140, 2, 2), width=100, height=100,
                       count=1, dtype="float32", nodata=-9999.0) as dst:
        dst.write(arr, 1)


def _write_laz(path, x, y, z, return_number, classification):
    hdr = laspy.LasHeader(point_format=1, version="1.2")
    hdr.offsets = [x.min(), y.min(), z.min()]
    hdr.scales = [0.01, 0.01, 0.01]
    las = laspy.LasData(hdr)
    las.x, las.y, las.z = x, y, z
    las.return_number = return_number
    las.classification = classification
    las.write(path)


def test_als_cell_metrics_one_cell(tmp_path):
    x0, y0 = 600000, 6806000
    # one 16 m cell fully populated: 40 ground + 60 canopy points at ~15 m
    rng = np.random.default_rng(0)
    n_g, n_c = 40, 60
    xg = x0 + rng.uniform(1, 15, n_g)
    yg = y0 + rng.uniform(1, 15, n_g)
    xc = x0 + rng.uniform(1, 15, n_c)
    yc = y0 + rng.uniform(1, 15, n_c)
    x = np.concatenate([xg, xc])
    y = np.concatenate([yg, yc])
    z = np.concatenate([np.full(n_g, 100.0), 100.0 + rng.uniform(12, 18, n_c)])
    rn = np.concatenate([np.ones(n_g), np.ones(n_c)]).astype("uint8")
    cl = np.concatenate([np.full(n_g, 2), np.full(n_c, 5)]).astype("uint8")

    laz = tmp_path / "t.laz"
    dem = tmp_path / "dem.tif"
    _write_laz(laz, x, y, z, rn, cl)
    _write_dem(dem, x0, y0)

    m = als_cell_metrics([laz], dem, (x0, y0, x0 + 16, y0 + 16), CFG)
    assert len(m) == 1
    row = m.iloc[0]
    assert row["n"] == 100
    assert row["cx"] == x0 and row["cy"] == y0
    # 60 of 100 first returns are canopy (>2 m)
    assert abs(row["canopy_cover"] - 0.6) < 0.02
    # p90 height should be up in the canopy (~15-18 m above the 100 m ground)
    assert 12 < row["h_p90"] < 20
    assert row["h_max"] > 15
