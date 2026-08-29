# boreal-stand-intelligence/fi_forest_data/fmi.py
"""Finnish Meteorological Institute (FMI) open data.

Fetches daily weather observations (minimum and mean temperature, precipitation,
snow depth) from the FMI WFS at opendata.fmi.fi, and lists stations near an AOI.
Used by Module C1 for climatic water balance.

Public interface (planned):
    fetch_daily(station_id, start, end, variables) -> pd.DataFrame
    stations_near(aoi, max_distance_km) -> pd.DataFrame

Route confirmed in TASK 00 (docs/DATA_SOURCES.md section 5): open WFS
https://opendata.fmi.fi/wfs, stored query
fmi::observations::weather::daily::simple (default params rrday, tday, snow, tmin,
tmax). Query by fmisid + starttime/endtime; the request span is capped at ~1 year,
so page by year. Project 2 long-record station: fmisid 101537 (Viitasaari
Haapaniemi, daily from 1970).

No implementation yet — scaffold only.
"""
