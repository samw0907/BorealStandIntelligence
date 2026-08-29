# boreal-stand-intelligence/fi_forest_data/fmi.py
"""Finnish Meteorological Institute (FMI) open data.

Daily weather observations from the FMI WFS (opendata.fmi.fi, no key), stored
query fmi::observations::weather::daily::simple: rrday (precip, -1 = dry), tday
(mean T), tmin, tmax, snow. Query by fmisid + starttime/endtime; the span is
capped near a year, so fetch_daily pages by calendar year.

    stations_near(aoi, max_distance_km=40) -> DataFrame[fmisid, name, lat, lon]
    fetch_daily(fmisid, start, end, variables=...) -> DataFrame indexed by date

Used by P2 D/D2/D3 (root-rot temperature rules, frozen-season length). `fetch_daily`
is functional; `stations_near` currently returns the whole network and needs a
client-side distance filter - finished and validated in Project 2 prep where FMI
is load-bearing. P1 C1 does not use a climatic predictor: the SE AOI is too small
for summer weather to vary meaningfully across it, so the 2018 drought is a
temporal trigger for the outbreak, not a spatial driver of its pattern (see
docs/MODULE_C_NOTES.md).
"""

from __future__ import annotations

import datetime as _dt
import xml.etree.ElementTree as ET

import pandas as pd
import requests

WFS = "https://opendata.fmi.fi/wfs"
_DAILY_QUERY = "fmi::observations::weather::daily::simple"
_STATION_QUERY = "fmi::ef::stations"
_DEFAULT_VARS = ("rrday", "tday", "tmin", "tmax")
_NS = {
    "wfs": "http://www.opengis.net/wfs/2.0",
    "BsWfs": "http://xml.fmi.fi/schema/wfs/2.0",
    "gml": "http://www.opengis.net/gml/3.2",
    "ef": "http://inspire.ec.europa.eu/schemas/ef/4.0",
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gco": "http://www.isotc211.org/2005/gco",
}


def _get(params: dict, *, session=None) -> ET.Element:
    r = (session or requests).get(WFS, params=params, timeout=120)
    r.raise_for_status()
    return ET.fromstring(r.content)


def stations_near(aoi, max_distance_km: float = 40.0, *, session=None) -> pd.DataFrame:
    """FMI weather stations within max_distance_km of the AOI (WGS84 bbox query)."""
    from pyproj import Transformer

    minx, miny, maxx, maxy = aoi.bbox_3067
    pad = max_distance_km * 1000
    t = Transformer.from_crs("EPSG:3067", "EPSG:4326", always_xy=True)
    lon0, lat0 = t.transform(minx - pad, miny - pad)
    lon1, lat1 = t.transform(maxx + pad, maxy + pad)
    root = _get({
        "service": "WFS", "version": "2.0.0", "request": "getFeature",
        "storedquery_id": _STATION_QUERY,
        "bbox": f"{lat0},{lon0},{lat1},{lon1}",
    }, session=session)

    rows = []
    for ef in root.iter("{http://inspire.ec.europa.eu/schemas/ef/4.0}EnvironmentalMonitoringFacility"):
        name_el = ef.find(".//gml:name", _NS)
        pos = ef.find(".//gml:pos", _NS)
        fmisid = None
        for ident in ef.iter("{http://www.opengis.net/gml/3.2}identifier"):
            if ident.text and ident.text.strip().isdigit():
                fmisid = ident.text.strip()
        if pos is None or fmisid is None:
            continue
        lat, lon = (float(v) for v in pos.text.split()[:2])
        rows.append({"fmisid": fmisid,
                     "name": name_el.text if name_el is not None else "",
                     "lat": lat, "lon": lon})
    return pd.DataFrame(rows).drop_duplicates("fmisid").reset_index(drop=True)


def _fetch_year(fmisid, start, end, variables, *, session) -> pd.DataFrame:
    root = _get({
        "service": "WFS", "version": "2.0.0", "request": "getFeature",
        "storedquery_id": _DAILY_QUERY, "fmisid": str(fmisid),
        "starttime": start, "endtime": end, "parameters": ",".join(variables),
    }, session=session)
    recs = []
    for el in root.iter("{http://xml.fmi.fi/schema/wfs/2.0}BsWfsElement"):
        t = el.find("BsWfs:Time", _NS).text
        name = el.find("BsWfs:ParameterName", _NS).text
        val = el.find("BsWfs:ParameterValue", _NS).text
        recs.append((t[:10], name, float(val) if val not in (None, "NaN") else None))
    if not recs:
        return pd.DataFrame(columns=list(variables))
    df = pd.DataFrame(recs, columns=["date", "param", "value"])
    return df.pivot_table(index="date", columns="param", values="value")


def fetch_daily(fmisid, start: str, end: str,
                variables=_DEFAULT_VARS, *, session=None) -> pd.DataFrame:
    """Daily observations for one station, start/end as YYYY-MM-DD, paged by year."""
    s = _dt.date.fromisoformat(start)
    e = _dt.date.fromisoformat(end)
    frames = []
    for yr in range(s.year, e.year + 1):
        y0 = max(s, _dt.date(yr, 1, 1)).isoformat() + "T00:00:00Z"
        y1 = min(e, _dt.date(yr, 12, 31)).isoformat() + "T00:00:00Z"
        frames.append(_fetch_year(fmisid, y0, y1, variables, session=session))
    out = pd.concat(frames) if frames else pd.DataFrame(columns=list(variables))
    out.index = pd.to_datetime(out.index)
    out.index.name = "date"
    return out.sort_index()
