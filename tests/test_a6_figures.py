# boreal-stand-intelligence/tests/test_a6_figures.py
"""Smoke tests for the Module A figure builders: they run and write a PNG."""

import pandas as pd

from src.figures import (
    module_a_error_by_volclass, module_a_msnfi_agreement, module_a_spectral_lift,
)


def _cv_metrics(r2_by_target):
    return pd.DataFrame(
        [{"target": t, "method": "knn5", "rmse": 30.0, "bias": 0.0,
          "rmse_pct": 20.0, "r2": r2} for t, r2 in r2_by_target.items()]
    )


def test_spectral_lift_writes_png(tmp_path):
    als = _cv_metrics({"vol_total": 0.81, "vol_pine": 0.40, "vol_spruce": 0.18,
                       "vol_other": 0.27, "basalarea": 0.66, "meanheight": 0.93})
    s2 = _cv_metrics({"vol_total": 0.86, "vol_pine": 0.62, "vol_spruce": 0.59,
                      "vol_other": 0.76, "basalarea": 0.78, "meanheight": 0.88})
    als.to_csv(tmp_path / "als.csv", index=False)
    s2.to_csv(tmp_path / "s2.csv", index=False)
    out = module_a_spectral_lift(tmp_path / "als.csv", tmp_path / "s2.csv",
                                 tmp_path / "lift.png")
    assert (tmp_path / "lift.png").stat().st_size > 0
    assert out.endswith("lift.png")


def test_msnfi_agreement_writes_png(tmp_path):
    pd.DataFrame([
        {"attribute": "vol_total", "n": 3480, "r_register_vs_msnfi": 0.73,
         "r_estimate_vs_msnfi": 0.77, "rmse_register_vs_msnfi": 64.5,
         "rmse_estimate_vs_msnfi": 57.0},
        {"attribute": "meanheight", "n": 3480, "r_register_vs_msnfi": 0.73,
         "r_estimate_vs_msnfi": 0.77, "rmse_register_vs_msnfi": 3.1,
         "rmse_estimate_vs_msnfi": 2.7},
    ]).to_csv(tmp_path / "agree.csv", index=False)
    module_a_msnfi_agreement(tmp_path / "agree.csv", tmp_path / "agree.png")
    assert (tmp_path / "agree.png").stat().st_size > 0


def test_error_by_volclass_writes_png(tmp_path):
    rows = []
    for m in ("aba", "knn5"):
        for c, b, n in [("0-50", 24, 37), ("50-100", 8, 301), ("100-150", 6, 702),
                        ("150-200", 3, 925), ("200-300", -4, 1190), ("300+", -19, 325)]:
            rows.append({"method": m, "vol_class": c, "n": n, "rmse": 25.0, "bias": b})
    pd.DataFrame(rows).to_csv(tmp_path / "vc.csv", index=False)
    module_a_error_by_volclass(tmp_path / "vc.csv", tmp_path / "vc.png")
    assert (tmp_path / "vc.png").stat().st_size > 0
