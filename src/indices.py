# boreal-stand-intelligence/src/indices.py
"""Spectral index helpers, shared across modules.

All inputs are surface reflectance arrays (float32, NaN = nodata). Normalised
differences return NaN where the denominator is zero or an input is NaN.
"""

from __future__ import annotations

import numpy as np


def normalized_difference(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = a.astype("float32", copy=False)
    b = b.astype("float32", copy=False)
    denom = a + b
    with np.errstate(invalid="ignore", divide="ignore"):
        out = (a - b) / denom
    out[denom == 0] = np.nan
    return out


def nbr(nir: np.ndarray, swir22: np.ndarray) -> np.ndarray:
    """Normalised Burn Ratio: (NIR - SWIR22) / (NIR + SWIR22). High = dense canopy."""
    return normalized_difference(nir, swir22)


def ndmi(nir: np.ndarray, swir16: np.ndarray) -> np.ndarray:
    """Normalised Difference Moisture Index: (NIR - SWIR16) / (NIR + SWIR16)."""
    return normalized_difference(nir, swir16)


def ndvi(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """Normalised Difference Vegetation Index: (NIR - RED) / (NIR + RED)."""
    return normalized_difference(nir, red)
