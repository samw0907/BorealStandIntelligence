# boreal-stand-intelligence/tests/test_a4b_models.py
"""Tests for the A4b modelling helpers: fold assignment, ABA OLS, k-NN imputation."""

import numpy as np
import pandas as pd

from src.a_stand_estimation import (
    ABA_PREDICTORS, assign_cv_folds, _aba_predict, _knn_predict,
)

CFG = {"module_a_stand_estimation": {"cv": {"n_folds": 5}}}


def _blocks_frame(seed=0):
    # 6 x 6 grid of 2 km blocks, a random but reproducible stand count each
    rng = np.random.default_rng(seed)
    rows = []
    for bx in range(600000, 612000, 2000):
        for by in range(6800000, 6812000, 2000):
            n = int(rng.integers(5, 120))
            rows += [f"{bx}_{by}"] * n
    return pd.DataFrame({"block_id": rows})


def test_assign_cv_folds_whole_blocks_and_balanced():
    df = _blocks_frame()
    folds = assign_cv_folds(df, CFG)
    assert set(folds.unique()) == {0, 1, 2, 3, 4}

    # every block sits entirely in one fold
    per_block = df.assign(fold=folds).groupby("block_id")["fold"].nunique()
    assert (per_block == 1).all()

    # folds are within ~1.6x of each other in stand count
    sizes = folds.value_counts()
    assert sizes.max() / sizes.min() < 1.6


def test_aba_predict_recovers_a_sqrt_linear_signal():
    rng = np.random.default_rng(1)
    n = 400
    h = rng.uniform(2, 25, n)
    tr = pd.DataFrame({
        "h_p90": h,
        "h_p50": h * 0.7 + rng.normal(0, 1.0, n),
        "h_p25": h * 0.3 + rng.normal(0, 0.8, n),
        "canopy_cover": rng.uniform(0.2, 0.95, n), "density": rng.uniform(0.6, 1.6, n),
    })
    # sqrt(volume) is linear in h_p90 with light noise
    tr["vol_total"] = (1.5 + 0.55 * h + rng.normal(0, 0.3, n)) ** 2
    te = tr.iloc[:50].copy()
    pred = _aba_predict(tr, te, "vol_total", ABA_PREDICTORS)
    assert pred.shape == (50,)
    assert (pred >= 0).all()
    # mean absolute error well under 15% of the mean level
    mape = np.mean(np.abs(pred - te["vol_total"])) / te["vol_total"].mean()
    assert mape < 0.15


def test_knn_predict_k1_returns_the_nearest_donor_vector():
    feats = {"h_p90": [5, 10, 20, 25], "h_p50": [3, 7, 14, 18],
             "h_p25": [1, 3, 6, 8], "canopy_cover": [0.3, 0.5, 0.8, 0.9],
             "density": [0.8, 1.0, 1.2, 1.4]}
    tr = pd.DataFrame(feats)
    tr["vol_total"] = [10.0, 80.0, 250.0, 400.0]
    tr["basalarea"] = [4.0, 15.0, 30.0, 40.0]
    tr["soil_main_type"] = "mineral"

    te = tr.iloc[[2]].copy()  # identical to donor row 2
    out = _knn_predict(tr, te, ["vol_total", "basalarea"], ABA_PREDICTORS,
                       k=1, weight_power=1.0, stratify_col=None)
    assert out.shape == (1, 2)
    assert np.allclose(out[0], [250.0, 30.0])


def test_knn_predict_stratified_falls_back_when_stratum_thin():
    rng = np.random.default_rng(2)
    n = 60
    tr = pd.DataFrame({
        "h_p90": rng.uniform(3, 24, n), "h_p50": rng.uniform(2, 16, n),
        "h_p25": rng.uniform(0, 6, n), "canopy_cover": rng.uniform(0.2, 0.95, n),
        "density": rng.uniform(0.6, 1.6, n),
        "vol_total": rng.uniform(0, 400, n),
        "soil_main_type": ["mineral"] * (n - 2) + ["peat"] * 2,
    })
    te = pd.DataFrame({
        "h_p90": [12.0], "h_p50": [8.0], "h_p25": [2.0],
        "canopy_cover": [0.6], "density": [1.0], "soil_main_type": ["peat"],
    })
    out = _knn_predict(tr, te, ["vol_total"], ABA_PREDICTORS,
                       k=5, weight_power=1.0, stratify_col="soil_main_type")
    # only 2 peat donors < k -> falls back to the full fold, still returns a value
    assert out.shape == (1, 1)
    assert 0.0 <= out[0, 0] <= 400.0
