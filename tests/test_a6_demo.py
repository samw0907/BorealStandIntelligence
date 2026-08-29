# boreal-stand-intelligence/tests/test_a6_demo.py
"""A6 draw-a-polygon demo: fit_production_models + estimate_polygon."""

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

from src.a_stand_estimation import (
    ABA_PREDICTORS, S2_BANDS, estimate_polygon, fit_production_models,
)

CFG = {"module_a_stand_estimation": {"knn": {"stratify_by": "soil_main_type"}}}
S2_COLS = [f"s2_{b}" for b in S2_BANDS] + ["s2_ndvi", "s2_ndre", "s2_ndmi"]
FEATURES = ABA_PREDICTORS + S2_COLS


def _frame(n=120):
    rng = np.random.default_rng(0)
    h = rng.uniform(4, 24, n)
    df = pd.DataFrame({
        "standid": np.arange(1, n + 1),
        "h_p25": h * 0.3 + rng.normal(0, 0.5, n),
        "h_p50": h * 0.6 + rng.normal(0, 0.5, n),
        "h_p75": h * 0.85 + rng.normal(0, 0.5, n),
        "h_p90": h, "h_p95": h * 1.05,
        "h_mean": h * 0.6, "h_max": h * 1.1,
        "canopy_cover": rng.uniform(0.3, 0.95, n),
        "density": rng.uniform(0.6, 1.5, n),
        "soil_main_type": rng.choice(["mineral", "peat"], n, p=[0.8, 0.2]),
    })
    for c in S2_COLS:
        df[c] = rng.uniform(0.02, 0.4, n)
    df["vol_total"] = np.clip(6.0 * h + rng.normal(0, 15, n), 0, None)
    df["meanheight"] = h * 0.9 + rng.normal(0, 0.4, n)
    return df


def _s2_tif(path, x0, y0, res=20, n=60):
    rng = np.random.default_rng(1)
    arr = np.stack([np.full((n, n), v, dtype="float32")
                    for v in rng.uniform(0.03, 0.3, len(S2_BANDS))])
    with rasterio.open(path, "w", driver="GTiff", crs="EPSG:3067",
                       transform=from_origin(x0, y0 + n * res, res, res),
                       width=n, height=n, count=len(S2_BANDS), dtype="float32",
                       nodata=float("nan")) as dst:
        dst.write(arr)
        for i, b in enumerate(S2_BANDS, start=1):
            dst.set_band_description(i, b)


def test_estimate_polygon_shapes_and_recovery(tmp_path):
    df = _frame()
    bundle = fit_production_models(
        df, CFG, features=FEATURES, targets=["vol_total", "meanheight"])
    assert set(bundle["knn_index"]) <= {"mineral", "peat"}

    x0, y0 = 600000, 6806000
    tif = tmp_path / "s2.tif"
    _s2_tif(tif, x0, y0)
    cells = pd.DataFrame([
        {"cx": x0 + i * 16, "cy": y0 + j * 16, "h_mean": 12.0, "h_max": 22.0,
         "h_p25": 4.0, "h_p50": 9.0, "h_p75": 15.0, "h_p90": 18.0,
         "h_p95": 19.0, "canopy_cover": 0.7, "density": 1.1}
        for i in range(20) for j in range(20)
    ])
    geom = box(x0 + 16, y0 + 16, x0 + 240, y0 + 240)

    out = estimate_polygon(geom, bundle, cells, tif, soil_main_type="mineral", k=5)
    assert set(out) == {"n_cells", "aba", "knn", "knn_donors"}
    assert out["n_cells"] > 0
    assert set(out["aba"]) == {"vol_total", "meanheight"}
    assert len(out["knn_donors"]) == 5
    assert abs(sum(d["weight"] for d in out["knn_donors"]) - 1.0) < 0.02  # weights rounded to 3dp
    # h_p90 ~ 18 -> vol_total ~ 6*18 ~ 108, within a wide sanity band
    assert 40 < out["aba"]["vol_total"] < 180
    assert 8 < out["knn"]["meanheight"] < 26
