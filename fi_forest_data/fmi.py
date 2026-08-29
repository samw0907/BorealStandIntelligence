# boreal-stand-intelligence/fi_forest_data/fmi.py
"""Finnish Meteorological Institute (FMI) open data.

Fetches daily weather observations (minimum and mean temperature, precipitation,
snow depth) from the FMI WFS at opendata.fmi.fi, and lists stations near an AOI.
Used by Module C1 for climatic water balance.

Public interface (planned):
    fetch_daily(station_id, start, end, variables) -> pd.DataFrame
    stations_near(aoi, max_distance_km) -> pd.DataFrame

No implementation yet — scaffold only. WFS stored query names and parameter
syntax are TO VERIFY in docs/DATA_SOURCES.md and are resolved by TASK 00.
"""
