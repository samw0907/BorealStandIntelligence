# Module B - notes, decisions and rationale

Running record of *why* Module B is built the way it is and *what the results
mean*, kept current as the module is built. Source material for the final README.
Plain-language explanations are deliberate - they are what gets reused in the
write-up and in conversation.

Companion planning doc: `PROJECT_1_BOREAL_STAND_INTELLIGENCE.md`, Module B section.
Numeric outputs live in `outputs/p1/module_b/<run_id>/`.

---

## 1. What Module B is

Find where forest was cut between 2021 and 2024 from free Sentinel-2 imagery,
then score those detections against the forest use declarations (metsankaytto-
ilmoitus) that foresters are legally required to file before cutting. The output
is an honest scorecard: how well can free satellite data catch clearcuts vs light
thinnings vs salvage (damage-driven) cuts, and how small a stand can it reliably
see. It also produces a per-stand "this stand was cut since its last inventory
scan" flag that Module A consumes.

This is a recognisable Metsakeskus-style operational workflow: optical change
detection checked against the declaration register.

---

## 2. Design decisions

### 2.1 Sentinel-2 source: AWS Earth Search, collection `sentinel-2-c1-l2a`

- Same ESA/Copernicus L2A product as CDSE would give (surface reflectance,
  Sen2Cor). Different distributor and format: Element 84 / AWS Open Data host it as
  public cloud-optimised GeoTIFFs, queried through the Earth Search STAC API. No
  credentials, no account.
- Kept the whole pipeline local and reproducible; let us read only the AOI and the
  bands we need instead of downloading whole SAFE packages.

### 2.2 The radiometric-offset gotcha, and why Collection 1 removes it

- From processing baseline 04.00 (Jan 2022), ESA store L2A reflectance with a
  +1000 offset (to allow slightly-negative values near zero). Older scenes have no
  offset. So `reflectance = DN * 0.0001` for old scenes but `(DN - 1000) * 0.0001`
  for new ones. Our pre-window is 2021 (no offset), post-window is 2024 (offset) -
  mixing them naively would make the 2021 vs 2024 comparison meaningless.
- **Collection 1** (`sentinel-2-c1-l2a`) is ESA's reprocessing of the entire
  archive onto a single baseline (05.00+). Every scene in both our windows carries
  the identical correction (`scale 0.0001, offset -0.1`). There is no mixed-
  baseline split to handle - one formula for every pixel.
- Belt and braces: the code still reads each scene's declared `raster:bands`
  scale/offset and asserts it matches config, failing loud if any scene deviates.
- Verified after building: the 2021 and 2024 composites have near-identical
  AOI-wide band medians (blue 0.023 both, NIR 0.213 both). A difference between
  them is therefore real change, not a calibration artefact.

### 2.3 Sentinel-1 dropped (2026-08-29)

- SAR is not a core Finnish operational forestry method. The operational products
  this project rebuilds are optical + airborne laser scanning. SAR is a forestry
  *research* topic in Finland.
- Its one strong justification here - filling cloud gaps - does not apply: the SE
  Finland summer S2 composites are 99.8% complete with ~11 clear looks per pixel
  (best optical statistics in the country).
- Adding a SAR log-ratio would make the project less faithful to "what Metsa
  does" and add a whole domain to defend for marginal gain.

### 2.4 Ground truth: two cohorts of the same declarations ("Option C")

- **A forest use declaration is a permit to cut, not a record that the cut
  happened, or when.** We have the filing date, not the cutting date. Our
  detection window is fixed (summer 2021 -> summer 2024). A declaration only
  produces a signal if the cut actually fell inside that window.
- Filed 2019-2020: often cut *before* our 2021 image, or the permit lapsed unused
  -> nothing to see. Filed 2024: often not yet cut by our 2024 image -> no signal
  yet. Filed ~2022-2023: cut within the window -> visible.
- So Module B scores two cohorts:
  - **full register**: all declarations arriving 2019-01 to 2024-06, as-is.
  - **executed-in-window**: declarations arriving 2021-07 to 2023-06 (a first-
    principles temporal filter - filed early enough to be cut before the post
    image, late enough that the cut is after the pre image).
- The gap between the two recalls is itself a finding: it quantifies how much the
  register overstates near-term activity, separately from how good the sensor is.

### 2.5 Thresholds calibrated per felling type, two ways

- Clearcut and thinning have completely different detectability, so one global
  threshold is wrong. Each felling type gets its own dNBR threshold, calibrated on
  the executed-in-window cohort.
- Two calibration views are both reported, because F1 can drift toward the noise
  floor when precision degrades only slowly:
  - **max F1** - the usual choice.
  - **precision >= 0.90** - the first threshold that keeps false alarms low;
    closer to how a detector would actually be deployed.
- For regeneration the two agree closely (dNBR ~0.06 vs ~0.08, both F1 ~0.86),
  which says the clearcut result is robust to the exact threshold.

---

## 3. Method

1. **Composites** (`fi_forest_data.sentinel.fetch_s2_composite`). Per pixel, the
   median of the cloud-free observations in each summer window (SCL mask; pixels
   with < 3 clear looks dropped). 71 scenes for 2021, 69 for 2024. Output: a
   7-band float32 reflectance COG per window, EPSG:3067, 20 m (SWIR-native - no
   upsampling).
2. **Change surfaces** (`src.b_harvest_detection.compute_change_surfaces`).
   dNBR = NBR(2021) - NBR(2024) and dNDMI likewise. Positive = index fell =
   canopy removed. Plus a rasterised forest mask.
3. **Zonal value per declaration** (`zonal_mean`). Mean dNBR over the pixels whose
   centroid falls in the declaration polygon; polygons with < 5 valid pixels or
   < 0.5 ha dropped. Implemented as rasterise-feature-ids + groupby (one raster
   read, vectorised) - fast enough for ~30k polygons in seconds.
4. **Negative control**. A random sample of stand polygons that have no
   declaration overlapping them in the full-register window. Gives the false-
   positive rate of the change surface on undisturbed forest.
5. **Threshold sweep** (`threshold_sweep`). For dNBR thresholds 0.0-0.60:
   precision, recall, F1 overall, per felling type, and per felling type x stand
   area class, for both cohorts. Precision uses the negative-control FP rate
   scaled to the full non-declared stand population.

---

## 4. Results and what they mean

Numbers are the executed-in-window cohort unless stated. Run
`20260829_084509_a9cff61`, dNBR from the 2021 vs 2024 summer composites, zonal
stats scored per polygon (overlap-safe). `report.json` in the run folder.

### 4.1 Clearcut (regeneration felling) - detected reliably

- dNBR >= 0.06: precision 0.90, recall 0.83 (executed cohort). ~4 in 5 executed
  clearcuts caught, with ~1 in 10 detections a false alarm.
- The two calibrations coincide - max F1 and "first threshold reaching precision
  0.90" are both dNBR 0.06 - so the result does not hinge on the threshold choice.
- Full-register recall is only 0.52 - see 4.4.

### 4.2 Thinning - not detectable with optical change

- Precision 0.90 is first reached at dNBR 0.42, where thinning recall is 0.00.
  Max-F1 sits at dNBR 0.02 (the noise floor) with precision 0.64 - not a real
  operating point. There is no threshold that both catches thinnings and keeps
  false alarms low.
- Why: a thinning removes part of the canopy. The burn ratio barely moves, and
  what movement there is sits inside the natural year-to-year variation. There is
  no signal to threshold.
- This is the expected honest result. It is a genuine limitation of free two-epoch
  optical change detection that a Metsa analyst should know about.

### 4.3 Salvage (damage-driven felling) - partial, and expected to be

- dNBR >= 0.12 (max-F1): precision 0.39, recall 0.33 on 168 executed declarations.
  Never reaches precision 0.90. Not usable as a detector.
- Why salvage is hard, and why this is a standard outcome rather than a flaw:
  1. **Intensity varies enormously.** A storm-blowdown salvage can strip ~90% of a
     stand (clearcut-like, strong signal). A bark-beetle salvage often removes
     only the attacked trees - scattered and partial (thinning-like, no signal).
     One threshold cannot fit a class that runs from obvious to invisible; hence
     the flat, low salvage curve.
  2. **The damage already moved the signal before any cut.** A beetle- or
     drought-hit stand has browning canopy across 2021-2024 whether or not it was
     cut, so the "before" state is not healthy forest. This specifically muddies a
     before/after test for salvage.
  3. **Timing is fuzzier.** Salvage declarations are reactive - often filed around
     or after the damage and the cutting - so the temporal cohort filter is looser
     here than for planned fellings.
  4. **Small, noisy sample.** ~48 true positives from 168; the recall estimate
     carries roughly +/- 0.07.
- Context: the Finnish bark-beetle remote-sensing literature consistently finds
  damage/salvage detection from a plain optical before/after is genuinely hard.
  That is *why* the project has a separate Module C for damage, with a
  known-hard-problem baseline stated up front. Metsa's own operational damage
  layers use denser time series and more indices for the same reason.
- Framing for the README: **Module B is a harvest detector** - strong on
  clearcuts, blind to thinnings, partial on salvage. Damage detection proper is
  Module C's job with a purpose-built time-series method.

### 4.4 The register-vs-executed gap

- Full-register clearcut recall 0.52 vs executed-in-window 0.83. So roughly 40% of
  "clearcut" permits filed in our window were cut before our 2021 image, not yet
  cut by 2024, or never acted on.
- The finding for a Metsa analyst: a forest use declaration is not evidence that a
  cut happened, nor when. The register overstates near-term activity. Any workflow
  that joins the register to imagery has to account for this.

### 4.5 Small-stand penalty - mild for clearcuts

- Regeneration recall by stand area (at dNBR 0.06): ~0.80 (0.5-1 ha) rising to
  ~0.89 (5-10 ha).
- A clearcut is a strong enough signal to catch even at ~0.5 ha (12-25 Sentinel
  pixels at 20 m). The plan expected small stands to fail badly; for clearcuts
  they do not. (Thinnings fail at every size - see 4.2.)
- Stated minimum reliably detectable clearcut (recall >= 0.75): the smallest class,
  **0.5-1 ha**. Minimum detectable thinning intensity: not applicable - thinning
  is not detectable at any intensity these declarations represent.

### 4.6 B6 deliverables (this run)

- **`inventory_stale` flag** (`vectors/inventory_stale.gpkg`, for Module A):
  **11,104 of 172,556 stands (13,719 ha, ~3.4% of forest)** show a detected
  clearcut that postdates the stand's last inventory measurement, so their
  attributes are modelled, not observed. Module A must handle these separately.
- **declared-but-not-detected (full register)**: 54,171 stands / 84,467 ha with a
  felling permit on file 2019-2024 that the 2021->2024 change surface does not
  confirm as cut - 58% undetectable thinnings, 41% regeneration (mostly timing,
  see 4.4), <1% salvage. This is *not* a missed-detection count; the missed-
  detection figure is 1 - executed-cohort recall (~17% for clearcuts).
- **detected-but-not-declared**: **243 stands / 277 ha (~0.07% of the AOI)** with
  strong canopy loss and no permit 2019-2024 - undeclared cutting, natural
  disturbance, or noise. Small, i.e. undeclared cutting appears rare (high Finnish
  compliance).
- **AOI harvest map** (`figures/aoi_harvest_map.png`) - first-pass; the polished
  poster version comes at the poster stage.

### 4.8 dNBR vs dNDMI cross-check

- The two independent SWIR-based change metrics agree: candidate-loss pixels
  (> 0.2) overlap with IoU 0.72, and both give ~2% of the AOI as candidate change
  over 3 years - in the expected Finnish harvest-rate range.

---

## 5. Self-assessment (for the README's "limitations" framing)

- **Methodology (7/10).** Clean, reproducible, standard operational pipeline;
  radiometric offset handled properly; the register-vs-executed cohort split is a
  strong design choice; negative results reported honestly. But this is the
  simplest form of the method - two epochs, not a dense time series as Metsakeskus
  runs - the executed-in-window cohort is a temporal heuristic not validated
  against real cut dates, and precision is an estimate from a scaled negative
  control, not a measured count.
- **Link to Metsa (8/10).** Faithful rebuild of a recognisable operational
  workflow on the real datasets, official felling codes decoded from the standard,
  `inventory_stale` targets a documented Metsa pain point. It is by design the
  open-data skeleton of a more sophisticated real system (AI + harvester feedback).
- **Analysability of the outputs (6.5/10).** Numbers are stable and the two
  calibrations converge, so the clearcut result is trustworthy. The ground truth
  is imperfect (permits are not verified cuts), the executed cohort is unvalidated
  against cut dates, no confidence intervals are reported, and salvage (n=168) is
  noisy. Defensible with the caveats stated.

The strong, reliable core is clearcut detection. Thinning and salvage are honest
negatives. The register-vs-executed insight is the distinctive contribution.

## 6. Caveats and open items

- **Legacy declaration codes.** `CUTTINGREALIZATIONPRACTICE` has values 13 and 19
  (used in older declarations) not in the current standard code list. The felling-
  class mapping leans on `CUTTINGPURPOSE`, which is clean, so this does not affect
  the results - but 13/19 should be pinned down for completeness.
- **Negative control is polygons, positives are declaration polygons.** Different
  polygon types; the FP scaling handles the count difference. An alternative would
  be a single stand-based sampling frame throughout.
- **Salvage n is small** (168 executed) - all salvage numbers are statistically
  noisy.
- **The executed-in-window filter is temporal only.** A stand-attribute cross-
  check (declaration whose overlapping stand was re-measured afterwards with
  post-harvest attributes) could sharpen it. Deferred.
