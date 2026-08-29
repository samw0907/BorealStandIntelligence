# Module C - notes, decisions and rationale

Running record of *why* Module C is built the way it is and *what the results
mean*. Source material for the final README. Companion plan:
`PROJECT_1_BOREAL_STAND_INTELLIGENCE.md`, Module C section.

---

## 1. What Module C is

Bark beetle (*Ips typographus*, the European spruce bark beetle) work, in two
halves that answer different questions:

- **C1 - susceptibility:** where is damage likely? Transparent logistic
  regression on the published Finnish risk drivers, validated against salvage
  declarations. Deliverables: coefficient table with confidence intervals and
  odds ratios; a precision-recall curve (not accuracy - damage is rare); a
  driver ranking compared with published Finnish findings.
- **C2 - stress detection:** where is damage happening now? Per-stand Sentinel-2
  NDRE / NDMI trajectories against each stand's own baseline; output is a
  days-early distribution versus the declared salvage date. The README leads
  with the honesty caveat that early detection is a known-unsolved problem.

The pest matters here because the Project 1 AOI is only ~28 % spruce by volume,
but that is still hundreds of km2, and SE Finland had a real *Ips typographus*
build-up over 2019-2023.

---

## 2. Design decisions

### 2.1 Damage label (C1a, 2026-08-29)

Positive = a forest-use declaration that is beetle / insect-damage salvage:
`FORESTDAMAGEQUALIFIER` 1602 (*Ips typographus*) **or**
`CUTTINGREALIZATIONPRACTICE` 22 / 23 (insect damage). In the SE AOI: **672 such
declarations, 585 fall inside some stand polygon.** A sensitivity check against
1602-only is planned. Storm salvage (1504, practice 20/21; 3,206 declarations) is
*not* included - windthrow and beetle are linked but "disturbance salvage" is a
different, broader target.

### 2.2 Why not the planned stand-level predictive model (C1a finding)

The plan was a logistic regression over spruce stands, damage vs no damage, with
an AOI susceptibility map. Two data facts defeat that:

1. **Leakage.** A stand's inventory attributes are re-measured *after* a salvage,
   so a damaged stand's recorded volume, basal area and height reflect the
   post-cut state. Restricting to stands whose inventory predates their damage
   leaves only ~20 clean positives in the whole AOI - too few to fit.
2. **Post-salvage reclassification.** A beetle clearcut salvage turns the stand
   into an opening or a seedling stand (dev class A0 / T1 / T2) with spruce
   share near zero in the next inventory. The eligibility filter
   ("spruce >= 20 %, past seedling stage") therefore *removes* most damaged
   stands: of 585 declaration-hit stands, only **33** survive as eligible spruce
   stands. The pre-damage stand is not recoverable from the current register.

So a well-powered, leakage-free *stand-level* model is not supported by this open
data. This is itself a documented finding (an inventory-currency limit, the same
theme as Module B's `inventory_stale`).

### 2.3 Chosen design: point-based presence / background logistic regression

- **Cases:** the 585 beetle / insect-damage salvage declaration locations
  (2019-2024).
- **Background:** a large random sample of points in spruce-bearing forest
  (MS-NFI 2023 spruce volume above a threshold), representing the available
  spruce landscape.
- **Predictors, sampled in a ~500 m neighbourhood of each point** (a landscape
  buffer, so the value is dominated by surrounding un-salvaged forest and is not
  corrupted by the salvage pixel itself): MS-NFI spruce volume and share, mean
  age, total volume, site fertility class; distance to nearest pre-2019 beetle
  declaration; plus, in C1b, forest-edge density (from Module B clearcuts) and a
  climatic water-balance term (FMI 2018-2019).
- **Model:** logistic regression (presence vs background), transparent
  coefficients and odds ratios, with an additive risk-index baseline for
  comparison. Spatially-blocked evaluation, precision-recall not accuracy.
- This is a standard species-distribution-model design; the "background is not
  confirmed absence" assumption is acknowledged, as in that literature.

---

## 3. Method and results

### C1a - label and eligibility exploration (done)

`src/c1_beetle_susceptibility.py`: `beetle_declarations` filters the salvage
label; `c1_model_frame` assembled the stand-level table and surfaced the two
problems in 2.2. Even so, the raw contrast between the 33 recoverable damaged
spruce stands and the rest points the expected way - damaged stands are older
(65 vs 50 yr), taller (21 vs 18 m), larger-diameter (26 vs 22 cm), higher spruce
share, on richer mineral sites, and closer to earlier damage (1.2 vs 2.5 km).
The signal is real; the design in 2.3 is what lets us measure it cleanly.

### C1b - point sample and logistic regression (done)

`build_point_sample`: 170 beetle / insect-damage salvage locations arriving
2019-2024 that fall in the AOI (the response), plus 6,000 background points
drawn at random in spruce-bearing forest (MS-NFI `volume_spruce` >= 20 m3/ha on
forest land), each >= 300 m from a case. Predictors are the **mean MS-NFI value
in a 500 m buffer** of each point - a landscape measure, dominated by the
surrounding un-salvaged forest: spruce share (`volume_spruce / volume`), stand
age, site fertility class; plus straight-line distance to the nearest 2012-2018
beetle declaration (`prior_damage_dist_km`). MS-NFI 2023 rasters fetched for the
full AOI via `fetch_msnfi` (COG-tiled, ~5 s each).

`fit_c1_logit` - logistic regression on the standardised predictors,
`c1_spatial_cv` - out-of-fold probabilities under 10 km blocked CV (train and
test never share a block), `c1_pr_metrics` - average precision vs an
equal-weight additive-index baseline.

### C1c - edge exposure added; climate term dropped (done)

- **Recent-clearcut exposure** (`recent_clearcut_ha`): area of regeneration-fell
  declarations arriving 2013-2018 whose polygon intersects the 500 m buffer -
  fresh warm, dry forest edge, the "sun effect" of the beetle literature. Added
  as a fifth predictor.
- **Climatic water balance: not used in C1.** `fmi.py` `fetch_daily` is
  functional, but the SE AOI is only 57 x 71 km and summer weather barely varies
  across it, so a station-interpolated water-balance term would be near-constant
  and cannot explain the *within-AOI* pattern of damage. The 2018 drought is a
  *temporal trigger* for the outbreak, handled in the README narrative, not a
  spatial C1 predictor. FMI is finished and validated in Project 2, where it is
  load-bearing (root-rot temperature rules, frozen-season length).

**Final C1 coefficient table (odds ratio per 1 SD, 170 cases / 6,170 points):**

| predictor | OR per SD | 95 % CI | p | direction |
|-----------|-----------|---------|---|-----------|
| prior_damage_dist_km | 0.32 | 0.22-0.46 | <0.001 | as expected - closer to the 2012-2018 wave, much higher risk |
| spruce_share | 1.58 | 1.30-1.92 | <0.001 | as expected - more spruce, more risk |
| recent_clearcut_ha | 1.30 | 1.13-1.50 | <0.001 | as expected - more fresh edge nearby, more risk |
| age | 0.89 | 0.72-1.10 | 0.27 | not significant (weak wrong-sign point estimate) |
| site_fertility | 0.96 | 0.75-1.23 | 0.74 | not significant |

McFadden pseudo-R2 0.12. Blocked-CV **average precision: logistic 0.096,
additive index 0.095, prevalence (random) 0.028** (mean of 5 seeds ~0.088 / 0.095).

**What it means.** Where beetle / insect-damage salvage happens is driven by
three landscape properties, in order: **proximity to the previous outbreak**
(contagious spread - by far the strongest, matches Kaervemo et al.), **how much
spruce is in the neighbourhood** (host abundance), and **how much fresh clearcut
edge is nearby** (the sun effect). Stand age and site fertility add nothing once
those are in - a genuine finding: at 500 m landscape scale the drivers are
spatial-ecological, not stand-structural. The logistic model and a naive
equal-weight index are neck and neck (~0.095 average precision), both about 3.5x
the 0.028 random baseline. That is the honest ceiling for beetle risk mapping
from open landscape data - a useful ranking, not a precise map, exactly as the
plan's "known-hard-problem" framing anticipated. Figures: `c1_coefficients.png`,
`c1_pr_curve.png`.

### C2 - next
Per-stand Sentinel-2 NDRE / NDMI trajectories over spruce stands, departure from
each stand's own baseline, detection date vs declared salvage date as a
days-early distribution.

---

## 4. Results and what they mean

- **Where beetle / insect-damage salvage occurs is explained by three landscape
  properties, not by stand character:** proximity to the previous (2012-2018)
  outbreak (OR 0.32 per SD - contagious spread, the strongest), neighbourhood
  spruce share (OR 1.58 - host abundance), and nearby fresh clearcut edge
  (OR 1.30 - the sun effect). Stand age and site fertility are null at 500 m
  scale.
- **The model is useful for ranking, not for finding.** Blocked-CV average
  precision ~0.09 vs 0.028 prevalence: the top-ranked areas are several times
  enriched for damage at low recall, but precision falls to the base rate by
  ~50 % recall. A transparent equal-weight index matches the logistic model.
- **This is the expected result** and it is stated as such: bark beetle risk
  mapping from open landscape data is a real but limited signal; the deliverable
  is the ranked driver list and an honest performance number, not a precise map.

---

## 5. Caveats and open items

- Beetle / insect label leans on declaration coding; 1602-only sensitivity check
  pending.
- Background points are "available spruce landscape", not confirmed undamaged.
- Predictors from MS-NFI 2023 for events spanning 2019-2024 - landscape spruce
  content changes slowly, but the mismatch is noted.
- Only 170 cases in the 2019-2024 window - adequate for 5 predictors, not large.
- `age` point estimate has an unexpected sign at 500 m scale (not significant).
- Background = available spruce forest, not confirmed undamaged (SDM assumption).
- MS-NFI 2023 predictors vs a 2019-2024 target; buffered mean limits the mismatch.
- Climate is not a C1 predictor (AOI too small for spatial weather variation);
  `fmi.py` `fetch_daily` works but `stations_near` is finished in Project 2.
- 1602-only label sensitivity check still pending.
