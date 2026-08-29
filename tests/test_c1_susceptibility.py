# boreal-stand-intelligence/tests/test_c1_susceptibility.py
"""C1 helpers: beetle label filter, logistic fit, blocked-CV PR metrics."""

import numpy as np
import pandas as pd

from src.c1_beetle_susceptibility import (
    C1_PREDICTORS, beetle_declarations, c1_pr_metrics, c1_spatial_cv, fit_c1_logit,
)


def test_beetle_declarations_selects_1602_and_insect_practice():
    decl = pd.DataFrame({
        "FORESTDAMAGEQUALIFIER": ["1602.0", "1504.0", None, None, "1602"],
        "CUTTINGREALIZATIONPRACTICE": [None, "20", "22", "5", None],
    })
    out = beetle_declarations(decl)
    assert set(out.index) == {0, 2, 4}          # 1602, practice 22, 1602 (int-str)


def _synthetic_sample(n=1500, seed=1):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "spruce_share": rng.uniform(0.1, 0.9, n),
        "age": rng.uniform(20, 120, n),
        "site_fertility": rng.integers(1, 7, n).astype(float),
        "prior_damage_dist_km": rng.exponential(3.0, n),
    })
    # true risk rises with spruce share, falls with distance to prior damage
    logit = (-3.0 + 2.5 * (df["spruce_share"] - 0.5)
             - 0.35 * df["prior_damage_dist_km"])
    df["presence"] = (rng.uniform(size=n) < 1 / (1 + np.exp(-logit))).astype(int)
    gx = rng.uniform(0, 50000, n)
    gy = rng.uniform(0, 50000, n)
    df["block_id"] = ((gx // 10000).astype(int).astype(str) + "_"
                      + (gy // 10000).astype(int).astype(str))
    return df


def test_fit_c1_logit_recovers_signs_and_reports_odds_ratios():
    s = _synthetic_sample()
    res, coef = fit_c1_logit(s)
    assert list(coef["predictor"]) and set(coef["predictor"]) == set(C1_PREDICTORS)

    row = coef.set_index("predictor")
    assert row.loc["spruce_share", "odds_ratio_per_sd"] > 1.0
    assert row.loc["prior_damage_dist_km", "odds_ratio_per_sd"] < 1.0
    assert row.loc["spruce_share", "sign_matches"]
    assert row.loc["prior_damage_dist_km", "sign_matches"]
    assert 0.0 < res.prsquared < 1.0


def test_c1_spatial_cv_and_pr_metrics():
    s = _synthetic_sample()
    cv = c1_spatial_cv(s, n_folds=4, seed=0)
    assert cv["p_logit"].notna().any()
    assert cv["p_index"].notna().any()

    m = c1_pr_metrics(cv)
    assert 0.0 <= m["logit"]["average_precision"] <= 1.0
    # a model with real signal should beat the prevalence baseline
    assert m["logit"]["average_precision"] > m["prevalence"]
    assert len(m["logit"]["precision"]) == len(m["logit"]["recall"])
