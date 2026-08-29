# Project 1 — Boreal Stand Intelligence
Modules A + B + C. Created 2026-08-26, revised same day.
Depends on: METSA_GIS_RESEARCH_FINDINGS.md
Working repo name: `/BorealStandIntelligence`

---

## One-line framing

Rebuilds Metsä Forest's three published geospatial data products — growing stock
estimation, harvest change detection, and insect damage mapping — from Finnish
open data, using the estimation methods the Finnish forest sector actually runs,
and quantifies where open data falls short of their harvester-calibrated system.

## Design principle: follow the analyst's workflow

The goal is to work the way a Metsä GIS analyst works, not to reprocess Finland
from scratch. An analyst pulls authoritative products where they exist and
computes what genuinely needs computing. So every input falls into one of three
tiers, and the tier is stated explicitly in the README:

- **FETCH** — registers and legal records. No sensible derivation exists.
  Forest use declarations, Forest Act §10 habitat polygons, stand boundaries,
  property boundaries. Used as reference and ground truth.
- **DERIVE AND BENCHMARK** — an official product exists, the method is published,
  and computing our own version gives us a validation figure plus a real
  understanding of what the product contains and where it fails.
- **DERIVE ONLY** — no official product exists. This is where the analysis lives.

Where we derive-and-benchmark, the honest pattern is: **derive on a validation
subset, quantify agreement against the official product, then consume the official
product at full AOI scale.** A 5,000 km² AOI is ~1.25 billion cells at 2 m and
~2.5 billion ALS points at 0.5 p/m². Reprocessing all of it would prove nothing
extra and is the wrong engineering call. Say so in the documentation.

## On machine learning — not the default approach

The Finnish operational methods are non-parametric **k-nearest neighbour
imputation** and **area-based regression**, not ML. MS-NFI uses k-NN (Tomppo), an
improved k-NN since MS-NFI-9, with k = 5 most frequently. Metsäkeskus grid-cell
inventory finds the best-matching field plots per 16 m cell and estimates from
them — the same idea. Using gradient boosting here would be less faithful to the
domain, not more sophisticated, and would be harder to defend in conversation.
So the default throughout is the operational non-ML method.

This is a default, not a prohibition. If a module turns out to clearly benefit
from or genuinely need ML, that is open for discussion — raised as a design
decision with options and trade-offs, agreed before implementing, and never
substituted silently. A gradient-boosted comparison is noted in the README as a
natural extension, not implemented, and sequenced after the ML certification in
Track 6 of the backlog. That is the honest position and it reads better than a
half-understood model.

## Why these three modules belong together

One data backbone, and they are causally chained:

- **B feeds A.** Metsäkeskus stand attributes are updated with growth models
  between six-year laser scanning rounds, and harvests are back-filled with
  standard thinning models. For any stand harvested since its last scan the
  reference value is modelled, not measured. Detecting those stands is a
  prerequisite for using the rest honestly.
- **B feeds C.** Salvage felling is recorded in the declaration system — the same
  response variable used in published Finnish bark beetle work.
- **A feeds C.** Spruce share, maturity and height are exactly the
  susceptibility covariates the literature uses.

Build order: **B → A → C.**

---

## Area of interest

**Southeastern Finland — Etelä-Savo / South Karelia.**
Puumala – Ruokolahti – southern Savonlinna. FIXED EXTENT:
- EPSG:3067 bbox: `[553000, 6780000, 610000, 6851000]`
- WGS84 bbox: `[28.00, 61.15, 29.05, 61.78]`
- 57 x 71 km, ~4,047 km² (similar scale to Prey Lang)

Rationale: mixed pine–spruce private forest of exactly the type Metsä buys from
members (TASK 00: pine 49% / spruce 28% / deciduous 23% by volume — the original
"spruce-dominant" framing was wrong, but the ~28% spruce component is ample for
Module C); the documented Finnish Ips typographus concentration, with Ruokolahti a
long-term monitoring site (2010 storm, outbreak from ~2014); dense harvesting so
the declaration layer is well populated (~176k declarations in the AOI, current to
the day); best Sentinel-2 cloud statistics in Finland.

**ALS source (TASK 00, Decision D1 — resolved).** The AOI is fully covered by
recent open 0.5 p ALS from the national programme: Puumala 2019, Lappeenranta
2020, Savonlinna 2021, Juva 2022, Parikkala 2023, all "products available". Module
A uses this (via the NLS OGC API, free key registered at Module A start), so it is
a clean, current methodology reproduction — no temporal-drift dimension. The
per-stand "harvested since last scan" question is a Module B output
(`inventory_stale`), which Module A honours via `exclude_stale_stands`. The 2020+
product is ~0.5 p/m² (the 2008–2019 legacy round, kept as fallback, measured
~1.6). Exact epoch/clip decided at Module A start.

FIRST TASK, before any bulk download: verify at feature/pixel level that the AOI
has current stand data with usable scan dates, sufficient declaration density, and
MS-NFI 2023 coverage. This follows the standing rule from the infrastructure notes.

---

## Module B — Harvest detection validated against forest use declarations

### Data

| Tier | Item | Source |
|---|---|---|
| FETCH | Forest use declarations (metsänkäyttöilmoitus) — geometry, felling type, dates | Metsäkeskus WFS `v1/forestusedeclaration/ows` |
| FETCH | Stand polygons, forest mask | Metsäkeskus WFS `v2/stand`, `v2/forestmask` |
| DERIVE ONLY | Sentinel-2 L2A composites and change surfaces | AWS Earth Search (Collection 1) |

**Sentinel-1 dropped (2026-08-29).** SAR is not a core Finnish operational
forestry method — the operational products this project rebuilds are optical +
ALS. Its only strong justification here (cloud gaps) does not apply: the SE
Finland summer S2 composites are 99.8% complete with ~11 clear looks per pixel.
Adding a SAR log-ratio would make the project less faithful to "what Metsa does"
and add domain surface area with marginal gain. `sentinel1.enabled: false`.

### Calculations
- Seasonal median composites, SCL cloud masking (Baltic/Prey Lang pattern)
- dNBR and ΔNDMI differencing between pre and post windows
- Zonal statistics per declaration polygon (GeoPandas + rasterstats),
  pixel-centroid mode, no_data excluded from the validation denominator
- Threshold calibrated by **F1 sweep against declarations**, not assumed —
  same procedure as the LA wildfire project
- Separate calibration and scoring for regeneration felling vs thinning

### Analytical outputs
- F1, precision and recall by felling type and by stand area class
- Threshold sweep curves showing where optimal thresholds diverge between
  clearcut and thinning
- Declared-but-not-executed and executed-outside-window handled as their own
  category rather than counted as false positives
- Minimum reliably detectable stand size, and minimum detectable thinning intensity
- AOI harvest map, and a per-stand "inventory currency" flag feeding module A

### Expected honest result
Clearcut detection strong, thinning detection weak, small stands underperforming
at 10–20 m pixel spacing for the same reason small buildings did in the LA project.
The contrast is the finding.

---

## Module A — Stand attribute estimation from open data

Direct rebuild of the open-data half of Metsä's wood trade offer tool: draw a
polygon, return the attributes an offer needs.

### Data

| Tier | Item | Source |
|---|---|---|
| FETCH | Stand attributes used as reference values | Metsäkeskus WFS `v2/stand` |
| FETCH | 16 m grid cell attributes | Metsäkeskus WFS `v2/gridcell` |
| DERIVE AND BENCHMARK | ALS height metrics per 16 m cell | NLS ALS 0.5 p + NLS 2 m DTM; benchmark vs Metsäkeskus latvusmalli (from paid 5 p) |
| DERIVE AND BENCHMARK | Volume and species estimates | Our k-NN/ABA; benchmark vs Luke MS-NFI 2023 |
| DERIVE ONLY | Sentinel-2 spectral features | CDSE / GEE |
| FETCH | Topographic derivatives, site and soil stratum | NLS 2 m DEM; MS-NFI mineral/peat main type |

### Calculations

**ALS metrics (area-based approach).** Height-normalise the 0.5 p point cloud
against the NLS 2 m DTM, then per 16 m cell compute height percentiles
(P25/P50/P75/P90/P95), mean and max height, canopy cover as the proportion of
returns above 2 m, and return density. The 2020+ open product is ~0.5 p/m² (thinned
from the 5 p programme); a 16 m cell then holds ~130 points — enough for percentile
metrics, not for crown delineation, and the documentation should say exactly that.
Tuominen et al. 2014 estimated volume, species-specific volumes, mean diameter and
mean height from ALS at 0.54 p/m², so this density is a published working point
rather than a gamble. (The 2008–2019 legacy round measured ~1.6 p/m² in this area
— denser, but older; it is the fallback only.) Verify the actual density on a
delivered tile at Module A start.

**Estimation.** Two approaches, reported side by side:
1. **Area-based regression** — volume as a function of height percentiles and
   canopy density. The classic Nordic ABA baseline, transparent and easy to defend.
2. **k-nearest neighbour imputation** — mirroring MS-NFI. Euclidean distance in
   feature space, distance-weighted average of the k nearest reference stands,
   **stratified by mineral soil vs peatland** and restricted by geographic
   distance, exactly as the operational method does. Test k, weighting power, and
   feature set. Start at k = 5 since that is MS-NFI's most frequent choice.

**Validation.** Spatially blocked cross-validation, not random splits — adjacent
stands are correlated and random splits inflate scores. RMSE and bias reported both
absolute and relative, matching how the Finnish literature reports.

### Analytical outputs
- RMSE, bias and relative RMSE by species and by volume class, ABA vs k-NN
- Our ALS metrics vs Metsäkeskus latvusmalli: agreement statistics that
  **quantify what the paid 5 p data buys over the open 0.5 p data**
- Our volume estimates vs MS-NFI 2023: agreement, and where they diverge
- Performance with and without MS-NFI features, as a circularity check
- **Performance on stale-label stands flagged by module B** — the cost of
  inventory staleness, expressed in m³/ha
- Which attributes are estimable and which are not: expect volume and height to
  work, and log-wood proportion and quality to fail, because stem form and defect
  are not observable from any open remote sensing product
- A demonstration that takes an arbitrary drawn polygon and returns estimates

### Honest limitations
No harvester outturn or sawmill log measurement. Metsä calibrate against measured
reality; this calibrates against a partly modelled inventory. That single
difference is the whole story and should be stated as a compliment to their system.

---

## Module C — Bark beetle susceptibility and stress detection

Deliberately two halves answering different questions.

### C1 — Susceptibility: where is damage likely

| Tier | Item | Source |
|---|---|---|
| FETCH | Salvage fellings (response variable) | Metsäkeskus declarations |
| FETCH / DERIVE | Spruce share, maturity, site fertility | Metsäkeskus stands, MS-NFI, module A |
| DERIVE ONLY | Forest edge exposure (the "sun effect") | Clearcut edges from module B |
| FETCH | Temperature and precipitation | FMI open data |

Calculations: transparent **logistic regression** on the published Finnish
drivers — spruce share and volume, stand maturity and height, site dryness, edge
exposure, proximity to prior damage, climatic water balance. Compared against a
simple weighted risk index for interpretability. No black box: the coefficients
are the result, because the audience will ask which factors matter.

Outputs: susceptibility map; **precision-recall curves, not accuracy** — damage is
rare and accuracy would be meaningless; coefficient table with confidence
intervals; comparison of driver ranking against the published Finnish findings.

### C2 — Stress detection: where is damage happening

Calculations: per-stand Sentinel-2 index trajectories over spruce stands, focusing
on **NDRE and NDMI**. NDRE is the point — Prey Lang already established that NDRE
tracks canopy biochemical state rather than structure, and that is the signal that
should move before visible mortality. Departure-from-baseline test against each
stand's own history rather than a single-date threshold.

Outputs: detection date per stand versus the declared salvage date, reported as a
**days-early distribution**, not a single accuracy figure.

### Non-negotiable honesty requirement
A critical review of 26 early-detection studies found timeliness and accuracy
insufficient for management regardless of platform, sensor type or resolution.
This goes at the top of the README. C2 is a reproduction of a known-hard problem
with an explicit measurement of how early detection actually is. If the answer is
"about the same time as visible mortality", that is the honest result and it will
land better with people who run this in production than an inflated claim.

---

## Shared infrastructure

```
fi_forest_data/          # shared with Project 2
  metsakeskus.py         # WFS/WCS/REST clients, version-pinned endpoints
  luke_msnfi.py          # MS-NFI sheet discovery, mosaic, nodata handling
  nls.py                 # DEM, ALS, topographic database, property register
  fmi.py                 # weather observations and climate
  aoi.py                 # AOI definition, EPSG:3067, coverage verification
```

- Everything in EPSG:3067. Reproject once at ingest, never mid-pipeline.
- MS-NFI nodata: 32766 = forestry land without satellite cover, 32767 = not
  forestry land or outside country. Different meanings, must not be collapsed.
- Metsäkeskus endpoints are versioned in the URL path and a data model reform is
  under way. Pin versions in config, record fetch date in run metadata.

Standard conventions: all parameters in `pipeline_config.yaml`, versioned S3
outputs per run, COG GeoTIFF DEFLATE, Docker, GitHub Actions with flake8, config
validation and unit tests, `data/` gitignored before any output is written.

---

## Deliverables
- Config-driven pipeline, three modules, AOI-generalisable
- Validation tables and figures per module
- One poster in the Prey Lang / Baltic layout. Best subject is module B: harvest
  detection against declaration polygons is visually immediate.
- README leading with the fetch/derive tiering and the limitations

## Talking points generated
- Inventory staleness bounds what any open-data model can achieve — the
  Track-64-equivalent insight for this project
- What 10× ALS point density actually buys, measured rather than asserted
- Thinning vs clearcut detectability as a resolution-limited problem
- Why harvester and sawmill feedback is the real moat
- Bark beetle early detection as an honestly unsolved problem
