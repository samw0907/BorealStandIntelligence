# boreal-stand-intelligence/src/a_stand_estimation.py
"""Module A - stand attribute estimation from open data.

Rebuild the open-data half of Metsa's wood-trade offer tool: ALS height metrics
-> volume and species via area-based regression and k-NN imputation (the MS-NFI
method), validated against MS-NFI 2023, the latvusmalli CHM, and the Metsakeskus
grid-cell operational estimates, on the E_ruokolahti validation subset.

Data tiers: stand boundaries and grid cells FETCH; ALS and 2 m DEM DERIVE input;
MS-NFI volume and latvusmalli DERIVE AND BENCHMARK.

Built step by step:
- A2b  als_cell_metrics    -> per-16 m-cell ALS metrics (this file, first)
- A3   CHM benchmark
- A4   ABA regression + k-NN imputation
- A5   validation and benchmarks
- A6   estimable attributes, the draw-a-polygon demo, report.json

See docs/MODULE_A_NOTES.md.
"""

from __future__ import annotations

from pathlib import Path

import laspy
import numpy as np
import pandas as pd
import rasterio

_GRID = 16  # Metsakeskus / MS-NFI 16 m grid, aligned to origin (0, 0)


def _sample_dem(dem_path: str | Path, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Bilinearly sample a DEM at point locations (EPSG:3067)."""
    with rasterio.open(dem_path) as src:
        arr = src.read(1).astype("float64")
        nod = src.nodata
        inv = ~src.transform
        col, row = inv * (x, y)
    arr[arr == nod] = np.nan
    r0 = np.floor(row).astype(int)
    c0 = np.floor(col).astype(int)
    fr = row - r0
    fc = col - c0
    h, w = arr.shape
    ok = (r0 >= 0) & (r0 < h - 1) & (c0 >= 0) & (c0 < w - 1)
    out = np.full(x.shape, np.nan)
    r0o, c0o, fro, fco = r0[ok], c0[ok], fr[ok], fc[ok]
    v = (arr[r0o, c0o] * (1 - fro) * (1 - fco)
         + arr[r0o, c0o + 1] * (1 - fro) * fco
         + arr[r0o + 1, c0o] * fro * (1 - fco)
         + arr[r0o + 1, c0o + 1] * fro * fco)
    out[ok] = v
    return out


def als_cell_metrics(
    laz_paths: list[str | Path],
    dem_path: str | Path,
    bbox_3067: tuple[float, float, float, float],
    cfg: dict,
) -> pd.DataFrame:
    """Per-16 m-cell area-based ALS metrics over the bbox.

    Returns one row per cell with: cx, cy (cell SW corner, EPSG:3067), n points,
    height percentiles, mean/max height, canopy cover (fraction of first returns
    above canopy_threshold_m), and point density (points / m2).
    Cells with fewer than min_points_per_cell points are dropped.
    """
    a = cfg["module_a_stand_estimation"]["als"]
    pcts = list(a["percentiles"])
    cc_thr = float(a["canopy_threshold_m"])
    min_pts = int(a["min_points_per_cell"])
    minx, miny, maxx, maxy = bbox_3067

    xs, ys, zs, rn, cls = [], [], [], [], []
    for p in laz_paths:
        las = laspy.read(str(p))
        x = np.asarray(las.x)
        y = np.asarray(las.y)
        m = (x >= minx) & (x < maxx) & (y >= miny) & (y < maxy)
        if not m.any():
            continue
        xs.append(x[m])
        ys.append(y[m])
        zs.append(np.asarray(las.z)[m])
        rn.append(np.asarray(las.return_number)[m])
        cls.append(np.asarray(las.classification)[m])
    x = np.concatenate(xs)
    y = np.concatenate(ys)
    z = np.concatenate(zs)
    rn = np.concatenate(rn)
    cls = np.concatenate(cls)

    # height above ground, from the NLS 2 m DEM
    ground = _sample_dem(dem_path, x, y)
    hgt = z - ground
    keep = np.isfinite(hgt) & (hgt > -1.0) & (hgt < 50.0) & (cls != 7) & (cls != 18)
    x, y, hgt, rn = x[keep], y[keep], hgt[keep], rn[keep]

    cx = (np.floor(x / _GRID) * _GRID).astype("int64")
    cy = (np.floor(y / _GRID) * _GRID).astype("int64")
    cell = cx.astype("int64") * 10_000_000 + cy  # composite key

    df = pd.DataFrame({"cell": cell, "cx": cx, "cy": cy, "h": hgt,
                       "first": (rn == 1), "veg": hgt > cc_thr})
    g = df.groupby("cell")

    out = g.agg(cx=("cx", "first"), cy=("cy", "first"), n=("h", "size"),
                h_mean=("h", "mean"), h_max=("h", "max")).reset_index(drop=True)
    q = g["h"].quantile([p / 100 for p in pcts]).unstack()
    q.columns = [f"h_p{p}" for p in pcts]
    out = pd.concat([out, q.reset_index(drop=True)], axis=1)
    # canopy cover: first returns above threshold / all first returns
    firsts = df[df["first"]].groupby("cell")
    cc = (firsts.apply(lambda d: (d["h"] > cc_thr).mean(), include_groups=False)
          .rename("canopy_cover").reset_index(drop=True))
    out = pd.concat([out, cc], axis=1)
    # a cell can hold points but no first returns (rare) -> no cover, read as 0
    out["canopy_cover"] = out["canopy_cover"].fillna(0.0)
    out["density"] = out["n"] / (_GRID * _GRID)
    out = out[out["n"] >= min_pts].reset_index(drop=True)
    return out


# ---------------------------------------------------------------------------
# A3 - latvusmalli (canopy height model) benchmark
# ---------------------------------------------------------------------------

CHM_UUSIN_URL = ("https://avoin.metsakeskus.fi/aineistot/Latvusmalli/Karttalehti/"
                 "uusin/CHM_{sheet}_uusin.tif")


def chm_cell_stats(chm_sources: list[str], bbox_3067, *, grid: int = _GRID) -> pd.DataFrame:
    """Aggregate the 1 m latvusmalli CHM to the 16 m grid over the bbox.

    chm_sources: local paths or `/vsicurl/...` URLs to CHM map-sheet GeoTIFFs.
    Returns cx, cy, chm_mean, chm_p90, chm_max, chm_cover (fraction of 1 m pixels
    above 2 m) per 16 m cell.
    """
    minx, miny, maxx, maxy = bbox_3067
    acc: dict[tuple[int, int], list[np.ndarray]] = {}
    for src in chm_sources:
        with rasterio.open(src) as ds:
            win = ds.window(minx, miny, maxx, maxy)
            arr = ds.read(1, window=win, boundless=True, fill_value=np.nan).astype("float32")
            wt = ds.window_transform(win)
            nod = ds.nodata
        if nod is not None:
            arr[arr == nod] = np.nan
        rows, cols = arr.shape
        # world coords of each pixel centre
        jj, ii = np.meshgrid(np.arange(cols), np.arange(rows))
        xw = wt.c + (jj + 0.5) * wt.a
        yw = wt.f + (ii + 0.5) * wt.e
        cx = (np.floor(xw / grid) * grid).astype("int64")
        cy = (np.floor(yw / grid) * grid).astype("int64")
        inb = (xw >= minx) & (xw < maxx) & (yw >= miny) & (yw < maxy) & np.isfinite(arr)
        for k, v in _group_pixels(cx[inb], cy[inb], arr[inb]):
            acc.setdefault(k, []).append(v)

    rows_out = []
    for (kx, ky), chunks in acc.items():
        v = np.concatenate(chunks)
        rows_out.append({
            "cx": kx, "cy": ky, "chm_n": v.size,
            "chm_mean": float(np.mean(v)), "chm_p90": float(np.percentile(v, 90)),
            "chm_max": float(np.max(v)), "chm_cover": float((v > 2.0).mean()),
        })
    return pd.DataFrame(rows_out)


def _group_pixels(cx: np.ndarray, cy: np.ndarray, val: np.ndarray):
    key = cx.astype("int64") * 10_000_000 + cy
    order = np.argsort(key, kind="stable")
    key, cx, cy, val = key[order], cx[order], cy[order], val[order]
    bounds = np.flatnonzero(np.diff(key)) + 1
    for a, b in zip(np.r_[0, bounds], np.r_[bounds, key.size]):
        yield (int(cx[a]), int(cy[a])), val[a:b]


# ---------------------------------------------------------------------------
# A4 - modelling table: stand attributes + stand-aggregated ALS metrics
# ---------------------------------------------------------------------------

ALS_FEATURES = ["h_mean", "h_max", "h_p25", "h_p50", "h_p75", "h_p90", "h_p95",
                "canopy_cover", "density"]
TARGETS = ["vol_total", "vol_pine", "vol_spruce", "vol_other", "basalarea",
           "meanheight", "meandiameter", "meanage", "sawlogvolume",
           "pulpwoodvolume", "stemcount", "volumegrowth"]


def stand_model_frame(
    stand_gpkg: str | Path,
    als_metrics_csv: str | Path,
    cfg: dict,
    *,
    min_cells: int = 8,
):
    """Join ALS 16 m cell metrics up to stand level and attach stand attributes.

    Reference stands only: treestanddatasource in {4 interpreted, 5 laser},
    maingroup 1 (forest land), non-null volume. ALS features are the per-stand
    median of each cell metric over cells whose centre falls inside the stand;
    stands with fewer than min_cells covered cells are dropped. Adds
    soil_main_type (mineral/peat) and a 5 km spatial-block id for blocked CV.
    Returns a GeoDataFrame, one row per stand.
    """
    import geopandas as gpd

    m = cfg["module_a_stand_estimation"]
    blk = int(m["cv"]["block_size_km"]) * 1000

    s = gpd.read_file(stand_gpkg)
    s = s[s["treestanddatasource"].astype("string").isin(["4", "5"])]
    s = s[s["maingroup"].astype("string") == "1"]
    s = s[s["volume"].notna()].copy()

    cells = pd.read_csv(als_metrics_csv)
    pts = gpd.GeoDataFrame(
        cells,
        geometry=gpd.points_from_xy(cells["cx"] + _GRID / 2, cells["cy"] + _GRID / 2),
        crs="EPSG:3067",
    )
    j = gpd.sjoin(pts, s[["standid", "geometry"]], predicate="within", how="inner")
    agg = j.groupby("standid")[ALS_FEATURES].median()
    agg["n_cells"] = j.groupby("standid").size()
    agg = agg[agg["n_cells"] >= min_cells]

    df = s.set_index("standid").join(agg, how="inner")

    p_pine = df["proportionpine"].fillna(0.0)
    p_spruce = df["proportionspruce"].fillna(0.0)
    p_other = df["proportionother"].fillna(0.0)
    df["vol_total"] = df["volume"]
    df["vol_pine"] = df["volume"] * p_pine
    df["vol_spruce"] = df["volume"] * p_spruce
    df["vol_other"] = df["volume"] * p_other

    st = pd.to_numeric(df["soiltype"], errors="coerce")
    df["soil_main_type"] = np.where(st >= 60, "peat", "mineral")

    cent = df.geometry.centroid
    bx = (np.floor(cent.x / blk) * blk).astype("int64")
    by = (np.floor(cent.y / blk) * blk).astype("int64")
    df["block_id"] = bx.astype(str) + "_" + by.astype(str)

    return df.reset_index()
