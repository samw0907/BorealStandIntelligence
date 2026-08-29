# boreal-stand-intelligence/tests/test_a5_spectral.py
"""Test src.a_stand_estimation.add_spectral_features on a synthetic S2 composite."""

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

from src.a_stand_estimation import add_spectral_features

BANDS = ["blue", "green", "red", "rededge1", "nir", "swir16", "swir22"]


def _write_s2(path, x0, y0, res=20, n=50):
    # constant reflectance per band, distinct values, so a stand median == that value
    vals = {"blue": 0.03, "green": 0.05, "red": 0.04, "rededge1": 0.08,
            "nir": 0.30, "swir16": 0.12, "swir22": 0.06}
    arr = np.stack([np.full((n, n), vals[b], dtype="float32") for b in BANDS])
    prof = dict(driver="GTiff", crs="EPSG:3067",
                transform=from_origin(x0, y0 + n * res, res, res),
                width=n, height=n, count=len(BANDS), dtype="float32",
                nodata=float("nan"))
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(arr)
        for i, b in enumerate(BANDS, start=1):
            dst.set_band_description(i, b)
    return vals


def test_add_spectral_features_medians_and_indices(tmp_path):
    x0, y0 = 600000, 6806000
    tif = tmp_path / "s2.tif"
    vals = _write_s2(tif, x0, y0)

    stands = gpd.GeoDataFrame(
        {"standid": [1, 2]},
        geometry=[box(x0 + 100, y0 + 100, x0 + 300, y0 + 300),
                  box(x0 + 400, y0 + 400, x0 + 700, y0 + 700)],
        crs="EPSG:3067",
    )
    out = add_spectral_features(stands, tif)

    for b in BANDS:
        assert np.allclose(out[f"s2_{b}"], vals[b], atol=1e-4)

    ndvi = (vals["nir"] - vals["red"]) / (vals["nir"] + vals["red"])
    assert np.allclose(out["s2_ndvi"], ndvi, atol=1e-4)
    assert {"s2_ndre", "s2_ndmi"}.issubset(out.columns)
    assert len(out) == 2
