# boreal-stand-intelligence/fi_forest_data/sentinel.py
"""Copernicus Sentinel access.

Fetches Sentinel-2 L2A (change detection, spectral features, stress time series)
and Sentinel-1 GRD (cloud-independent cross-check) over an AOI and date window.
All Sentinel use is DERIVE ONLY and Project 1 only.

Access decision (TASK 00, docs/DATA_SOURCES.md section 6): CDSE, not GEE. Catalogue
via CDSE STAC/OData (no auth), band-level partial reads from CDSE S3 to avoid bulk
SAFE downloads; reuse the Baltic project's CDSE code. Scene availability over the
SE AOI is ample (~70 S2 L2A scenes < 40% cloud per JJA window, every year); the
pipeline.yaml composite windows are viable as-is.

Public interface (planned):
    fetch_s2_composite(aoi, window, config) -> str   # path to COG stack
    fetch_s1_composite(aoi, window, config) -> str

No implementation yet — scaffold only.
"""
