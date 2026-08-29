# boreal-stand-intelligence/src/c2_beetle_stress.py
"""Module C2 — bark beetle canopy stress detection.

Builds a multi-year baseline of red-edge and moisture indices (NDRE, NDMI) per
stand from Sentinel-2 and flags departures beyond a standard-deviation threshold
as candidate stress. Compares detection dates against declared salvage felling
dates and reports the days-early distribution.

Data tier: Sentinel-2 DERIVE ONLY; declared salvage dates FETCH.

No implementation yet — scaffold only.
"""
