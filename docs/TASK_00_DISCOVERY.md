# TASK 00 — Data Discovery

**This is the first task. Do not start module work before it is complete.**

Purpose: resolve every TO VERIFY marker in `DATA_SOURCES.md` against the live
services, and confirm both AOIs actually have the coverage the plans assume.

Output: an updated `DATA_SOURCES.md` with no TO VERIFY markers remaining, plus a
short `docs/TASK_00_FINDINGS.md` recording anything surprising.

This is deliberately bounded. Do not write pipeline code, do not bulk download,
do not start analysis. Fetch the smallest sample needed to answer each question.

---

## Working method

Work through the sections below in order. After each section, report back what was
found before continuing — Sam wants to review as this goes, not receive it all at
the end. Where something is missing or different from what the plans assume, stop
and raise it rather than choosing a substitute.

Keep every sample download in `data/discovery/`. Total volume here should be small
— tens of megabytes, not gigabytes.

---

## Section 1 — Metsäkeskus WFS

For each layer listed in `DATA_SOURCES.md` section 1:

1. `GetCapabilities` — record the exact `typeName`, supported output formats,
   default and maximum feature counts, and whether paging is required.
2. `DescribeFeatureType` — record every attribute name and type.
3. Fetch a small sample (10–20 features) inside each AOI bbox and inspect actual
   values, not just the schema. Coded values matter: find out what the codes mean
   for felling type, site type and soil type.

**Specific questions that must be answered:**

- Which stand attribute fields carry total volume, volume by species, mean
  diameter, mean height, basal area, stand age, site type, soil main type?
- **Is there an inventory or laser scanning date field on the stand layer?** The
  entire staleness analysis in Project 1 module A depends on knowing when each
  stand was last measured. If it is not on the stand layer, find where it lives.
  If it does not exist anywhere, stop and raise it — module A needs rescoping.
- On the forest use declaration layer: which fields carry felling type,
  declaration date, and validity period? What are the felling type codes, and can
  regeneration, thinning and salvage be distinguished?
- Roughly how many declarations fall inside each AOI bbox, and over what date
  range? Module B needs enough for meaningful validation.
- What are the exact paths for the subsidy layer group and the ympäristötuki
  (environmental support) layer? Module F needs the latter.

For the raster layers (CHM, korjuukelpoisuus, wetness indices, flow products,
RUSLE): confirm WCS access, native resolution, data type, nodata value, and
whether values are scaled. The TWI 16 m product stores values multiplied by 1000
as integers — check whether DTW does anything similar.

---

## Section 2 — Luke MS-NFI

1. Determine the download mechanism from `kartta.luke.fi`. Is there a direct HTTP
   pattern per UTM200 map sheet, or does it require the map interface?
2. Identify which UTM200 sheets cover each AOI bbox.
3. Get the exact theme filenames for: total volume, pine volume, spruce volume,
   deciduous volume, mean height, canopy cover, site fertility class, mineral/peat
   main type.
4. **Confirm whether standing deadwood volume is among the 45 themes.** Project 2
   module E's deadwood deficit depends on it. If absent, stop and raise it.
5. Download one sheet and confirm: EPSG:3067, 16 m pixels, and that both nodata
   values (32766, 32767) appear and behave as documented.

---

## Section 3 — Luke DTW

1. Compare the Paituli route (`paituli.csc.fi`) against the Metsäkeskus WCS route.
   Record which is simpler and use that.
2. Confirm native resolution and value scaling.
3. Download all four thresholds over a small area inside the Project 2 AOI and
   confirm they behave as expected — lower values in valley bottoms and near
   watercourses, and the 0.5 ha product wetter than the 10 ha product.

---

## Section 4 — NLS

1. Determine whether an API key via OmaTili is required, and for which products.
2. Identify the tiles covering each AOI for the 2 m DEM and the 0.5 p laser
   scanning data.
3. Confirm the point cloud format and tiling scheme (expected LAZ).
4. **Download one DEM tile and one ALS tile and confirm they load.** Record actual
   point density in the ALS tile — the plans assume ~0.5 p/m² and the k-NN
   feasibility argument rests on it.
5. Fetch the topographic database hydrography theme over a small area — this is
   needed both for culvert burning in module D1 and as the mapped-hydrography
   comparison in module E.

---

## Section 5 — FMI

1. Find the WFS stored query names and parameter syntax for daily observations.
2. List stations within or near each AOI, with record start dates.
3. **Identify the longest continuous record in or near the Project 2 AOI.** The
   frozen-season trend analysis needs decades, not years. Record the station id
   and write it into `config/pipeline.yaml` (Repo 2, recorded now for later).
4. Confirm daily minimum temperature, mean temperature, precipitation and snow
   depth are all available for that station.
5. Check whether a gridded product exists that would beat station interpolation.

---

## Section 6 — Sentinel scene availability

1. Query scene availability for both AOIs across the candidate composite windows.
2. Report cloud-free scene counts per season per year.
3. **Confirm the composite windows in `config/pipeline.yaml` are viable.** The
   growing season is short and the plans currently use placeholder dates. If the
   windows need moving, propose new ones with the scene counts behind them.
4. Decide CDSE versus GEE on practical grounds and record the reasoning.

---

## Section 7 — SYKE

1. Confirm the live download route for protected areas and CORINE land cover.
2. Fetch protected area boundaries over the Project 2 AOI and count features —
   module F needs enough nodes for connectivity analysis to be meaningful.

---

## Section 8 — AOI verification and validation catchment

1. For each AOI, produce a coverage summary table: does every required source
   cover the full bbox, and where are the gaps?
2. Report forest area as a share of each AOI, and the species composition split.
   Project 1 assumes spruce dominance in the southeast; confirm it.
3. Report peatland share in the Project 2 AOI. The continuous-cover and
   trafficability analyses assume it is substantial; confirm it.
4. **Select the validation catchment for module D1** — a single catchment inside
   the Project 2 AOI, large enough to be meaningful but small enough to reprocess
   at 2 m. Target somewhere in the range of 50–200 km². Write its bbox into
   `config/pipeline.yaml` (Repo 2, recorded now for later).
5. If either AOI turns out to be a poor fit on the evidence, say so and propose an
   alternative with reasons. Do not change the AOIs silently.

---

## Completion

TASK 00 is done when:

- `DATA_SOURCES.md` contains no TO VERIFY markers
- Every null placeholder in the config files is filled
- `docs/TASK_00_FINDINGS.md` records anything that differed from the plans
- A coverage summary table exists for both AOIs
- Any finding that requires rescoping a module has been raised explicitly

Then stop and review with Sam before starting module B.
