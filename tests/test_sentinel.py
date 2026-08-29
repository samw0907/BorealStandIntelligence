# boreal-stand-intelligence/tests/test_sentinel.py
"""Tests for fi_forest_data.sentinel helpers (no network)."""

import pytest

from fi_forest_data.aoi import AOI
from fi_forest_data.sentinel import _assert_scale_offset, _cache_paths, search_s2_scenes

AOI_SE = AOI(name="se_test", bbox_3067=(553000.0, 6780000.0, 610000.0, 6851000.0))

CFG = {
    "sentinel2": {
        "stac_url": "https://example/v1",
        "collection": "sentinel-2-c1-l2a",
        "max_cloud_scene_pct": 40,
        "reflectance_scale": 0.0001,
        "reflectance_offset": -0.1,
        "composite_windows": {"pre": {"start": "2021-06-01", "end": "2021-08-31"}},
    }
}


class FakeAsset:
    def __init__(self, scale, offset):
        self.extra_fields = {"raster:bands": [{"scale": scale, "offset": offset}]}


class FakeItem:
    def __init__(self, item_id, scale, offset, dt="2021-07-01T10:00:00Z"):
        self.id = item_id
        self.properties = {"datetime": dt}
        self.assets = {b: FakeAsset(scale, offset) for b in ("red", "nir", "swir16")}


class FakeSearch:
    def __init__(self, items):
        self._items = items

    def items(self):
        return list(self._items)


class FakeClient:
    def __init__(self, items):
        self._items = items
        self.last_kwargs = None

    def search(self, **kwargs):
        self.last_kwargs = kwargs
        return FakeSearch(self._items)


def test_assert_scale_offset_passes_on_expected():
    items = [FakeItem("a", 0.0001, -0.1), FakeItem("b", 0.0001, -0.1)]
    _assert_scale_offset(items, ["red", "nir", "swir16"], 0.0001, -0.1)


def test_assert_scale_offset_raises_on_mismatch():
    items = [FakeItem("a", 0.0001, -0.1), FakeItem("b", 0.0001, 0.0)]
    with pytest.raises(RuntimeError, match="radiometric baseline"):
        _assert_scale_offset(items, ["red"], 0.0001, -0.1)


def test_search_passes_expected_query():
    client = FakeClient([FakeItem("z", 0.0001, -0.1)])
    window = CFG["sentinel2"]["composite_windows"]["pre"]
    items = search_s2_scenes(AOI_SE, window, CFG, client=client)
    assert len(items) == 1
    kw = client.last_kwargs
    assert kw["collections"] == ["sentinel-2-c1-l2a"]
    assert kw["datetime"] == "2021-06-01/2021-08-31"
    assert kw["query"] == {"eo:cloud_cover": {"lt": 40}}
    assert len(kw["bbox"]) == 4 and 27 < kw["bbox"][0] < 30


def test_cache_paths_layout(tmp_path):
    tif, meta = _cache_paths(tmp_path, "pre", "se_test")
    assert tif.name == "s2_pre__se_test.tif"
    assert meta.name == "s2_pre__se_test.meta.json"
    assert tif.parent.name == "sentinel2"
