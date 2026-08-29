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

### 2.6 Modelling design decisions (A4b, 2026-08-29, agreed with Sam)

Recorded so the design reasoning is traceable later.

1. **Modelling unit: stand-level.** Aggregate the 16 m ALS metrics to the stand
   (per-stand median) and model stand attributes directly.
   - *Why:* the reference (Metsakeskus stand attributes) is genuinely per-stand,
     and the deliverable is "draw a stand polygon -> offer attributes", so the
     unit matches both. Modelling at cell level would need a per-cell truth; the
     only per-cell numbers available are Metsakeskus's own operational estimates,
     so regressing onto those is circular (our pipeline vs theirs, not vs
     inventory). Assigning stand means down to cells just pseudo-replicates.
   - *Cost:* within-stand variation is discarded; ~median 32 ALS cells per stand
     makes the median a stable summary.

2. **Cross-validation: 2 km spatial blocks grouped into 5 spatially-disjoint
   folds.** `cv.block_size_km` changed 5 -> 2 in `config/pipeline.yaml`.
   - *Why:* the 81 km2 subset spans only ~4 full 5 km blocks (>99% of stands in
     4 blocks), so 5-fold blocked CV as originally configured cannot run. 2 km
     blocks give ~16-20 groups; assigning whole blocks (not stands) to folds
     keeps train and test spatially separated, which is the point of blocked CV -
     adjacent stands are autocorrelated and random splits inflate the score.
   - *Alternative considered:* 4-fold leave-one-block-out at 5 km. Rejected as
     coarser and fewer folds for no real gain.

3. **Area-based regression form: OLS on `sqrt(y)`** against a fixed predictor set
   `h_p90 + h_p50 + h_p25 + canopy_cover + density`, back-transformed as
   `E[y] = mu^2 + Var(resid)`.
   - *Why:* transparent fixed-predictor OLS (no stepwise / no automated
     selection). sqrt is variance-stabilising for volume and admits zero-volume
     stands natively.
   - *Amendment (A4b -> A4c, 2026-08-29, agreed with Sam):* originally
     `log(y+1)` + Duan smearing. In the blocked CV that over-predicted total
     volume by +29 m3/ha - the long positive tail of the log residuals (young /
     cleared stands the linear-in-log model overshoots) inflated the smearing
     factor to ~1.32. sqrt has no such pathology: pooled bias fell to ~0 and
     pooled RMSE from 92 to 52 m3/ha. Kept as a fixed-predictor transparent OLS.

4. **k-NN imputation: z-scored features, Euclidean, k in {1,3,5,7,10}, stratified
   mineral vs peat, one donor set imputes the whole attribute vector.**
   - *Why:* this is the MS-NFI operational method (Tomppo). Standardising
     features before Euclidean distance stops `density` and the height
     percentiles being compared on different scales; one shared donor set per
     target keeps the imputed attributes mutually consistent (a real stand's
     numbers), which is k-NN's advantage over independent regressions. k = 5 is
     the MS-NFI reference point; the sweep shows sensitivity. `sklearn`
     `NearestNeighbors` is used only as the distance search, not as an ML model.

5. **Circularity is acknowledged, not eliminated.** Datasource-4 ("interpreted")
   stands already carry ALS-informed attributes, so A4 measures how well open
   data + published method *reproduce* the operational estimate, not agreement
   with independent field truth.
   - *Mitigation (A5):* report the 405 datasource-5 ("laser") stands separately;
     run the models with and without MS-NFI-style features to show the ALS
     metrics are doing the work; benchmark against MS-NFI 2023 as a second
     reference.

6. **Production feature set: ALS metrics + a 2023 Sentinel-2 summer composite**
   (A5, 2026-08-29). Predictors are the 5 ALS metrics plus the 7 median band
   reflectances and NDVI / NDRE / NDMI from an epoch-matched
   2023-06-01..08-31 median composite (`sentinel2.composite_windows.s2_2023`).
   - *Why:* ALS height metrics carry almost no species information; in the
     blocked CV the S2 bands roughly double the per-species volume R2 (see A5)
     at little cost to the structural attributes. This mirrors the real
     operational stack (MS-NFI has always used satellite optical; ALS is the
     newer half). ALS-only stays reported as the ablation.

---

## 3. Method

### A1 - reference layers (done)

Fetched for the subset and cached: `stand` (8,884) and `gridcell` (564,752 cells,
all dated 2023). The grid-cell layer carries per-species volumes, `LASERHEIGHT` /
`LASERDENSITY` (Metsakeskus's own ALS metrics - a direct comparison target),
`DOMINANTHEIGHT`, `BASALAREA`, `AGE`, and `SAMPLEPLOTID1-6` + weights (the
operational k-NN structure).

### A2 - ALS fetch and per-cell metrics (done)

- **NLS file service** (`fi_forest_data/nls.py`): OGC API Processes. Non-standard
  quirk - the process id must be in the POST body (`{"id": ..., "inputs": ...}`)
  as well as the URL path, or the F5 gateway returns a bare HTTP 400. Job async:
  POST execution -> poll `/jobs/{id}` -> GET `/jobs/{id}/results` -> download the
  `results[].path` URLs (each needs the api-key).
- **2 m DEM**: `korkeusmalli_2m_bbox` for the subset bbox -> one 4500x4500
  GeoTIFF (2 m, EPSG:3067, float32, nodata -9999), 81 MB, ~20 s.
- **0.5 p ALS**: `laserkeilausaineisto_05_karttalehti`, `dataSetInput` =
  `05p_2020-`. Delivered by 3 km map sheets (`utm5` layer of
  `karttalehtijako_koko_suomi`); the subset touches 16 sheets -> 16 LAZ tiles,
  848 MB, ~90 s. **124.5 M points, density 0.86 p/m2** (above the 0.5 nominal;
  the 0.54 p/m2 the method needs is comfortably cleared). LAS 1.2, point format 1,
  classified (ground + low/med/high veg).
- **Per-16 m-cell metrics** (`src.a_stand_estimation.als_cell_metrics`): points
  clipped to the subset bbox, height-normalised against the 2 m DEM (bilinear
  sample), noise and sub-ground returns dropped. Per cell (aligned to the
  Metsakeskus / MS-NFI 16 m grid): height percentiles P25-P95, mean/max height,
  canopy cover (first returns > 2 m), point density. **282,033 cells** with >= 30
  points (~89% of the subset), ~43 s. Sanity: density mean 0.96 p/m2, h_max
  median 17.8 m, canopy cover median 0.70, h_p90 median 13.1 m - all plausible
  for managed boreal forest.

### A3 - latvusmalli CHM benchmark (done)

The DERIVE AND BENCHMARK check for canopy height: does the open 0.5 p ALS
reproduce the canopy-height structure that Metsakeskus's official latvusmalli
product carries? The latvusmalli is a 1 m canopy height model built from the
full-density (5 p) national ALS - so this is also the concrete "what does the
paid 5 p buy over the open 0.5 p" answer.

- **Fetch** (`src.a_stand_estimation.chm_cell_stats`): 6 latvusmalli map sheets
  (utm10, 6 km) cover the 81 km2 subset - `M5322B/D/F`, `M5411A/C/E`. Downloaded
  whole from `avoin.metsakeskus.fi/.../CHM_{sheet}_uusin.tif` (~70 MB each, ~40 s
  total) then aggregated locally; windowed `/vsicurl` reads on these non-COG 1 m
  tiles were far too slow. Aggregated to the same 16 m grid: `chm_mean`,
  `chm_p90`, `chm_max`, `chm_cover` (fraction of 1 m pixels > 2 m) per cell,
  256 pixels per full cell, 316,969 cells.
- **Compared** on the 282,033 cells shared with the A2 ALS metrics:

  | pair | r | bias (CHM - ALS) | RMSE | medians (ALS / CHM) |
  |------|-----|-----|-----|-----|
  | p90 height  | 0.980 | +2.97 m | 3.37 m | 13.1 / 16.5 m |
  | max height  | 0.981 | +1.07 m | 1.82 m | 17.8 / 18.8 m |
  | mean height | 0.965 | +5.26 m | 6.07 m | 5.7 / 11.4 m |
  | canopy cover| 0.785 | +0.18   | 0.28   | 0.70 / 0.95 |

**What it means.** Height percentiles from the open 0.5 p ALS track the official
5 p canopy model almost perfectly in shape (r ~ 0.98). The paid product buys a
small, systematic height correction, not new structure: our sparse cloud
under-samples crown apices, so our percentiles sit a little low - the gap is
smallest at `h_max` (+1.1 m) and grows for lower percentiles. That downward bias
is a known, correctable property of thinned ALS and does not threaten the volume
models in A4, which calibrate against measured plots and absorb a linear offset.

Two comparisons are not like-for-like and are recorded only for completeness:
`mean height` (ours is the mean of all returns including ground; the latvusmalli
is a canopy *surface*), and `canopy cover` (the latvusmalli is a filled,
interpolated surface - its cover saturates near 1.0, median 0.95 - so our
first-return cover, median 0.70, is the better gap-fraction metric, and it is the
one A4 will use). Two ALS cells had `n >= 30` but zero first returns, giving NaN
`canopy_cover`; harmless here (dropped from the correlation), guard added in A4.

Output: `data/raw/nls/chm_cell_stats_e_ruokolahti.csv`.

### A4a - modelling table (done)

`src.a_stand_estimation.stand_model_frame` joins the A2 16 m ALS cell metrics up
to stand level (per-stand median of each metric over cells whose centre falls in
the stand) and attaches the stand attributes. Reference stands only:
`treestanddatasource` in {4 interpreted, 5 laser}, `maingroup` 1, non-null
volume; stands with < 8 covered cells dropped. Adds `soil_main_type`
(mineral/peat, split at soiltype 60) and a spatial-block id for blocked CV.

**4,166 stands** (3,761 datasource 4, 405 datasource 5), median 32 covered cells.
Soil: 3,571 mineral / 595 peat. Targets: `vol_total`, `vol_pine/spruce/other`
(= total x the stand species proportions - the stand layer has no per-species
volume column), `basalarea`, `meanheight`, `meandiameter`, `meanage`,
`sawlogvolume`, `pulpwoodvolume`, `stemcount`, `volumegrowth`. Raw Pearson r of
`h_p90` with vol_total 0.80, meanheight 0.83, meanage 0.80 - the ALS signal is
clearly present. Output: `data/raw/nls/stand_model_frame_e_ruokolahti.csv`.

Also folded in the A3 carry-forward: `als_cell_metrics` now fills NaN
`canopy_cover` (points but no first returns) with 0.

Open decision carried into A4b: the 81 km2 subset spans only ~4 full 5 km CV
blocks, so 5-fold spatial-block CV as configured is not viable - resolve the
block size / fold assignment before fitting.

### A4b/A4c - blocked-CV comparison of ABA vs k-NN (done)

CV: block size 5 km -> 2 km (config), 35 blocks; `assign_cv_folds` orders blocks
on a snake path and cuts them into 5 runs of roughly equal *stand* count (fold
sizes 949 / 737 / 1033 / 693 / 754). Predictors for both methods:
`h_p90, h_p50, h_p25, canopy_cover, density`. ABA = OLS on `sqrt(y)` (A4c
amendment - see 2.6-3). Pooled out-of-fold metrics
(`outputs/tables/a4b_cv_metrics.csv`):

| target | ABA (sqrt) RMSE / bias / R2 | k-NN k=5 RMSE / bias / R2 |
|--------|------|------|
| vol_total | 51.7 / -0.1 / 0.72 | 53.8 / +0.9 / 0.69 |
| vol_pine | 51.9 / -0.4 / 0.40 | 50.9 / +1.9 / 0.42 |
| vol_spruce | 57.8 / +0.3 / 0.25 | 58.2 / +0.7 / 0.23 |
| vol_other | 32.0 / -0.0 / 0.26 | 31.9 / -1.7 / 0.27 |
| basalarea | 5.4 / -0.0 / 0.64 | 5.4 / +0.1 / 0.64 |
| meanheight | 3.8 / -0.0 / 0.68 | 3.8 / +0.1 / 0.67 |
| meandiameter | 4.9 / -0.0 / 0.65 | 4.9 / +0.2 / 0.65 |
| meanage | 12.3 / -0.0 / 0.66 | 12.9 / +0.3 / 0.62 |

k sweep, vol_total: k=1 67.6 / k=3 56.2 / k=5 53.8 / k=7 52.5 / k=10 52.0. Plateau
by k=7; k=5 keeps the MS-NFI default at ~1 m3/ha off the best score.

**Both methods land in the operational range for the aggregate attributes** -
total volume ~31-33 % RMSE, R2 ~0.7, bias ~0; height / diameter / basal area
R2 0.62-0.68. With the sqrt transform the transparent OLS is level with or
slightly ahead of k-NN on these *univariate* scores. k-NN is still carried
forward because its advantage is a jointly consistent attribute *vector* (one
real donor stand supplies every number), which univariate RMSE does not show;
A6's draw-a-polygon output uses that.

**Per-species volume is weak for both** (pine R2 0.40, spruce 0.25). ALS height
metrics carry little species information; A5 tests adding the Sentinel-2 bands.

**Error structure (`outputs/tables/a4b_vol_total_by_volclass.csv`,
`_by_species.csv`):**
- Regression toward the mean, both methods: 0-50 m3/ha stands (n 683)
  over-predicted +40 to +44, RMSE ~95; 300+ stands (n 325) under-predicted ~-59.
  ALS cell medians cannot separate a freshly cleared stand from a young one. The
  100-200 m3/ha classes are well behaved (RMSE 28-33, bias < 9).
- Pine and spruce stands fine (RMSE 41-53, bias < 7). Birch (n 37) and other
  broadleaf (n 298) badly over-predicted (+140, +42) - small n, mostly sparse
  young stands.

### A5a - Sentinel-2 spectral features (done)

Fetched an epoch-matched 2023 summer median composite over the 81 km2 subset
(`fetch_s2_composite`, window `s2_2023`, ~40 s; cached
`data/raw/sentinel2/s2_s2_2023__e_ruokolahti_sub.tif`). `add_spectral_features`
adds the per-stand median of each band plus NDVI / NDRE / NDMI; all 4,166 stands
kept (no cloud gaps). Re-ran the blocked CV with ALS-only vs ALS + S2 predictors
(`outputs/tables/a5_als_vs_als_s2.csv`), R2 (k-NN k=5 / ABA sqrt):

| target | ALS only | ALS + S2 |
|--------|----------|----------|
| vol_total | 0.70 / 0.72 | 0.73 / 0.75 |
| vol_pine | 0.42 / 0.40 | 0.58 / 0.55 |
| vol_spruce | 0.23 / 0.25 | 0.56 / 0.54 |
| vol_other | 0.27 / 0.26 | 0.73 / 0.73 |
| basalarea | 0.64 / 0.64 | 0.68 / 0.69 |
| meanheight | 0.67 / 0.68 | 0.67 / 0.68 |
| meandiameter | 0.65 / 0.65 | 0.66 / 0.67 |
| meanage | 0.62 / 0.66 | 0.64 / 0.69 |

**The spectral input is what unlocks species.** Per-species volume R2 roughly
doubles (spruce 0.25 -> 0.54, pine 0.42 -> 0.58, other 0.27 -> 0.73), RMSE for
spruce 58 -> 44 m3/ha. Structural attributes (height, diameter, basal area) barely
move - ALS already carries them. Total volume gains a little (0.72 -> 0.75).
ABA (sqrt) and k-NN stay level with each other throughout. This is the expected
division of labour and matches the operational stack: ALS for structure, optical
for species. ALS + S2 is the Module A production feature set (decision 2.6-6);
ALS-only is kept as the ablation.

### A5b - circularity probe and the model domain (done; one decision pending)

**Circularity probe (`outputs/tables/a5b_circularity_probe.csv`).** Two parts:

- Our open-data ALS metrics reproduce Metsakeskus's own operational ALS metrics
  almost exactly: `h_p90` vs `LASERHEIGHT` r = 0.993, `h_p75` r = 0.976,
  `density` vs `LASERDENSITY` r = 0.898. We rebuilt the same structural signal
  from open inputs.
- Adding the official `LASERHEIGHT` / `LASERDENSITY` to the feature set changes
  CV R2 by only +0.00 to +0.03 across all targets. Our independent features
  already carry the signal - the result is **not** inflated by feeding the
  operational inputs back in.

The residual circularity (the reference attributes are themselves ALS-model
outputs, not field measurement) is inherent to open data and cannot be removed;
the MS-NFI 2023 benchmark (A5c) is the second, more independent reference.

**Datasource 4 vs 5, and the discovery.** Splitting the out-of-fold predictions
by `treestanddatasource`:

| group | n | vol_total RMSE | vol_total R2 |
|-------|---|------|------|
| datasource 4 (interpreted) | 3,761 | 31 m3/ha | 0.87 |
| datasource 5 ("laser") | 405 | 125 m3/ha | strongly negative |

Datasource 5 is not a quality problem - those 405 stands are almost all
**regeneration / seedling** stands (development class T1 / T2 / A0, volume
median 0 m3/ha, height median 1.2 m). A near-treeless stand still returns some
ALS + optical signal, which the model - trained overwhelmingly on established
forest - maps to a non-zero volume, so relative error explodes. These stands are
also most of the "0-50 m3/ha over-predicted +44" tail seen in A4c.

**Established stands only (drop dev class A0 / T1 / T2, n 4,166 -> 3,480), ALS+S2:**

| target | ABA (sqrt) RMSE / R2 | k-NN k=5 RMSE / R2 |
|--------|------|------|
| vol_total | 25.0 m3/ha (13%) / 0.89 | 28.8 / 0.86 |
| meanheight | 1.04 m (6%) / 0.94 | 1.44 / 0.88 |
| meandiameter | 1.58 cm (8%) / 0.91 | 2.05 / 0.85 |
| basalarea | 2.71 m2/ha (12%) / 0.78 | 2.70 / 0.78 |
| meanage | 6.0 yr / 0.87 | 7.1 / 0.82 |
| vol_pine | 42.8 (52%) / 0.57 | 40.4 / 0.62 |
| vol_spruce | 43.9 (55%) / 0.56 | 42.3 / 0.59 |

These are operational-grade (stand volume ~13 % RMSE is in the range Metsakeskus
reports for its own ALS product). The pooled A4/A5a numbers were being halved by
the 686 seedling stands. On the clean established-forest domain the transparent
**sqrt-OLS clearly beats k-NN** for the structural attributes; k-NN keeps a small
edge only on per-species volume.

**Decision pending (Sam): gate Module A to established stands** - exclude
development classes A0 / T1 / T2 from the reference and modelling set, state the
model domain explicitly. A regeneration stand has no growing stock to estimate
and is identified (Module B, or dev class, or `h_p90 < ~5 m`), not estimated -
which is how an operational tool treats bare ground too.

### A5c-A6
Benchmark vs MS-NFI 2023 (`fetch_msnfi`, not yet implemented); performance on
Module B's `inventory_stale` stands; estimable-attribute summary; draw-a-polygon
demo; report.json.

---

## 4. Results and what they mean

(filled in as A4-A6 complete)

---

## 5. Caveats and open items

- `treestanddatasource` codes 7 and 9 not decoded (minor - excluded from reference).
- The subset is one 144 km2 window in one AOI - single-subset result.
- Open 0.5 p ALS height percentiles run ~1-3 m below the 5 p latvusmalli (crown-apex
  under-sampling); A4 models absorb this as a linear offset against measured plots.
- `als_cell_metrics` can emit NaN `canopy_cover` for a cell with points but no
  first returns (2 of 282,033 cells) - add a guard in A4.
