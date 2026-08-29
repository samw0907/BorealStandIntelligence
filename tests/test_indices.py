# boreal-stand-intelligence/tests/test_indices.py
"""Tests for src.indices."""

import numpy as np

from src.indices import nbr, ndmi, ndvi, normalized_difference


def test_normalized_difference_basic():
    a = np.array([3.0, 1.0, 0.0], dtype="float32")
    b = np.array([1.0, 1.0, 0.0], dtype="float32")
    out = normalized_difference(a, b)
    assert np.isclose(out[0], 0.5)
    assert np.isclose(out[1], 0.0)
    assert np.isnan(out[2])  # 0/0 -> nan


def test_nan_propagates():
    a = np.array([np.nan, 0.2], dtype="float32")
    b = np.array([0.1, 0.1], dtype="float32")
    out = normalized_difference(a, b)
    assert np.isnan(out[0])
    assert np.isclose(out[1], (0.2 - 0.1) / 0.3)


def test_index_wrappers_orientation():
    # dense canopy: high NIR, low SWIR -> NBR and NDMI positive; NDVI positive
    nir = np.array([0.30], dtype="float32")
    swir22 = np.array([0.05], dtype="float32")
    swir16 = np.array([0.10], dtype="float32")
    red = np.array([0.03], dtype="float32")
    assert nbr(nir, swir22)[0] > 0.6
    assert ndmi(nir, swir16)[0] > 0.4
    assert ndvi(red, nir)[0] > 0.7
