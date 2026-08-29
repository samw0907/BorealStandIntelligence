# boreal-stand-intelligence/tests/test_a5_domain.py
"""stand_model_frame gates the Module A domain to established stands (A5b)."""

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

from src.a_stand_estimation import ALS_FEATURES, stand_model_frame

CFG = {
    "module_a_stand_estimation": {
        "exclude_dev_classes": ["A0", "T1", "T2"],
        "cv": {"block_size_km": 2},
        "als": {},
    }
}


def _cells_for(x0, y0, nx, ny):
    rows = []
    for i in range(nx):
        for j in range(ny):
            cx, cy = x0 + i * 16, y0 + j * 16
            rows.append({"cx": cx, "cy": cy, "h_mean": 12.0, "h_max": 20.0,
                         "h_p25": 4.0, "h_p50": 10.0, "h_p75": 15.0,
                         "h_p90": 18.0, "h_p95": 19.0, "canopy_cover": 0.7,
                         "density": 1.1})
    return rows


def _make_inputs(tmp_path):
    specs = [  # standid, dev class, corner
        (1, "03", (600000, 6806000)),
        (2, "02", (600400, 6806000)),
        (3, "T1", (600800, 6806000)),  # seedling - must be dropped
    ]
    polys, cells = [], []
    for sid, dev, (x0, y0) in specs:
        polys.append({"standid": sid, "developmentclass": dev,
                      "treestanddatasource": "4", "maingroup": "1",
                      "soiltype": "10", "volume": 150.0, "proportionpine": 0.6,
                      "proportionspruce": 0.3, "proportionother": 0.1,
                      "sawlogvolume": 70.0, "pulpwoodvolume": 60.0,
                      "stemcount": 900.0, "meanage": 50.0, "basalarea": 20.0,
                      "meanheight": 18.0, "meandiameter": 20.0,
                      "volumegrowth": 8.0, "maintreespecies": 1,
                      "geometry": box(x0, y0, x0 + 240, y0 + 240)})
        cells += _cells_for(x0 + 16, y0 + 16, 12, 12)

    gpkg = tmp_path / "stand.gpkg"
    gpd.GeoDataFrame(polys, crs="EPSG:3067").to_file(gpkg, driver="GPKG")
    csv = tmp_path / "cells.csv"
    pd.DataFrame(cells).to_csv(csv, index=False)
    return str(gpkg), str(csv)


def test_seedling_class_is_excluded(tmp_path):
    gpkg, csv = _make_inputs(tmp_path)
    frame = stand_model_frame(gpkg, csv, CFG, min_cells=8)
    assert set(frame["standid"]) == {1, 2}
    assert "T1" not in set(frame["developmentclass"])
    assert set(ALS_FEATURES).issubset(frame.columns)
    assert (frame["soil_main_type"] == "mineral").all()


def test_no_exclusion_when_config_key_absent(tmp_path):
    gpkg, csv = _make_inputs(tmp_path)
    cfg = {"module_a_stand_estimation": {"cv": {"block_size_km": 2}, "als": {}}}
    frame = stand_model_frame(gpkg, csv, cfg, min_cells=8)
    assert set(frame["standid"]) == {1, 2, 3}
    assert np.isin(["T1"], frame["developmentclass"]).any()
