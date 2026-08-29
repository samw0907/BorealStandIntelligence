# Module A - notes, decisions and rationale

Running record of *why* Module A is built the way it is and *what the results
mean*, kept current as the module is built. Source material for the final README.

Companion planning doc: `PROJECT_1_BOREAL_STAND_INTELLIGENCE.md`, Module A section.

---

## 1. What Module A is

Rebuild the open-data half of Metsa's wood-trade offer tool: draw a stand
polygon, return the growing-stock attributes an offer needs (total and per-species
volume, mean height, basal area). The method is the one the Finnish sector
actually runs: **area-based regression** and **k-nearest-neighbour imputation**
from airborne laser scanning (ALS) height metrics, validated against the official
products (MS-NFI 2023, the Metsakeskus latvusmalli canopy height model).

Metsa's real tool adds a closed calibration loop against measured harvester
outturn and sawmill log measurement - that is their moat and is not reproducible
from open data. Module A rebuilds the open skeleton and names the missing half.

---

## 2. Design decisions

### 2.1 DERIVE AND BENCHMARK on a validation subset (three-tier rule)

The AOI is ~4,000 km2; reprocessing ~2 billion ALS points proves nothing extra
over deriving on a representative subset, quantifying agreement, then consuming
the official product at scale. Module A derives on the subset only.

### 2.2 Validation subset: `E_ruokolahti` (A0, 2026-08-29)

EPSG:3067 `[598000, 6805000, 610000, 6817000]` - 144 km2, near Ruokolahti /
Parikkala, well inside the AOI. Chosen because it is the one place where recent
stands and recent ALS coincide cleanly:

- **8,878 of 8,882 stands measured 2023** - one inventory epoch.
- **ALS entirely Parikkala 2023** ("products available") - matches the stands.
- Balanced **pine 46% / spruce 45%**, **peat soil 16%**, volume p10-p90
  1-276 m3/ha, height 3-22 m - a representative spread.
- Near the documented Ruokolahti bark-beetle monitoring site, so it also serves
  Module C.
- Fallback if 144 km2 is too heavy: an 81 km2 sub-box, near-identical composition.

Because ALS epoch (2023) matches stand-attribute epoch (2023), **Module A is a
clean "can open data + published methods reproduce the operational ALS-based
estimation" test - there is no inventory-drift dimension.** Inventory staleness
lives entirely in Module B's `inventory_stale` flag (stands elsewhere in the AOI
still on 2011-2012 data). This is how Decision D1 finally resolves.

### 2.3 ALS product and access

The 2020+ open 0.5 p laser scanning product (thinned from the 5 p national
programme; ~0.5 p/m2). Reached via the NLS OGC API Processes file service
`avoin-paikkatieto.maanmittauslaitos.fi/tiedostopalvelu/ogcproc/v1/`, which needs
a **free** NLS open-data API key (`NLS_API_KEY` in `config/.env`, gitignored,
never committed or logged; loaded by `fi_forest_data/config.py`).
The 2008-2019 legacy round (Funet mirror, key-free, ~1.6 p/m2 here) is the
documented fallback only.

### 2.4 Reference set

Metsakeskus stand attributes for the subset, restricted to
`treestanddatasource` in {4 interpreted, 5 laser} - i.e. stands whose attributes
come from ALS-based estimation. Codes 7 and 9 (~5% of stands, meaning not decoded)
are excluded. The 16 m grid-cell layer (`v2/gridcell`) is fetched too - it carries
per-species volumes, `LASERHEIGHT`/`LASERDENSITY`, and the operational k-NN
reference plot ids + weights, and is a second benchmark target.

### 2.5 Method constraints

- k-NN uses `sklearn.neighbors.NearestNeighbors` only, as a distance utility -
  not as an ML framework (CLAUDE.md).
- Area-based regression via ordinary least squares (statsmodels / numpy).
- Spatially-blocked cross-validation (5 km blocks), not random splits - adjacent
  stands are correlated and random splits inflate the scores.
- k-NN stratified by mineral vs peat soil, as MS-NFI does; start k = 5.

---

## 3. Method

(filled in as A1-A6 are built)

- **A1** fetch the 16 m grid-cell layer for the subset.
- **A2** fetch 0.5 p ALS for the subset, height-normalise against the 2 m DEM,
  compute per-16 m-cell metrics (height percentiles, canopy cover, return density).
- **A3** fetch the latvusmalli 1 m CHM; compare our ALS canopy metrics to it
  ("what does the paid 5 p buy").
- **A4** ABA regression + k-NN imputation, spatially-blocked CV.
- **A5** RMSE / bias by species and volume class, ABA vs k-NN; vs MS-NFI 2023;
  circularity check (with / without MS-NFI features); performance on Module B's
  `inventory_stale` stands.
- **A6** which attributes are estimable, the draw-a-polygon demo, report.json.

---

## 4. Results and what they mean

(filled in as A4-A6 complete)

---

## 5. Caveats and open items

- `treestanddatasource` codes 7 and 9 not decoded (minor - excluded from reference).
- The subset is one 144 km2 window in one AOI - single-subset result.
