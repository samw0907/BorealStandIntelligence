# boreal-stand-intelligence/tests/test_a6_report.py
"""A6 reporting helpers: estimable_tier and attribute_summary."""

import pandas as pd

from src.a_stand_estimation import attribute_summary, estimable_tier


def test_estimable_tier_thresholds():
    assert estimable_tier(0.90, 13.0) == "reliable"
    assert estimable_tier(0.90, 28.0) == "usable"      # ranks well but scatters
    assert estimable_tier(0.72, 18.0) == "usable"
    assert estimable_tier(0.55, 40.0) == "weak"
    assert estimable_tier(0.20, 90.0) == "not_estimable"


def _metrics(rows):
    return pd.DataFrame(rows, columns=["target", "method", "rmse", "bias",
                                       "rmse_pct", "r2"])


def test_attribute_summary_picks_best_method_and_orders_by_tier():
    s2 = _metrics([
        ("vol_total", "aba", 25.0, -0.3, 12.9, 0.89),
        ("vol_total", "knn5", 28.8, -1.9, 14.8, 0.86),
        ("vol_total", "knn1", 40.0, 0.0, 20.0, 0.60),
        ("vol_spruce", "aba", 44.0, 0.2, 55.0, 0.56),
        ("vol_spruce", "knn5", 42.3, -3.2, 52.9, 0.59),
    ])
    als = _metrics([
        ("vol_total", "aba", 33.0, 0.0, 17.0, 0.81),
        ("vol_spruce", "knn5", 60.0, 0.5, 75.0, 0.18),
    ])
    out = attribute_summary(s2, als)

    vt = out[out["attribute"] == "vol_total"].iloc[0]
    assert vt["best_method"] == "aba"          # lowest RMSE of the k=5 / aba pair
    assert vt["tier"] == "reliable"
    assert vt["r2_als_only"] == 0.81

    vs = out[out["attribute"] == "vol_spruce"].iloc[0]
    assert vs["best_method"] == "knn5"
    assert vs["tier"] == "weak"

    # reliable sorts above weak
    assert list(out["attribute"]) == ["vol_total", "vol_spruce"]
