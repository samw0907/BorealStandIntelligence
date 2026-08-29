# boreal-stand-intelligence/tests/test_b_change_surfaces.py
"""Tests for src.b_harvest_detection.compute_change_surfaces on synthetic composites."""

import json

import numpy as np
import rasterio
from rasterio.transform import from_origin

from src.b_harvest_detection import compute_change_surfaces

BANDS = ("blue", "green", "red", "rededge1", "nir", "swir16", "swir22")


def _write_composite(path, nir, swir16, swir22):
    h, w = nir.shape
    arr = np.zeros((len(BANDS), h, w), dtype="float32")
    arr[BANDS.index("nir")] = nir
    arr[BANDS.index("swir16")] = swir16
    arr[BANDS.index("swir22")] = swir22
    profile = {
        "driver": "GTiff", "crs": "EPSG:3067",
        "transform": from_origin(553000, 6790000, 20, 20),
        "width": w, "height": h, "count": len(BANDS), "dtype": "float32", "nodata": np.nan,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr)
        for i, b in enumerate(BANDS, start=1):
            dst.set_band_description(i, b)


def test_change_surface_sign_and_outputs(tmp_path):
    # forest everywhere pre; a 2x2 patch clearcut in post (NIR down, SWIR up)
    nir_pre = np.full((6, 6), 0.30, dtype="float32")
    sw16_pre = np.full((6, 6), 0.10, dtype="float32")
    sw22_pre = np.full((6, 6), 0.05, dtype="float32")

    nir_post = nir_pre.copy()
    sw22_post = sw22_pre.copy()
    sw16_post = sw16_pre.copy()
    nir_post[2:4, 2:4] = 0.18
    sw22_post[2:4, 2:4] = 0.16
    sw16_post[2:4, 2:4] = 0.22

    pre = tmp_path / "pre.tif"
    post = tmp_path / "post.tif"
    _write_composite(pre, nir_pre, sw16_pre, sw22_pre)
    _write_composite(post, nir_post, sw16_post, sw22_post)

    res = compute_change_surfaces(pre, post, tmp_path / "out")
    with rasterio.open(res["dnbr"]) as src:
        dnbr = src.read(1)
        assert src.tags().get("attribution", "").startswith("Contains modified Copernicus")

    # clearcut patch has a strongly positive dNBR; undisturbed background ~ 0
    assert dnbr[2:4, 2:4].mean() > 0.3
    assert abs(dnbr[0, 0]) < 1e-4

    meta = json.loads((tmp_path / "out" / "change_surfaces.meta.json").read_text())
    assert meta["step"] == "B3_change_surfaces"
    assert meta["dnbr"]["p99"] > 0.3
    assert res["forest_mask"] is None
