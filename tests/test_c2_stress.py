# boreal-stand-intelligence/tests/test_c2_stress.py
"""C2 detection: seasonal baseline, windowed sustained departure, summary."""

import numpy as np
import pandas as pd

from src.c2_beetle_stress import c2_detect, c2_summary


def _series(standid, level, drop_from=None, drop_to=-0.15, years=range(2019, 2025),
            months=(5, 6, 7, 8, 9)):
    rows = []
    for y in years:
        for m in months:
            v = level
            if drop_from is not None and pd.Timestamp(y, m, 15) >= drop_from:
                v = level + drop_to
            rows.append({"standid": standid, "year": y, "month": m,
                         "date": pd.Timestamp(y, m, 15), "ndre": v,
                         "ndmi": v - 0.05, "n_scenes": 8})
    return rows


def _dataset():
    rng = np.random.default_rng(0)
    idx_rows, stands = [], []
    # 6 damaged stands with a real NDRE drop starting a year before salvage
    for i in range(6):
        salvage = pd.Timestamp(2023, 6, 15)
        rows = _series(i, 0.45 + rng.normal(0, 0.002),
                       drop_from=pd.Timestamp(2022, 6, 15), drop_to=-0.18)
        for r in rows:
            r["ndre"] += rng.normal(0, 0.003)
        idx_rows += rows
        stands.append({"standid": i, "group": "damaged", "salvage_date": salvage})
    # 6 stable control stands
    for i in range(100, 106):
        rows = _series(i, 0.42 + rng.normal(0, 0.002))
        for r in rows:
            r["ndre"] += rng.normal(0, 0.003)
        idx_rows += rows
        stands.append({"standid": i, "group": "control", "salvage_date": pd.NaT})
    return pd.DataFrame(idx_rows), pd.DataFrame(stands)


def test_c2_detect_flags_damaged_before_salvage_and_spares_controls():
    idx, sel = _dataset()
    det = c2_detect(idx, sel, index="ndre", z_threshold=2.0)

    dmg = det[det["group"] == "damaged"]
    ctl = det[det["group"] == "control"]
    assert dmg["detected"].mean() >= 0.8            # the real drop is caught
    assert ctl["detected"].mean() == 0.0           # stable controls not flagged
    # detection precedes the salvage declaration
    assert (dmg.loc[dmg["detected"], "days_early"] > 0).all()


def test_c2_summary_shape_and_small_n_guard():
    idx, sel = _dataset()
    s = c2_summary(c2_detect(idx, sel, index="ndre"))
    assert s["n_damaged_evaluated"] == 6
    assert 0.0 <= s["false_alarm_rate_control"] <= 1.0
    assert s["days_early"]["share_before_declaration"] == 1.0
    assert s["fisher_p_detection_gt_falsealarm"] is not None
    # n = 6 detected < 12 -> no quantiles, a note instead
    assert "median" not in s["days_early"]
    assert "note" in s["days_early"]
    # with the threshold lowered, quantiles appear
    s2 = c2_summary(c2_detect(idx, sel, index="ndre"), min_n_for_quantiles=3)
    assert {"median", "q25", "q75"} <= set(s2["days_early"])
