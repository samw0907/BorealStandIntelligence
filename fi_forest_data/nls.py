# boreal-stand-intelligence/fi_forest_data/nls.py
"""National Land Survey of Finland (Maanmittauslaitos, NLS) data.

Fetches the open 2 m elevation model, the open 0.5 p laser scanning point cloud
(2020 onwards, for Module A ALS height metrics), and topographic database themes
(hydrography, roads). The licensed and paid 5 p laser scanning product is out of
scope and must not be attempted.

Public interface (planned):
    fetch_dem(aoi, resolution_m=2) -> str
    fetch_als(aoi, subset=None) -> list[str]     # LAZ tile paths
    fetch_topographic(theme, aoi) -> gpd.GeoDataFrame

Routes confirmed in TASK 00 (docs/DATA_SOURCES.md section 4): the Funet mirror
https://www.nic.funet.fi/index/geodata/mml/ (no API key; the official NLS OGC API
needs one and is avoided). dem2m/2008_latest/{block}/{sub}/{tile}.tif (2 m,
Float32, nodata -9999); laserkeilaus/2008_latest/ LAZ tiles + national index
shapefile 2008_latest.shp; maastotietokanta/2025/ per-mapsheet-block dirs for
hydrography and roads. NB: open ALS over the Project 1 SE AOI is 2009-2015 only
(~1.6 pts/m2); see Decision D1 in docs/TASK_00_FINDINGS.md.

No implementation yet — scaffold only.
"""
