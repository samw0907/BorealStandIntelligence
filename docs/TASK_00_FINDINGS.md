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

No coverage gaps. (Follow-up check after the initial discovery run: the Project 1
SE AOI **does** have recent open 0.5 p ALS — 2019–2023 national-programme flights,
all "products available" — reachable via the NLS OGC API with a free key. The
key-free Funet mirror only carries the 2008–2019 legacy round for this area. See
decision D1 below.)

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
| F | Open **0.5p ALS, 2020 onwards**, "matching the current inventory round" | Correct after all — the SE AOI **is** covered by 2019–2023 national-programme 0.5 p flights (Puumala 2019, Lappeenranta 2020, Savonlinna 2021, Juva 2022, Parikkala 2023), all "products available". The key-free Funet mirror only carries the 2008–2019 legacy round (2009–2015 here). | Decision D1 → use the 2020+ product via the NLS OGC API. |
| G | NLS may need an **OmaTili API key** | The DEM, topographic DB and legacy ALS are on the Funet mirror with no key. The **2020+ 0.5 p ALS** needs the NLS OGC API, which needs a **free** key (email registration, open CC BY 4.0 data). | Sam registers the free key at Module A start; supplied via `.env` (gitignored), never committed. Everything else stays key-free. |
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

## 4. Decisions

### D1 — Project 1 ALS source — RESOLVED
Use the **2020+ open 0.5 p ALS** (2019–2023 flights, "products available") for the
SE AOI, via the NLS OGC API with a free key. AOI unchanged, no re-verification.
Module A becomes a clean, current methodology reproduction — 2019–2023 ALS
benchmarked against MS-NFI ~2021/2023 and same-era field plots — with the exact
epoch/clip decided at Module A start (the AOI is a patchwork of flight years;
likely clip to the Savonlinna 2021 + Puumala 2019 blocks, or match the mosaic to
MS-NFI 2021).
- The "inventory staleness" question is **not** a Module A dimension. It stays a
  standard Module B output: the per-stand `inventory_stale` flag (stands harvested
  since their last scan). Module A honours `exclude_stale_stands: true`.
- 2008–2015 legacy ALS from the Funet mirror is the documented fallback only.
- Sam registers the free NLS key when Module A starts (Claude will point to where);
  key lives in `.env` (gitignored), never committed, never read by Claude.

### D3 — Project 2 DTW vintage — RESOLVED
Project 2 Module D uses **Luke DTW 2023 CMv2**, thresholds `[0.5, 1, 2, 4, 10]` ha,
values in cm. Recorded in `REPO_SCAFFOLD.md` P2 config.

### D2 — Project 2 Module E deadwood deficit — DEFERRED (before Module E)
MS-NFI 2023 has no standing-deadwood theme. **Deferred** — Sam's call is to revisit
once more of the pipeline is built and the picture is fuller. Candidate directions
(none equal to stand-level m³/ha): drop the component; use the Metsäkeskus habitat
`deadwoodpotential` (qualitative); Luke VMI field-plot deadwood stats at region
level; model from mortality / biomass.

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
