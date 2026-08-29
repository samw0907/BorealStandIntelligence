# boreal-stand-intelligence/fi_forest_data/metsakeskus.py
"""Metsakeskus (Finnish Forest Centre) open forest and nature data.

GeoServer WFS/WMS/WCS at https://avoin.metsakeskus.fi/rajapinnat/. Fetches
vector layers (stands, habitats, forest use declarations, grid cells) and
rasters (canopy height model, forest mask, trafficability). Endpoint versions
are pinned in the URL path (/v1/, /v2/) and recorded, with the fetch date, in
run metadata. Layer keys, tiers and consumers are listed in docs/DATA_SOURCES.md.

Public interface (planned):
    fetch_layer(layer_key, aoi, version) -> gpd.GeoDataFrame
    fetch_raster(layer_key, aoi, version) -> str  # path to COG

No implementation yet — scaffold only. Several layer schemas are TO VERIFY in
docs/DATA_SOURCES.md and are resolved by TASK 00 before this module is written.
"""
