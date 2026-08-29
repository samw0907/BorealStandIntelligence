# boreal-stand-intelligence/fi_forest_data/sentinel.py
"""Copernicus Sentinel access.

Fetches Sentinel-2 L2A (change detection, spectral features, stress time series)
and Sentinel-1 GRD (cloud-independent cross-check) over an AOI and date window.
Access via CDSE, or GEE if that proves simpler; existing portfolio code exists
for both and should be reused rather than rewritten. All Sentinel use is DERIVE
ONLY.

Public interface (planned):
    fetch_s2_composite(aoi, window, config) -> str   # path to COG stack
    fetch_s1_composite(aoi, window, config) -> str

No implementation yet — scaffold only. Cloud-free scene availability per season
is TO VERIFY in docs/DATA_SOURCES.md and is checked in TASK 00.
"""
