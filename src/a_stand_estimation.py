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
    out["density"] = out["n"] / (_GRID * _GRID)
    out = out[out["n"] >= min_pts].reset_index(drop=True)
    return out
