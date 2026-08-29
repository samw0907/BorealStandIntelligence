# boreal-stand-intelligence/fi_forest_data/luke.py
"""Luke (Natural Resources Institute Finland) data.

Fetches MS-NFI multi-source national forest inventory rasters (16 m, EPSG:3067,
delivered by UTM200 map sheets, most recent set 2023) and the DTW depth-to-water
rasters (0.5, 1, 4, 10 ha thresholds). MS-NFI nodata values 32766 (forestry land
without satellite cover) and 32767 (not forestry land or outside country) have
different meanings and must not be collapsed.

Public interface (planned):
    fetch_msnfi(theme, aoi, year=2023) -> str   # path to mosaicked COG
    fetch_dtw(threshold_ha, aoi) -> str         # path to COG

Routes confirmed in TASK 00 (docs/DATA_SOURCES.md sections 2 and 3):
- MS-NFI 2023: one whole-Finland GeoTIFF per theme on the Funet mirror
  https://www.nic.funet.fi/index/geodata/luke/vmi/2023/{theme}_vmi1x_1923.tif
  (UInt16, 16 m, EPSG:3067, nodata 32767; window via /vsicurl, not mapsheet-tiled).
- DTW: Funet mirror https://www.nic.funet.fi/index/geodata/luke/dtw/{2019|2023}/
  (Int16, 2 m, mapsheet GeoTIFF tiles + tile-index shapefile). 2019 unit = mm
  (metres x 1000); 2023 "CMv2" unit = cm (metres x 100), thresholds 0.5/1/2/4/10 ha.
  fetch_dtw must apply the vintage-correct scale.

No implementation yet — scaffold only.
"""
