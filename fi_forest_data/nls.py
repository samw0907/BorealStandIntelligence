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

No implementation yet — scaffold only. Download mechanism, whether an OmaTili API
key is required, and the tiling scheme are TO VERIFY in docs/DATA_SOURCES.md and
are resolved by TASK 00.
"""
