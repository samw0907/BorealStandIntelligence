# TASK 00 — Findings

Discovery run 2026-08-28 – 2026-08-29. Full working notes are in
`boreal-stand-intelligence/data/discovery/` (gitignored), per source:
`metsakeskus/NOTES_1a…`, `NOTES_1b…`, `luke/NOTES_2…`, `NOTES_3…`, `nls/NOTES_4…`,
`fmi/NOTES_5…`, `sentinel/NOTES_6…`, `syke/NOTES_7…`, `aoi/NOTES_8…`.

`DATA_SOURCES.md` now carries the confirmed endpoints. This file records what
**differed from the original plan** and the **open decisions** carried forward.

---

## 1. Coverage summary

Every national dataset covers both AOI bboxes in full: Metsäkeskus WFS vectors and
WCS/download rasters, Luke MS-NFI 2023, Luke DTW (2019 and 2023), NLS 2 m DEM and
topographic database, SYKE protected areas / CORINE, FMI daily stations.

**One coverage gap:** open ALS over the Project 1 SE AOI is 2009–2015 only — no
post-2019 laser scanning. See decision D1 below.

Nothing needed an AOI change. Both bboxes are kept.

---

## 2. Deviations from the plan (documentation corrected)

| # | Plan said | Reality | Action taken |
|---|---|---|---|
| A | Project 1 SE AOI is **spruce-dominant** | MS-NFI 2023: pine 49% / spruce 28% / deciduous 23% by volume; 60% of stocked cells pine-dominant. **Mixed pine–spruce.** | AOI kept. "Spruce dominance" wording corrected to "mixed pine–spruce (spruce ~28%)" in `PROJECT_1` and this file. No methodological impact: A and B are species-agnostic; C works off a `spruce_volume_share` gradient and 28% spruce is ample. |
| B | MS-NFI delivered **by UTM200 map sheets**; `AOI.utm200_sheets()` in the module interface | MS-NFI 2023 is **one whole-Finland GeoTIFF per theme** on the Funet mirror, COG-like, read by window via `/vsicurl`. Not tiled. | `fi_forest_data.luke` fetches the national file and windows it. `AOI.utm200_sheets()` is **not needed for MS-NFI** (still useful for DTW / DEM / ALS, which *are* mapsheet-tiled). |
| C | DTW: one product, **2019**, unit metres, thresholds 0.5/1/4/10 ha, "confirm if scaled like TWI ×1000" | Two vintages. **2019** = Int16, metres **×1000**. **2023 "CMv2"** also exists: Int16, **centimetres (×100)**, adds a **2 ha** threshold, 2023 DEM, cost model improved for **drained peatlands**. | `DATA_SOURCES` §3 documents both and the unit difference. Recommendation: Project 2 Module D uses **2023 CMv2**, thresholds `[0.5,1,2,4,10]`. `REPO_SCAFFOLD` P2 config updated. Confirm at Project 2 start. |
| D | CHM / latvusmalli via Metsäkeskus `v1/CHM_newest/ows` (WCS/WFS) | **Not on Metsäkeskus WCS.** Available as **1 m GeoTIFF** download: `aineistot/Latvusmalli/Karttalehti/{year\|uusin}/` + index zip. | `DATA_SOURCES` §1 raster table updated. Module A benchmark source is the download tree. |
| E | Surface water flow model + subsidy/ympäristötuki layer paths "to verify" | Pintavesien virtausmalli is **WMS-only** on Metsäkeskus — no analysis route found yet. Subsidy sites are the **Kemera** GeoPackage in the `aineistot/` tree; ympäristötuki is a category within it. | Both marked **OPEN** in `DATA_SOURCES`, to close in Project 2 prep (they are Project 2 / Module E–F inputs). |
| F | Open **0.5p ALS, 2020 onwards**, "matching the current inventory round" | The 2020+ 0.5p programme **has not reached SE Finland**. Open ALS for the P1 AOI is **2009–2015** (best coverage 2015). Actual density **~1.6 pts/m²**, not 0.5. | `DATA_SOURCES` §4 updated. Density is good news (feasibility argument more than holds). Vintage gap → decision D1. |
| G | NLS may need an **OmaTili API key** | Official NLS OGC API returns 401 (key needed), **but the Funet mirror carries DEM + ALS + topographic DB with no key.** | Use the mirror. No credentials required. |
| H | FMI: identify the longest continuous station near the P2 AOI | Station "begin" dates ≠ WFS data start; several long nearby records are precip/snow only. **`fmisid 101537` Viitasaari Haapaniemi**, temp+precip+snow from **1970**, is the pick. | `REPO_SCAFFOLD` P2 config: `fmi_station_id: 101537`. |
| I | SYKE via GeoServer WFS | SYKE GeoServer **WFS is disabled** on almost all workspaces. Use the `wwwd3.ymparisto.fi` direct download tree. | `DATA_SOURCES` §7 updated. |
| J | Sentinel: CDSE **or** GEE, "whichever is simpler" | Both viable. | **Decision: CDSE** (single local-reproducible paradigm, S3 band-level reads, reuse Baltic code). GEE = documented fallback. `pipeline.yaml` already has `sentinel2.source: cdse`. |
| K | (implicit) MS-NFI has a standing-deadwood theme for Module E | **MS-NFI 2023 has no standing/downed deadwood volume theme.** The `bm_*_kuolleetoksat_*` layers are dead branches on live trees. | Decision D2 below. |

---

## 3. Confirmed as planned

- Metsäkeskus stand layer **does** carry inventory dates (`measurementdate`,
  `treestanddatadate`, `treestanddatasource`) — Module A staleness analysis is
  viable, no rescoping.
- Forest use declarations **cleanly separate** regeneration / thinning / salvage
  (via `CUTTINGPURPOSE` + `CUTTINGREALIZATIONPRACTICE` + `FORESTDAMAGEQUALIFIER`);
  ~176k declarations in the P1 AOI, current to the day. Module B is well supplied.
- Per-species volume, mean height, and the operational k-NN reference plots +
  weights are on the Metsäkeskus **16 m grid-cell** layer.
- Sentinel-2 composite windows in `pipeline.yaml` are viable (~70 clear scenes per
  JJA window, every year). Keep as-is.
- Both AOI extents are fine; no change.
- EPSG:3067 native for all Finnish sources; MS-NFI nodata 32766/32767 confirmed
  distinct.

---

## 4. Open decisions carried forward

### D1 — Project 1 ALS vintage (before Module A)
Open ALS for the SE AOI is 2009–2015 (best: 2015). Metsäkeskus stand
`measurementdate` ≈ 2023; MS-NFI 2023. ~8-year gap. **Needs a
pros/cons/recommendation before Module A starts.** Rough options:
(a) accept 2015 ALS, reframe Module A so the ALS is the temporally-stale layer
(growth + harvest between ALS and labels — analytically interesting);
(b) seek fresher coverage via the keyed NLS service;
(c) shift the P1 AOI to a part of SE Finland with 2020+ ALS.
Do not change the AOI silently.

### D2 — Project 2 Module E deadwood deficit (before Module E)
MS-NFI 2023 has no standing-deadwood theme. **Deferred** — Sam's call is to revisit
once more of the pipeline is built and the picture is fuller. Candidate directions
(none equal to stand-level m³/ha): drop the component; use the Metsäkeskus habitat
`deadwoodpotential` (qualitative); Luke VMI field-plot deadwood stats at region
level; model from mortality / biomass.

### D3 — Project 2 DTW vintage (at Project 2 start)
Recommendation is 2023 CMv2 with thresholds `[0.5,1,2,4,10]` ha. Confirm, and set
the `fi_forest_data.luke` scaling (cm for 2023) accordingly.

### D4 — small OPEN items (Project 2 prep, low risk)
Pintavesien virtausmalli download route; ympäristötuki field/value in the Kemera
GPKG; CLC2024 release; confirm a 32766 pixel appears in-AOI when MS-NFI is first
pulled; P1 SE FMI station fmisid list for Module C1.

---

## 5. Config values discovered (recorded for Repo 2)

To be written into `regenerative-harvest-planning/config/pipeline.yaml` when Repo 2
is created (also reflected in `REPO_SCAFFOLD.md`):

```yaml
module_d1_dtw_derive:
  validation_catchment_bbox_3067: [414920, 6945300, 429010, 6964880]   # SYKE FI1-14.06.161, 148 km2
  channel_thresholds_ha: [0.5, 1.0, 2.0, 4.0, 10.0]                    # 2023 DTW CMv2 set
module_d2_dtw_extend:
  weather_term:
    fmi_station_id: 101537                                             # Viitasaari Haapaniemi, daily from 1970
```

`boreal-stand-intelligence/config/pipeline.yaml` (Project 1) needed **no changes** —
its placeholders were already concrete and nothing discovered contradicts them
(`sentinel2.source: cdse` matches decision J; composite windows match §6).
