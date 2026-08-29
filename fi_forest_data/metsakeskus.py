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

Routes confirmed in TASK 00 (see docs/DATA_SOURCES.md section 1): WFS 2.0.0 for
vectors (stand, habitat, gridcell, forestusedeclaration, forestmask; GeoJSON
output, paging, EPSG:3067 native); WCS 2.0.1 for a subset of rasters
(Korjuukelpoisuus, DTW 1/4 ha, D8, FA, Virtausverkko, RUSLE); the
https://avoin.metsakeskus.fi/aineistot/ bulk file tree for the rest (CHM 1 m,
Kemera subsidy sites) and for full-AOI GeoPackage pulls. Coded values decode via
the KOOD V35 workbook.

No implementation yet — scaffold only.
"""
