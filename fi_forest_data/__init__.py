# boreal-stand-intelligence/fi_forest_data/__init__.py
"""Data access layer for the Finnish forest portfolio.

Fetches, caches and reprojects data from Metsakeskus, Luke, NLS, FMI and
Copernicus Sentinel. Reprojection to EPSG:3067 happens here at ingest, once, and
nowhere else. This layer contains no analysis logic: it only gets data and hands
it over. Copied verbatim into the companion repo when Project 2 begins.
"""

from fi_forest_data.aoi import AOI

__all__ = ["AOI"]
