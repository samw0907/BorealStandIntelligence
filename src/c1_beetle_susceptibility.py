# boreal-stand-intelligence/src/c1_beetle_susceptibility.py
"""Module C1 - bark beetle stand susceptibility.

A stand-level case-control study of Ips typographus / insect-damage salvage in
spruce stands, by transparent logistic regression on the published Finnish
drivers (spruce share, tree size, stand age, site fertility, soil, distance to
prior damage; edge exposure and climatic water balance added in C1b). Reports a
coefficient table with confidence intervals and odds ratios, a precision-recall
curve and average precision (not accuracy - damage is rare), and a driver
ranking against published Finnish findings.

Why case-control and not a predictive susceptibility map (deviation from the
plan, 2026-08-29): clean leakage-free positives (stands whose inventory predates
their damage) number only ~20 in the SE AOI - too few to fit. Using the
contemporaneous inventory recovers ~585 damaged stands but their attributes are
partly re-measured after salvage. Matching each damaged stand to undamaged
spruce stands of the same measurement-year and locality balances that confound,
which a whole-AOI predictive fit cannot. The three stated C1 deliverables
(coefficient table, PR curve, driver ranking) are unchanged.

Data tiers: stand attributes and prior damage records FETCH; edge exposure and
climatic water balance DERIVE ONLY.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

BEETLE_DAMAGE_QUALIFIER = "1602"          # Ips typographus
INSECT_PRACTICE_CODES = {"22", "23"}      # insect-damage cutting realisation
SEEDLING_DEV_CLASSES = {"A0", "T1", "T2"}
_BLOCK_M = 5000


def _code(series: pd.Series) -> pd.Series:
    return series.astype("string").str.replace(r"\.0$", "", regex=True)


def beetle_declarations(decl):
    """Subset of a declarations GeoDataFrame that is beetle / insect-damage salvage."""
    mask = (_code(decl["FORESTDAMAGEQUALIFIER"]).eq(BEETLE_DAMAGE_QUALIFIER)
            | _code(decl["CUTTINGREALIZATIONPRACTICE"]).isin(INSECT_PRACTICE_CODES))
    return decl[mask].copy()


def c1_model_frame(
    stand_gpkg: str | Path,
    declarations_gpkg: str | Path,
    cfg: dict,
    *,
    target_years: tuple[int, int] = (2019, 2024),
    prior_cutoff_year: int = 2018,
    min_spruce: float = 0.2,
):
    """Assemble the C1 stand-level table over eligible spruce stands.

    Eligible: forest land, spruce proportion >= min_spruce, past the seedling
    stage, key attributes present. `damaged` = 1 if a beetle / insect-damage
    salvage declaration arriving in target_years falls inside the stand.
    `prior_damage_dist_m` = distance to the nearest such declaration arriving on
    or before prior_cutoff_year. `meas_year` and `block_id` support case-control
    matching in the fitting step (C1b).
    """
    import geopandas as gpd

    s = gpd.read_file(stand_gpkg)
    s = s[s["maingroup"].astype("string") == "1"]
    s = s[s["proportionspruce"].fillna(0.0) >= min_spruce]
    s = s[~s["developmentclass"].astype("string").isin(SEEDLING_DEV_CLASSES)]
    need = ["proportionspruce", "meanheight", "meandiameter", "meanage",
            "fertilityclass", "soiltype", "volume", "basalarea"]
    s = s[s[need].notna().all(axis=1)].copy()
    s["meas_year"] = pd.to_datetime(s["measurementdate"], utc=True,
                                    errors="coerce").dt.year

    decl = beetle_declarations(gpd.read_file(declarations_gpkg))
    yr = pd.to_numeric(decl["DECLARATIONARRIVALYEAR"], errors="coerce")
    dmg = decl[(yr >= target_years[0]) & (yr <= target_years[1])].copy()
    prior = decl[yr <= prior_cutoff_year].copy()

    dmg["geometry"] = dmg.geometry.centroid
    hit = gpd.sjoin(dmg[["geometry"]], s[["standid", "geometry"]],
                    predicate="within", how="inner")
    s["damaged"] = s["standid"].isin(set(hit["standid"])).astype(int)

    cent = s.copy()
    cent["geometry"] = cent.geometry.centroid
    if len(prior):
        pr = prior[["geometry"]].copy()
        pr["geometry"] = pr.geometry.centroid
        near = gpd.sjoin_nearest(cent[["standid", "geometry"]], pr,
                                 distance_col="prior_damage_dist_m", how="left")
        s = s.merge(near.drop_duplicates("standid")[["standid", "prior_damage_dist_m"]],
                    on="standid", how="left")
    else:
        s["prior_damage_dist_m"] = np.nan

    s["spruce_share"] = s["proportionspruce"].astype(float)
    s["site_fertility"] = pd.to_numeric(s["fertilityclass"], errors="coerce")
    s["soil_peat"] = (pd.to_numeric(s["soiltype"], errors="coerce") >= 60).astype(int)
    s["block_id"] = (
        (np.floor(cent.geometry.x / _BLOCK_M) * _BLOCK_M).astype("int64").astype(str)
        + "_"
        + (np.floor(cent.geometry.y / _BLOCK_M) * _BLOCK_M).astype("int64").astype(str)
    )
    return s.reset_index(drop=True)
