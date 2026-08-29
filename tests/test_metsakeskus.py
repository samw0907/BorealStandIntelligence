# boreal-stand-intelligence/tests/test_metsakeskus.py
"""Tests for fi_forest_data.metsakeskus (no network — a fake session feeds pages)."""

import json

import pytest

from fi_forest_data.aoi import AOI
from fi_forest_data.metsakeskus import LAYERS, _bbox_param, _paged_features, fetch_layer

AOI_SE = AOI(name="se_test", bbox_3067=(553000.0, 6780000.0, 610000.0, 6851000.0))


def _feature(i):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [560000 + i, 6800000 + i]},
        "properties": {"id": i},
    }


class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeSession:
    """Returns `total` features across pages of `page` size, echoing startIndex/count."""

    def __init__(self, total, page):
        self.total = total
        self.page = page
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(params)
        start = params["startIndex"]
        count = params["count"]
        feats = [_feature(i) for i in range(start, min(start + count, self.total))]
        return FakeResp({"type": "FeatureCollection", "features": feats})


def test_bbox_param_format():
    assert _bbox_param((1, 2, 3, 4)) == "1,2,3,4,urn:ogc:def:crs:EPSG::3067"


def test_layer_registry_has_module_b_layers():
    for key in ("stand", "forestusedeclaration", "forestmask"):
        assert key in LAYERS


def test_paged_features_walks_all_pages():
    sess = FakeSession(total=25, page=10)
    feats = list(_paged_features(sess, "http://x", {"request": "GetFeature"}, page=10))
    assert len(feats) == 25
    assert [c["startIndex"] for c in sess.calls] == [0, 10, 20]


def test_paged_features_exact_multiple_makes_one_extra_empty_call():
    sess = FakeSession(total=20, page=10)
    feats = list(_paged_features(sess, "http://x", {}, page=10))
    assert len(feats) == 20
    assert [c["startIndex"] for c in sess.calls] == [0, 10, 20]


def test_fetch_layer_caches_and_reads_back(tmp_path):
    sess = FakeSession(total=15, page=10)
    gdf = fetch_layer("stand", AOI_SE, cache_dir=tmp_path, session=sess)
    assert len(gdf) == 15
    assert gdf.crs.to_epsg() == 3067

    gpkg = tmp_path / "metsakeskus" / "stand__se_test.gpkg"
    meta = tmp_path / "metsakeskus" / "stand__se_test.meta.json"
    assert gpkg.exists() and meta.exists()
    m = json.loads(meta.read_text())
    assert m["feature_count"] == 15 and m["typeName"] == "v2:stand"

    # second call: cache hit, no further requests
    sess2 = FakeSession(total=0, page=10)
    gdf2 = fetch_layer("stand", AOI_SE, cache_dir=tmp_path, session=sess2)
    assert len(gdf2) == 15
    assert sess2.calls == []


def test_fetch_layer_rejects_unknown_key(tmp_path):
    with pytest.raises(KeyError):
        fetch_layer("banana", AOI_SE, cache_dir=tmp_path, session=FakeSession(0, 10))
