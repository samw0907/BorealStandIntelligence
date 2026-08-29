# boreal-stand-intelligence/tests/test_io.py
"""Tests for fi_forest_data.io."""

import re

import numpy as np
import rasterio
from rasterio.transform import from_origin

from fi_forest_data.io import attribution_for, run_id, run_metadata, write_cog


def test_run_id_format():
    rid = run_id()
    assert re.fullmatch(r"\d{8}_\d{6}_\S+", rid)


def test_attribution_for_stable_order_and_subset():
    s = attribution_for(["copernicus", "metsakeskus"])
    assert s.startswith("Contains data from the Finnish Forest Centre")
    assert "Copernicus" in s
    assert attribution_for(["nls"]) == "Contains data from the National Land Survey of Finland, CC BY 4.0"


def test_run_metadata_has_expected_keys():
    md = run_metadata(
        {"a": 1, "b": [2, 3]},
        {"metsakeskus": {"fetched": "2026-08-29", "endpoint_version": "v2"}},
        aoi_bbox=(553000, 6780000, 610000, 6851000),
    )
    for key in ("created_utc", "run_id", "config_sha256", "aoi_bbox_3067", "sources", "packages"):
        assert key in md
    assert len(md["config_sha256"]) == 64
    assert md["sources"]["metsakeskus"]["endpoint_version"] == "v2"
    assert md["packages"]["rasterio"] is not None


def test_write_cog_round_trip(tmp_path):
    arr = (np.arange(64 * 64, dtype="float32").reshape(64, 64))
    transform = from_origin(553000, 6851000, 16, 16)
    profile = {"crs": "EPSG:3067", "transform": transform, "dtype": "float32"}
    out = tmp_path / "sub" / "test.tif"
    write_cog(arr, profile, out, attribution="test attribution", nodata=-9999.0)

    assert out.exists()
    with rasterio.open(out) as src:
        assert src.crs.to_epsg() == 3067
        assert src.count == 1
        assert src.nodata == -9999.0
        assert src.tags().get("attribution") == "test attribution"
        np.testing.assert_array_equal(src.read(1), arr)
