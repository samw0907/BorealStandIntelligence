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

Routes confirmed in TASK 00 (docs/DATA_SOURCES.md section 4):
- Funet mirror https://www.nic.funet.fi/index/geodata/mml/ (no key) for the 2 m
  DEM (dem2m/2008_latest/...), the topographic database
  (maastotietokanta/2025/ per-mapsheet-block dirs), and the 2008-2019 legacy laser
  round (fallback only).
- NLS OGC API https://avoin-paikkatieto.maanmittauslaitos.fi/ for the 2020+ open
  0.5 p ALS (P1 Module A). Needs a FREE key (open CC BY 4.0 data). The key is read
  from an environment variable / .env that is gitignored and never committed; this
  module must not write or log it. The SE AOI is fully covered by 2019-2023
  national-programme flights (Decision D1, docs/TASK_00_FINDINGS.md).

No implementation yet — scaffold only.
"""
