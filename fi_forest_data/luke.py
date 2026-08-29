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

No implementation yet — scaffold only. Download mechanism and theme filenames
are TO VERIFY in docs/DATA_SOURCES.md and are resolved by TASK 00.
"""
