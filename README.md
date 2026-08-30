# Boreal Stand Intelligence

Reproducing three geospatial data products used in operational Finnish forestry
from **open data only**, as a validated batch pipeline: **growing-stock
estimation** (Module A), **harvest change detection** (Module B), and
**bark-beetle susceptibility and stress detection** (Module C). Every method is a
documented operational method, transparent statistics, or a deterministic rule —
no black boxes. Project 1 of two; companion repo `regenerative-harvest-planning`.

**Area of interest:** south-east Finland (Puumala–Ruokolahti–Savonlinna),
EPSG:3067 `[553000, 6780000, 610000, 6851000]`, 57 × 71 km, ~4,047 km², mixed
pine–spruce (spruce ~28 % by volume). All processing in EPSG:3067.

---

## Data and method at a glance

| Source | Product | Tier | Used for |
|---|---|---|---|
| Finnish Forest Centre (Metsäkeskus) | stands, grid cells, forest-use declarations | FETCH / BENCHMARK | reference attributes, harvest & damage records |
| NLS | 0.5 p airborne laser scanning, 2 m DEM | DERIVE input | ALS canopy metrics (Module A) |
| Metsäkeskus | latvusmalli canopy height model | BENCHMARK | "what does the paid 5 p ALS buy" |
| Luke | MS-NFI 2023 rasters (16 m) | BENCHMARK / predictors | second reference for volume, C1 landscape predictors |
| Copernicus | Sentinel-2 (C1 L2A for A/B, standard L2A for C2) | DERIVE ONLY | spectral features (A), change detection (B), stress (C2) |

**Three-tier rule.** *FETCH* — registers and legal records, no derivation
possible. *DERIVE AND BENCHMARK* — an official product exists; derive our own on a
validation subset and quantify agreement, then consume the official product at
AOI scale. **Module A stops at the "quantify agreement" step** — it is a subset
reproduction study, not an AOI-scale product. *DERIVE ONLY* — no official product;
this is where the analysis lives. The tier is stated in every module docstring.

Run: `pip install -r requirements.txt && pip install -e . --no-deps`, then
`python -m fi_forest_data.validate config/pipeline.yaml` and the per-module
drivers. `data/` and `outputs/` are gitignored and regenerated.

---

## Module A — Growing-stock estimation

**Question.** Draw a stand polygon, return the growing-stock attributes a
wood-trade offer needs. **Method.** A transparent implementation in the spirit of
the operational Finnish approach: area-based regression (OLS on `√volume`, five
ALS metrics) and k-NN imputation, plus a 2023 Sentinel-2 summer composite. It is
*not* the full operational method (which uses ~15–20 ALS metrics and a weighted
k-NN distance). **Validation.** Spatially blocked 5-fold CV on 3,480 established
stands in an 81 km² subset, epoch-matched (2023 stands + 2023 ALS + 2023
Sentinel-2). The reference is the Metsäkeskus interpreted stand attributes, which
are themselves ALS-model outputs — so this measures **how well open inputs
reproduce the operational estimate, not accuracy against field measurement**.

### What is estimable

![Estimable attributes by tier](docs/img/attribute_tiers.png)

| Attribute | Best RMSE | R² | Tier |
|---|---|---|---|
| mean height | 1.0 m (6 %) | 0.94 | reliable |
| mean diameter | 1.6 cm (8 %) | 0.91 | reliable |
| **total volume** | **25 m³/ha (13 %)** | **0.89** | reliable |
| mean age | 6 yr (13 %) | 0.87 | reliable |
| basal area | 2.7 m²/ha (12 %) | 0.78 | usable |
| pine / spruce volume | ~42 m³/ha (~50 %) | 0.6 / 0.6 | weak (target = total × stand species proportion, not independently measured) |

![Estimate vs register, total volume](docs/img/obs_pred_vol_total.png)

Total-volume RMSE varies with ALS coverage: **17 m³/ha (11 %)** for stands with
> 60 covered cells, **34 m³/ha** for stands with < 15. The 25 m³/ha headline is
the blend; typical-sized stands do better.

### Key analytical points

- **ALS carries structure, optical carries species.** Adding the Sentinel-2 bands
  barely moves height or diameter but roughly triples per-species volume R²
  (spruce 0.20 → 0.56).

  ![ALS vs ALS + Sentinel-2](docs/img/spectral_lift.png)

- **Not circular.** Our ALS metrics reproduce Metsäkeskus's own operational ones
  (`h_p90` vs their `LASERHEIGHT` r = 0.99); adding the official metrics changes
  R² by ≤ 0.03, so our independent features carry the signal.

- **Second reference.** Against MS-NFI 2023 our estimates sit as close as the
  operational register does (slightly closer on every attribute). MS-NFI shares
  inputs (Sentinel, NFI plots) so this is corroboration, not full independence; a
  consistent +35–37 m³/ha offset affects register and estimate equally.

  ![Agreement with MS-NFI 2023](docs/img/msnfi_agreement.png)

- **The blocked CV is sound.** The CV residuals lose spatial autocorrelation by
  ~250 m — well inside the 2 km CV block — so R² 0.89 is not inflated by
  train/test leakage.

- **Honest error structure.** Mild regression toward the mean: high-volume stands
  under-predicted, low over-predicted; unbiased through the 50–300 m³/ha range.

  ![Volume bias by stand size](docs/img/error_by_volclass.png)

- **The transparent model is enough** — `√`-OLS matches or beats k-NN on every
  structural attribute. The missing half is the closed harvester-outturn and
  sawmill-measurement calibration loop that operators run, which open data cannot
  reproduce.

---

## Module B — Harvest change detection

**Question.** Can harvests be detected from satellite, and at what size and
intensity does detection fail? **Method.** dNBR between 2021 and 2024
growing-season Sentinel-2 median composites (a two-date difference — not
time-series break detection), per-declaration zonal mean, per-type threshold
calibrated against ~172,000 forest-use declarations. A declaration is a permit,
not a record of execution, so results are given for **both** cohorts.

![Detected canopy loss 2021→2024; cyan = inventory-stale stands](docs/img/aoi_harvest_map.png)

| Felling type | Threshold (dNBR) | Precision | Recall — executed | Recall — full register | F1 |
|---|---|---|---|---|---|
| **Regeneration (clearcut)** | ≥ 0.06 | **0.90** | **0.83** | 0.52 | 0.86 |
| Thinning | ≥ 0.02 | 0.64 | 0.64 | 0.38 | 0.64 |
| Salvage (damage) | ≥ 0.12 | 0.39 | 0.33 | 0.29 | 0.36 |

Clearcut recall by stand area: **0.5–1 ha 0.80 · 1–2 ha 0.84 · 2–5 ha 0.88 ·
5–10 ha 0.89 · >10 ha 1.00.**

### Key analytical points

- **Clearcut detection is operational** (precision 0.90, recall 0.83 executed /
  0.52 full register — the gap is permits not yet cut, not misses).
- **Thinning is not separable by two-date optical differencing** — a method limit
  as much as a resolution limit. A time-series break detector or Sentinel-1
  coherence might recover some thinning; that is untested here.
- **Salvage is partial** — its signal spans clearcut-like to thinning-like and
  the damage moves the pre-image; this points straight to Module C.
- **`inventory_stale` flag:** 11,104 stands (~13,700 ha) show a detected clearcut
  postdating their last inventory — consumed by Module A as a data-currency
  caveat.

---

## Module C — Bark beetle

Two halves. Early detection of *Ips typographus* attack is a **known-unsolved
problem** (a 26-study critical review found timeliness and accuracy insufficient
for management); Module C reproduces that honestly, with significance tests, not
an inflated claim.

### C1 — Susceptibility: where is damage likely?

**Method.** Point-based presence/background logistic regression — 170
beetle/insect-damage salvage locations (2019–2024) vs 6,000 background points in
spruce forest; predictors are the mean MS-NFI 2023 value in a 500 m landscape
buffer, plus distance to the previous (2012–18) outbreak and nearby recent
clearcut area. Spatially blocked CV, precision-recall not accuracy.

| Driver | Odds ratio per 1 SD | p | direction |
|---|---|---|---|
| distance to previous outbreak | 0.32 | <0.001 | contagious spread — strongest |
| neighbourhood spruce share | 1.58 | <0.001 | host abundance |
| nearby recent clearcut | 1.30 | <0.001 | warm/dry forest edge |
| stand age | 0.89 | 0.27 | null at 500 m scale |
| site fertility | 0.96 | 0.74 | null |

![C1 drivers](docs/img/c1_coefficients.png) ![C1 precision-recall](docs/img/c1_pr_curve.png)

- **Damage location is driven by spread and host abundance** — both landscape
  properties, not stand structure.
- **The ranking is robust.** All predictor VIFs < 2.4 (spread and spruce share
  are not collinear), and the top-3 ranking is unchanged on the *Ips*-only
  (code 1602) subset (n = 120).
- Blocked-CV average precision **0.096 (model) ≈ 0.095 (naive additive index)**
  vs 0.028 random. The model has essentially no skill beyond weighting the
  obvious things equally, so the driver ranking is read as *consistent with the
  naive index and the Finnish literature*, not "the model proves". A useful
  ranking, not a predictive map.

### C2 — Stress detection: how early can it be seen?

**Method.** Monthly Sentinel-2 NDRE / NDMI per spruce stand, 2019–2024, over a
600 km² damage hotspot (44 damaged + 300 control). Per-stand seasonal baseline
from 2019–20; first sustained departure ≥ 2 SD below baseline within ±18/+6
months of the salvage date; controls get a matched pseudo-date (rates averaged
over 20 seeds; Fisher exact test that detection exceeds the false-alarm rate).

| Detector | Damaged detected | Control false alarm | Detection > false alarm? |
|---|---|---|---|
| **NDRE** | 0.11 | 0.07 ± 0.01 | **not significant** (Fisher p ≈ 0.25) |
| NDMI | 0.39 | 0.13 ± 0.01 | **significant** (p ≈ 0.0001) — but no lead time |
| NDRE ∧ NDMI | 0.02 | 0.02 | not significant |

![C2 sensitivity vs false alarms](docs/img/c2_rates.png) ![C2 NDRE lead-time sample](docs/img/c2_days_early.png)

- **NDRE gives no usable early signal here** — its detection rate is not
  statistically distinguishable from the rate at which the same departure appears
  in healthy control stands. The handful of NDRE detections that do precede the
  declaration (n ≈ 5) are too few to quantify a lead time.
- **NDMI detects damage** significantly more often than in controls, but fires
  *around or after* the salvage declaration — a "damage happened" signal, not an
  early-warning one.
- The declaration date already lags visible mortality, so even NDMI offers no
  operational lead. This matches the published critical review.

---

## Limitations

- **Module A** is a subset reproduction study (one 81 km² window, one epoch); the
  reference is itself an ALS model, so "R² 0.89" is agreement with the operational
  estimate, not field accuracy. Per-species volume is `total × stand proportion`,
  not independently measured.
- **Module B** uses a two-date dNBR; "thinning undetectable" is partly a method
  limit. The 0.83 clearcut recall is for an unvalidated executed-in-window
  heuristic — full-register recall is 0.52.
- **Module C1** has 170 events and no out-of-sample skill beyond a naive index;
  the coefficient table is a driver ranking, not a validated model. MS-NFI 2023
  predictors postdate part of the 2019–2024 target window.
- **Module C2** has 44 damaged stands and a thin 2019–20 baseline; the z-score
  threshold is indicative, not calibrated. A longer baseline + harmonic seasonal
  model is the standard alternative (deferred). Controls are drawn only from
  inside the damage hotspot.
- Operational products add closed feedback loops (harvester outturn, sawmill
  measurement, field survey) that open data cannot reproduce — this repo rebuilds
  the open skeleton and names the missing half.

## Repository layout

```
fi_forest_data/   data access: Metsäkeskus, NLS, Luke, FMI, Sentinel (fetch, cache, reproject)
src/              analysis modules, letter-prefixed (a_*, b_*, c1_*, c2_*), figures.py
config/           pipeline.yaml (all parameters), aoi_southeast.yaml
docs/             MODULE_*_NOTES.md — full rationale and results per module
outputs/          per-run report.json, tables, figures (gitignored)
```

## Attribution

Contains data from the Finnish Forest Centre, licensed CC BY 4.0. Contains
Natural Resources Institute Finland MS-NFI data, CC BY 4.0. Contains data from
the National Land Survey of Finland, CC BY 4.0. Contains modified Copernicus
Sentinel data. Contains Finnish Meteorological Institute open data, CC BY 4.0.
