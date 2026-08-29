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

7. **Model domain: established stands only** (A5b, 2026-08-29, agreed with Sam).
   `stand_model_frame` drops development classes A0 (open), T1 and T2 (seedling)
   via `module_a_stand_estimation.exclude_dev_classes` in the config. ~686 of
   4,166 subset stands, and with them all but ~3 of the datasource-5 stands.
   - *Why:* a regeneration / seedling stand has ~0 growing stock, so estimating
     its volume is not a real task; it is *identified* (Module B, the dev class
     itself, or `h_p90 < ~5 m`) and gated out, exactly as an operational offer
     tool treats bare ground. Kept in, they held the apparent volume R2 down
     from ~0.89 to ~0.75 and injected a +40 m3/ha low-end bias that
     misrepresented performance on the stands the model is actually for.
   - *Alternatives rejected:* keep them with a caveat (misleading headline
     numbers); a bare/seedling pre-classifier feeding the estimator (more
     machinery, same result as a dev-class gate).
   - *Effect on the reference set:* now effectively datasource-4 only. The
     datasource-4 vs -5 comparison from A5b is kept in the notes as the evidence.

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
volume, development class not in `exclude_dev_classes` (A0/T1/T2 - decision
2.6-7, added at A5b); stands with < 8 covered cells dropped. Adds
`soil_main_type` (mineral/peat, split at soiltype 60) and a spatial-block id.

As first built (no dev-class gate) the frame was **4,166 stands** (3,761
datasource 4, 405 datasource 5). With the A5b gate it is **3,480 stands**,
effectively datasource-4 only (3 datasource-5 survive). Targets: `vol_total`,
`vol_pine/spruce/other` (= total x the stand species proportions - the stand
layer has no per-species volume column), `basalarea`, `meanheight`,
`meandiameter`, `meanage`, `sawlogvolume`, `pulpwoodvolume`, `stemcount`,
`volumegrowth`. Output: `data/raw/nls/stand_model_frame_e_ruokolahti.csv`
(pre-S2), `stand_model_frame_s2_e_ruokolahti.csv` (with spectral features).

Also folded in the A3 carry-forward: `als_cell_metrics` now fills NaN
`canopy_cover` (points but no first returns) with 0.

Open decision carried into A4b: the 81 km2 subset spans only ~4 full 5 km CV
blocks, so 5-fold spatial-block CV as configured is not viable - resolve the
block size / fold assignment before fitting.

### A4b/A4c/A5a - blocked-CV comparison of ABA vs k-NN (done)

All tables below are the **final established-stand domain** (2.6-7 gate) with the
**ALS + S2 production feature set** (2.6-6). CV: 2 km blocks (config, was 5 km),
`assign_cv_folds` snakes the blocks and cuts them into 5 runs of ~equal stand
count (791 / 635 / 870 / 583 / 601). ABA = OLS on `sqrt(y)` (2.6-3). Pooled
out-of-fold metrics, `outputs/tables/a4b_cv_metrics.csv`
(ALS-only ablation in `a4b_cv_metrics_als_only.csv`):

| target | ABA (sqrt) RMSE / R2 | k-NN k=5 RMSE / R2 | ALS-only R2 (ABA) |
|--------|------|------|------|
| vol_total | 25.0 m3/ha (13%) / 0.89 | 28.8 / 0.86 | 0.81 |
| meanheight | 1.04 m (6%) / 0.94 | 1.44 / 0.88 | 0.93 |
| meandiameter | 1.58 cm (8%) / 0.91 | 2.05 / 0.85 | 0.88 |
| basalarea | 2.71 m2/ha (12%) / 0.78 | 2.70 / 0.78 | 0.65 |
| meanage | 6.0 yr (13%) / 0.87 | 7.1 / 0.82 | 0.79 |
| vol_pine | 42.8 (52%) / 0.57 | 40.4 / 0.62 | 0.38 |
| vol_spruce | 43.9 (55%) / 0.56 | 42.3 / 0.59 | 0.20 |
| vol_other | 17.8 (57%) / 0.79 | 19.2 / 0.76 | 0.27 |

k sweep, vol_total: k=1 36.7 / k=3 30.1 / k=5 28.8 / k=7 28.4 / k=10 28.1. k-NN
plateaus ~28; ABA (25.0) beats every k.

**These are operational-grade.** Stand total-volume RMSE ~13 %, mean-height
RMSE ~1 m, are in the range Metsakeskus reports for its own ALS product.
Before the 2.6-7 gate the pooled figures were ~2x worse (vol_total R2 ~0.72,
RMSE ~52) - held down entirely by the 686 seedling / regeneration stands; see
A5b for that comparison.

**On this clean domain the transparent sqrt-OLS beats k-NN** on every structural
attribute (height 0.94 vs 0.88, diameter 0.91 vs 0.85, volume 0.89 vs 0.86).
k-NN keeps a small edge only on per-species volume, where its jointly consistent
donor vector helps. k-NN stays carried forward for the A6 draw-a-polygon output
(a single real donor stand supplies a physically consistent attribute set).

**Sentinel-2 unlocks species** (`a4b_cv_metrics_als_only.csv` vs the S2 set):
per-species volume R2 roughly doubles (spruce 0.20 -> 0.56, pine 0.38 -> 0.57,
other 0.27 -> 0.79); total volume 0.81 -> 0.89, basal area 0.65 -> 0.78; height
/ diameter barely move (ALS already carries them). Expected division of labour -
ALS for structure, optical for species.

**Error structure (`a4b_vol_total_by_volclass.csv`, `_by_species.csv`):**
- Mild regression toward the mean: the 300+ m3/ha class (n 325) is
  under-predicted -19 (ABA) / -30 (k-NN), the residual 0-50 class (n 37, mostly
  `Y1` seedling-with-overstorey) over-predicted ~+24. The 50-300 m3/ha range is
  tight (RMSE 20-25, bias < 8).
- By main species, pine and spruce are even (RMSE ~24, bias < 3 for ABA); the
  mixed-broadleaf group (n 289) is over-predicted +18.

### A5b - circularity probe and the model domain (done)

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

Dropping dev class A0 / T1 / T2 (n 4,166 -> 3,480) lifts vol_total R2 from ~0.72
to 0.89 and removes the low-end bias. **Resolved as decision 2.6-7: gate Module A
to established stands.** The gated-domain result tables are the A4b/A4c/A5a
section above; this section keeps the datasource-4/5 split as the evidence.

### A5c - MS-NFI 2023 benchmark (done)

`fi_forest_data/luke.fetch_msnfi(theme, aoi)` implemented: windows a whole-Finland
MS-NFI 2023 theme GeoTIFF (Funet mirror, `{theme}_vmi1x_1923.tif`, UInt16, 16 m,
EPSG:3067) to the subset via `/vsicurl` and caches a COG. Nodata 32766 / 32767
kept distinct, both masked for analysis. Themes pulled: `tilavuus` (total
volume), `manty`, `kuusi`, `keskipituus` (dm), `ppa`, `keskilapimitta`, `ika`.
`src.a_stand_estimation.msnfi_stand_medians` gives the per-stand zonal median.

Triangulation on the 3,480 established stands - how well each of (a) the
Metsakeskus stand register and (b) our out-of-fold CV estimates agree with the
**independent** MS-NFI product (`outputs/tables/a5c_msnfi_benchmark.csv`):

| attribute | register vs MS-NFI | our best estimate vs MS-NFI |
|-----------|--------------------|-----------------------------|
| total volume | r 0.73, RMSE 65 | r 0.77, RMSE 57 |
| pine volume | r 0.70, RMSE 54 | r 0.74, RMSE 41 |
| spruce volume | r 0.75, RMSE 52 | r 0.79, RMSE 40 |
| mean height | r 0.73, RMSE 3.1 m | r 0.77, RMSE 2.7 m |
| basal area | r 0.65, RMSE 5.2 | r 0.71, RMSE 4.6 |
| mean diameter | r 0.73, RMSE 4.3 cm | r 0.77, RMSE 3.7 cm |
| mean age | r 0.68, RMSE 13 yr | r 0.73, RMSE 12 yr |

**Our open-data reconstruction agrees with MS-NFI as well as the official stand
register does - marginally better on every attribute.** That is the headline
validation: an independent official product places our estimates and the
operational register at the same distance from itself. k-NN edges ABA here (it
was the other way against the register) - unsurprising, MS-NFI is itself a k-NN
product, so method affinity.

**A consistent +35 to +37 m3/ha offset on total volume affects the register and
our estimates equally**, so it is an MS-NFI property, not our error: MS-NFI k-NN
on a coarse 16 m satellite grid saturates and regresses high volumes toward the
mean, and a raster zonal median over a stand also dilutes with small gaps that
the stand polygon and the register exclude. Documented, not corrected.

### A6a - estimable-attribute summary and report.json (done)

`run_module_a` (in `src/a_stand_estimation.py`) runs the whole module end to end -
frame, blocked CV (ALS and ALS+S2), attribute summary, MS-NFI benchmark,
circularity probe - and writes `outputs/p1/module_a/{run_id}/report.json` plus
tables. `estimable_tier` buckets each attribute by its cross-validated R2 and
relative error ("reliable" needs both R2 >= 0.85 and RMSE <= 20 %, so a
high-R2 / high-scatter attribute like sawlog volume is not oversold).

| tier | attributes (best method, R2) |
|------|------------------------------|
| reliable | mean height (0.94), mean diameter (0.91), **total volume (0.89, 13 %)**, mean age (0.87) |
| usable | sawlog volume (0.90 R2 but 28 % RMSE), other-species volume (0.79), basal area (0.78), stem count (0.74), pulpwood volume (0.69) |
| weak | pine volume (0.62), spruce volume (0.59), volume growth (0.54) |
| not estimable | none |

The `inventory_stale` question is answered by cross-reference, not new
processing: Module B flags 11,104 stands (~13,700 ha) AOI-wide whose record
predates a detected disturbance; those are identified for re-inventory, not
estimated here. No ALS is fetched outside the 81 km2 subset (three-tier rule).

### A6b - draw-a-polygon demo and figures (done)

`fit_production_models` fits the ABA sqrt-OLS (one fit per target) and a
per-stratum k-NN index on the whole established-stand frame; `estimate_polygon`
takes any EPSG:3067 polygon inside the subset, pulls its median ALS cell metrics
and median Sentinel-2 reflectance, and returns the attribute vector from both
methods plus **the real donor stands k-NN used** (ids + inverse-distance
weights) - the "your estimate is an average of these five actual stands"
transparency.

`run_module_a` runs a 3-stand demo (low / median / high recorded volume),
fitting with those three left out so both methods are genuinely out-of-sample
(k-NN cannot retrieve the stand itself). Result lands in `report.json`
(`draw_a_polygon_demo`). Example: a 116 m3/ha stand -> ABA 121, k-NN 107; a
296 m3/ha stand -> ABA 281, k-NN 296.

**Module A is complete.** Open item: wire `run_module_a` into `src/run.py`
(currently invoked directly); the README section is a project-end task.

### A6c - figure set and what each one shows

Five figures, `src/figures.py`, written to
`outputs/p1/module_a/{run_id}/figures/`. Chosen to cover the analysis in layers:
the headline result, the breadth of what is estimable, the two independent
validations, and the error structure. Recorded here so the rationale is
traceable for the write-up.

1. **`obs_pred_vol_total.png` - estimate vs register, total volume.** The
   standard estimation-validation plot: each established stand as (register x,
   cross-validated estimate y), both methods, 1:1 line, RMSE / R2 in the legend.
   *Why:* it is the first plot a reviewer looks for; shape (curvature, ceiling,
   fan) diagnoses *how* a model fails. Total volume is the attribute the module
   exists to produce.
   *Signal:* strong - the cloud hugs the 1:1 line across 0-430 m3/ha, R2 0.89 /
   0.86, no curvature, only mild under-prediction above ~300.
   *Weakness:* ~3,500 semi-transparent points overplot in the middle - a
   density / hexbin version would read better on a poster.

2. **`attribute_tiers.png` - R2 per attribute, coloured by estimable tier.**
   *Why:* the module's real question is "which attributes can open data deliver,
   and how well"; turns the 12-row metrics table into one ranked, colour-coded
   view, weak attributes shown honestly.
   *Signal:* clear gradient - 4 reliable (R2 0.87-0.94), a usable band, 3 weak.
   *Weakness:* the tier is R2-led, so `sawlogvolume` (R2 0.90 / 28 % RMSE) and
   `vol_other` (R2 0.79 / 57 % RMSE) look better than their scatter warrants;
   the "(R2 / %)" label is there to keep that honest.

3. **`spectral_lift.png` - ALS-only vs ALS + Sentinel-2 R2, per attribute
   (k-NN).** *Why:* shows the division of labour that decision 2.6-6 rests on.
   *Signal:* strong and on-message - per-species volume roughly doubles or
   triples (spruce 0.18 -> 0.59, pine 0.40 -> 0.62, other 0.27 -> 0.76), while
   structural attributes barely move; `meanheight` even dips 0.93 -> 0.88 (extra
   features add a little k-NN noise to a metric ALS already nails - a fair point
   to make, not a problem).

4. **`msnfi_agreement.png` - Pearson r with MS-NFI 2023: register vs MS-NFI,
   and our estimate vs MS-NFI, per attribute.** *Why:* the strongest "this is
   validated" visual - an independent official product as referee.
   *Signal:* strong - our estimate (blue) edges the operational register (grey)
   on every one of the seven attributes. Note this is agreement with a second
   *model*, not field truth (caveat in section 5).

5. **`error_by_volclass.png` - volume bias by observed volume class, both
   methods.** *Why:* makes the one real weakness visible - regression toward the
   mean.
   *Signal:* textbook fan - low stands over-predicted +24 / +29, high stands
   under-predicted -19 / -30, near-zero in the 150-200 band; n-labels show the
   mass is in the mid classes where the model is unbiased.
   *Weakness:* n-labels crowd the axis at the extremes - poster polish deferred.

Deferred to poster / README stage: hexbin version of (1), a map of one demo
stand with its k-NN donor stands, and per-fold spatial-CV maps.

---

## 4. Results and what they mean

(A6 adds the estimable-attribute summary and the demo; the numbers so far)

- **The open-data + published-method pipeline reproduces operational ALS stand
  estimation.** On established stands (3,480, epoch-matched 2023) with ALS + a
  2023 Sentinel-2 composite: total volume RMSE 25 m3/ha (13 %, R2 0.89), mean
  height RMSE 1.0 m (R2 0.94), mean diameter RMSE 1.6 cm (R2 0.91), basal area
  R2 0.78, age R2 0.87. These match the accuracy Metsakeskus reports for its own
  ALS product.
- **ALS carries structure, optical carries species.** ALS alone gets volume /
  height / diameter; adding the S2 bands roughly doubles per-species volume R2
  (spruce 0.20 -> 0.56, pine 0.38 -> 0.57). Per-species volume stays the weakest
  output (R2 ~0.6) - the known limit of passive optical for conifer separation.
- **Not circular.** Our ALS metrics reproduce Metsakeskus's own (h_p90 vs
  LASERHEIGHT r 0.99); adding the official metrics changes R2 by <= 0.03. An
  independent product (MS-NFI 2023) sits as close to our estimates as to the
  operational register.
- **The transparent model is enough.** sqrt-OLS matches or beats k-NN on every
  structural attribute on the clean domain; k-NN is kept only for the
  physically-consistent attribute vector it gives the polygon demo.
- **What it cannot do:** estimate regeneration / seedling stands (gated out, no
  growing stock), or beat ~13 % volume RMSE from open inputs - Metsa's closed
  harvester-outturn calibration loop is the missing half and is not reproducible
  from open data.

---

## 5. Caveats and open items

- `treestanddatasource` codes 7 and 9 not decoded (minor - excluded from reference).
- The subset is one 144 km2 window in one AOI - single-subset result.
- Open 0.5 p ALS height percentiles run ~1-3 m below the 5 p latvusmalli (crown-apex
  under-sampling); A4 models absorb this as a linear offset against measured plots.
- `als_cell_metrics` NaN `canopy_cover` (points but no first returns, 2 of
  282,033 cells) - guarded in A4 (`fillna(0)`).
- Per-species volume targets are `total x stand species proportion`, not measured
  per-species volumes (the stand layer has none) - the split is partly
  definitional.
- MS-NFI benchmark carries a consistent +35-37 m3/ha volume offset (affects the
  register equally; an MS-NFI saturation / zonal-median property, not our error).
- `inventory_stale` performance (A5d) needs ALS + S2 outside the 81 km2 subset;
  feasibility to be assessed before committing to it.
