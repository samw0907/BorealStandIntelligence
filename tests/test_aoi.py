# boreal-stand-intelligence/tests/test_aoi.py
"""Tests for fi_forest_data.aoi."""

from pathlib import Path

import pytest

from fi_forest_data.aoi import AOI

CONFIG = Path(__file__).resolve().parents[1] / "config" / "aoi_southeast.yaml"


def test_load_southeast_aoi():
    aoi = AOI.from_yaml(CONFIG)
    assert aoi.name == "southeast_finland"
    assert aoi.crs == "EPSG:3067"
    assert aoi.bbox_3067 == (553000.0, 6780000.0, 610000.0, 6851000.0)


def test_area_matches_documented_extent():
    aoi = AOI.from_yaml(CONFIG)
    # 57 x 71 km -> ~4047 km2 (docs)
    assert 4000 < aoi.area_km2() < 4100


def test_polygon_bounds_round_trip():
    aoi = AOI.from_yaml(CONFIG)
    assert aoi.to_polygon().bounds == aoi.bbox_3067


def test_bbox_wgs84_is_in_southeast_finland():
    aoi = AOI.from_yaml(CONFIG)
    lon0, lat0, lon1, lat1 = aoi.bbox_wgs84()
    assert 27.5 < lon0 < lon1 < 29.5
    assert 60.8 < lat0 < lat1 < 62.0


def test_rejects_inverted_bbox():
    with pytest.raises(ValueError):
        AOI(name="bad", bbox_3067=(10.0, 10.0, 0.0, 0.0))


def test_rejects_non_tm35fin_crs():
    with pytest.raises(ValueError):
        AOI(name="bad", bbox_3067=(0.0, 0.0, 1.0, 1.0), crs="EPSG:4326")
