# DATA_SOURCES.md

Every data source across both projects. Endpoints and parameters here were
verified against the live services during **TASK 00 discovery on 2026-08-29**
unless a line says otherwise. Anything still uncertain is marked **OPEN** with a
pointer to where it gets closed.

Coordinate system throughout: **EPSG:3067 (ETRS-TM35FIN)**.
Licence for Metsäkeskus, Luke and NLS data: **CC BY 4.0** — attribution required
on all derived outputs.

TASK 00 findings, deviations from the original plan, and open decisions are in
`docs/TASK_00_FINDINGS.md`. This file is the "where and how"; that file is the
"what we learned".

---

## 1. Metsäkeskus (Finnish Forest Centre) — open forest and nature data

**Two access routes**, both open, no key, EPSG:3067 native:

1. **OGC services**, per layer: `https://avoin.metsakeskus.fi/rajapinnat/{v1|v2}/{layer}/ows`
   (also `/wfs`, `/wcs`). GeoServer. One feature type / coverage per path. There
   is no master catalogue endpoint.
   - WFS 2.0.0: `outputFormat=application/json` (GeoJSON), `SHAPE-ZIP`, CSV, GML.
     `CountDefault` 10000, paging via `startIndex`/`count`, `resultType=hits` for
     counts, `sortBy=FIELD+D`. BBOX: `&srsName=urn:ogc:def:crs:EPSG::3067&bbox=minx,miny,maxx,maxy,urn:ogc:def:crs:EPSG::3067`.
   - WCS 2.0.1: `GetCoverage` with `&subset=E(minx,maxx)&subset=N(miny,maxy)&format=image/tiff`.
     **WCS is enabled for only some rasters** (see table).
2. **Bulk file tree**: `https://avoin.metsakeskus.fi/aineistot/` (Apache autoindex).
   GeoPackage vectors and GeoTIFF rasters split by Karttalehti (map sheet) / Kunta
   (municipality) / Maakunta (region). Cleaner than WFS paging for full-AOI pulls.
   Folders include: `Metsavarakuviot` (stands), `Hila` (grid cells),
   `Metsankayttoilmoitukset` (declarations), `Erityisen_tarkeat_elinymparistokuviot`
   (habitat §10), `Metsamaski`, `Kemera` (subsidy sites), `Korjuukelpoisuus`,
   `Latvusmalli`, `Inventointikoealat` and `Kaukokartoituskoealat` (sample plots).

The `/rajapinnat/rest/mvrest/` metsätietostandardi REST endpoint returns HTTP 401
(needs auth) — not used. Code lists come from the published KOOD workbook instead
(see below).

### Vector layers (WFS)

| Layer | Path | typeName | Tier | Used by |
|---|---|---|---|---|
| Forest stands (metsävarakuviot) | `v2/stand` | `v2:stand` | FETCH | P1 A, P1 B, P2 D, P2 E |
| Valuable habitats, Forest Act §10 | `v2/habitat` | `v2:habitat` | FETCH | P2 E, P2 F |
| Grid cells 16 m (hila) | `v2/gridcell` | `v2:gridcell` | FETCH | P1 A |
| Forest use declarations | `v1/forestusedeclaration` | `forestusedeclaration` | FETCH | P1 B, P1 C, P2 D |
| Forest mask (metsämaski) | `v2/forestmask` | `v2:forestmask` | FETCH | P1 B |

Feature counts (2026-08-29): stand 172,556 in the P1 AOI; forestusedeclaration
175,738 (P1) / 123,571 (P2), current to the day, back to ~2004; habitat 2,099
(P2); forestmask 57,244 (P1). gridcell is ~16 M cells over the P1 AOI — fetch by
sub-tile / small bbox, never whole.

**`v2:stand` — key fields** (43 total):
- Volume: `volume`, `sawlogvolume`, `pulpwoodvolume`, `volumegrowth` (m³/ha). **No
  per-species volume on the stand layer** — species is `maintreespecies` plus
  `proportionpine` / `proportionspruce` / `proportionother`. Per-species volume,
  if needed, comes from `v2:gridcell` or MS-NFI.
- Dimensions: `meanheight`, `meandiameter`, `basalarea`, `meanage`, `stemcount`.
- Site: `fertilityclass`, `soiltype`, `maingroup`, `subgroup`, `drainagestate`,
  `ditchingyear`, `developmentclass`.
- **Inventory dates (Module A staleness — resolved, viable):** `measurementdate`
  (field/laser measurement), `treestanddatadate` (reference date the tree data is
  projected to), `treestanddatasource` (method code — see InventoryMethodType),
  plus `creationtime` / `updatetime`.
- `harvestaccessibility` (korjuukelpoisuus 1–6) is present at stand level — bonus
  for P2 D.
- Proposed cuttings: `cuttingtype` + `cuttingproposalyear` (and `_ccs` variants).

**`v2:gridcell` (16 m hila) — has the full per-species inventory** Module A needs:
`VOLUMEPINE` / `VOLUMESPRUCE` / `VOLUMEDECIDUOUS`, per-species age / basal area /
stem count / diameter / height, totals, `DOMINANTHEIGHT`, `LASERHEIGHT`,
`LASERDENSITY`, `TREEDATADATE`, `GROWTHPLACEDATASOURCE`, and
`SAMPLEPLOTID1..6` + `SAMPLEPLOTWEIGHT1..6` — the operational k-NN reference plots
and weights per cell.

**`forestusedeclaration` — key fields** (44 total, UPPERCASE, mostly coded):
- Felling type (Module B — resolved, cleanly separable):
  - `CUTTINGPURPOSE` (`CuttingPurposeType`): 1 thinning even-aged, 2 thinning
    uneven-aged, 3 regeneration, 4 special, 5 land-use change, **6 forest-damage
    area (salvage)**.
  - `CUTTINGREALIZATIONPRACTICE` (`CuttingRealizationPracticeType`, 19 codes):
    incl. 2 first thinning, 3 thinning, 5 clearcut, and explicit damage codes
    **20/21 storm, 22/23 insect, 24/25 other damage**.
  - `FORESTDAMAGEQUALIFIER` (`ForestDamageQualifierType`, 57 codes): damage agent,
    e.g. **1602 Ips typographus**, 1504 storm, 1503 fire, 1650 moose. Useful for
    Module C2.
  - Module B class mapping: regeneration = purpose 3 or practice {1,4,5,6,7,8,17};
    thinning = purpose 1/2 or practice {2,3,12}; salvage = purpose 6 or practice
    {20–25}.
- Dates: `DECLARATIONARRIVALDATE`, `STANDARRIVALDATE` (dateTime),
  `DECLARATIONARRIVALYEAR`, `COMPLETIONYEAR`, `REGENERATIONYEAR`. No explicit
  validity-period range; `VALID_NOW` (0/1) reads 0 even on 2026 records — treat as
  unreliable, use `DECLARATIONSTATE` (10 arrived / 20 active / 50 old) + dates.

### Raster layers

| Layer | Route | Res | dtype | nodata | notes |
|---|---|---|---|---|---|
| Korjuukelpoisuus | WCS `v1__Korjuukelpoisuus` + `aineistot/Korjuukelpoisuus/` | 16 m | Byte | 0, 254 | pixel value = class 1–6 = `HarvestAccessibilityType` (1 Kelirikko … 6 Talvi); green→red ramp; 254 = unclassified |
| DTW / Kosteusindeksi 1 ha, 4 ha | WCS `v1__Kosteusindeksi_DTW_1_ha`, `..._4_ha` | 2 m | Int16 | 32768 declared; 32767 = capped/dry fill | **2019 vintage, values = metres × 1000.** See §3 for the full DTW picture. |
| DTW 0.5 ha, 10 ha | not on Metsäkeskus WCS (WMS only) | — | — | — | get the full set from Luke (§3) |
| CHM / Latvusmalli | download only: `aineistot/Latvusmalli/Karttalehti/{year|uusin}/` + index zip | **1 m** | GeoTIFF | tbd | **not on Metsäkeskus WCS.** P1 A benchmark source. |
| D8 flow direction | WCS `v1__D8_flow_direction` | 2 m | Int16 | −32768 | P2 D |
| FA flow accumulation | WCS `v1__FA_flow_accumulation` | 2 m | Float32 | NaN | P2 D |
| Virtausverkko 16 m (flow network) | WCS `v1__Virtausverkko_16m` | 16 m | Float32 | 0 | P2 E |
| RUSLE erosion model | WCS `v1__RUSLE-eroosiomalli` | 2 m | Float32 | −9999 | P2 E (t/ha/yr) |
| Pintavesien virtausmalli (surface water flow model) | not on Metsäkeskus WCS (WMS only) | — | — | — | P2 E benchmark — **OPEN**: find download/Paituli route in Project 2 prep |
| Environmental support / subsidy sites | `aineistot/Kemera/{Karttalehti\|Kunta\|Maakunta}/` (GeoPackage) | — | vector | — | P2 F. ympäristötuki is a category inside the Kemera dataset — **OPEN**: confirm its field/value in the GPKG schema in Project 2 prep |

### Code lists

Decoded from the published **KOOD V35** workbook (approved 2026-06-01):
`https://metsatietostandardit-extra.sitowise.com/aineistot/XML/V35/KOOD/excel/MetsatietostandardienSanomakuvauksetKoodistot_V35_03.xlsx`
(saved locally during discovery). Full field→code-list→codes mapping is in
`data/discovery/metsakeskus/NOTES_1a_wfs_vectors.md`. Key ones: `CuttingPurposeType`,
`CuttingRealizationPracticeType`, `ForestDamageQualifierType`, `SoilTypeType`
(codes 10–50 mineral, 60–67 peat, 70/80 organic edge cases),
`FertilityClassType` (1–8), `InventoryMethodType` (`treestanddatasource`: 1 remote
sensing, 2 field, 3 calculated, 4 interpreted, 5 laser scanning, 6 MS-NFI),
`TreeSpeciesType` (1 pine, 2 spruce, 3/4 birch, …).

---

## 2. Luke (Natural Resources Institute Finland) — MS-NFI

### 2a. MS-NFI multi-source national forest inventory rasters

- Set used: **2023** (suffix `_1923`, meaning the 2019→2023 period). Earlier sets
  2021 (`_1721`), 2019 (`_1519`), … available.
- **16 m × 16 m, EPSG:3067, UInt16, GeoTIFF**, internally tiled 512×512 with 8
  overviews (COG-like). **nodata 32767** (band). **32766** = forestry land without
  satellite cover, **32767** = not forestry land / outside country — different
  meanings, do not collapse (32766 not seen in the small discovery window but is
  documented; handle per spec).
- **45 themes**: 24 stand/volume + 21 living-tree biomass compartments (`bm_*`).
- **Distribution — resolved:** INSPIRE Atom feed
  `https://kartta.luke.fi/inspireatom/MVMI-2023.xml` → **one whole-Finland GeoTIFF
  per theme** on the Funet/CSC mirror:
  `https://www.nic.funet.fi/index/geodata/luke/vmi/2023/{theme}_vmi1x_1923.tif`.
  **Not tiled by map sheet** — window the national file (GDAL `/vsicurl` streams a
  windowed read; verified). Full bundle also at `kartta.luke.fi` → `data/mvmi2023.zip`.
  The `kartta.luke.fi` GeoServer `MVMI:` WMS/WCS workspace serves an 8-bit *styled*
  coverage (Byte, nodata 255) — **not analysis-grade; use the Funet GeoTIFFs.**
- Tier: FETCH (species and soil for P2 D/E; features for P1 A), and the benchmark
  target for P1 A volume estimates.

**Theme filenames** (`{name}_vmi1x_1923.tif`):

| need | file | unit |
|---|---|---|
| total volume | `tilavuus_` | m³/ha |
| pine / spruce / birch / other-deciduous volume | `manty_` / `kuusi_` / `koivu_` / `muulp_` | m³/ha |
| mean height | `keskipituus_` | **dm** (÷10 for m) |
| mean diameter | `keskilapimitta_` | cm |
| basal area | `ppa_` | m²/ha |
| stand age | `ika_` | yr |
| canopy cover | `latvuspeitto_` | % |
| site fertility class | `kasvupaikka_` | 1–10 |
| **mineral / peat main type** | `paatyyppi_` | 1–4 (1 mineral, 2 korpi, 3 räme, 4 open mire) |
| data-source index | `mista_` | code |

The Atom feed's English label calls `paatyyppi_` "site fertility class"; that is
wrong — it is the site MAIN type and is the mineral/peat split.

**Standing deadwood volume — NOT in MS-NFI 2023.** Confirmed against the Atom feed
(all 45 themes). The `bm_*_kuolleetoksat_*` layers are dead *branches on living
trees*, not snags. Project 2 Module E's deadwood-deficit component has no MS-NFI
source — **decision deferred** (see TASK_00_FINDINGS.md).

### 2b. DTW depth-to-water rasters

See §3.

---

## 3. DTW depth-to-water (Luke)

**Route — resolved:** Funet/CSC mirror, Apache autoindex, same pattern as MS-NFI:
- `https://www.nic.funet.fi/index/geodata/luke/dtw/2019/` — thresholds 0.5/1/4/10 ha
- `https://www.nic.funet.fi/index/geodata/luke/dtw/2023/` — thresholds
  **0.5/1/2/4/10 ha**, "CMv2" cost model
- GeoTIFF tiles on the NLS UTM10/TM35FIN mapsheet grid, 3000×3000 px = 6×6 km.
  The 2023 dirs (`DTW_INT_CMv2_{050,1,2,4,10}/`) each ship a **tile-index shapefile**
  (`location` field = tile filename; 10,291 tiles). Readable via GDAL `/vsicurl`.
- Rejected routes: Paituli (JS app, indirect `data_id`s); Luke Allas containers
  (`a3s.fi/.../DTW_0X_Xha_updates/`, listing disabled); SYKE (8 m only);
  Metsäkeskus WCS (1 & 4 ha only, and it is the 2019 vintage).

| | 2019 | 2023 (CMv2) |
|---|---|---|
| pixel | 2 m | 2 m |
| dtype / nodata | Int16 / 32767 | Int16 / 32767 |
| **unit** | **metres × 1000 (mm)** | **centimetres (metres × 100)** |
| thresholds | 0.5, 1, 4, 10 ha | 0.5, 1, 2, 4, 10 ha |
| DEM | NLS 2 m, 11/2019 | NLS 2 m, 11/2023 |
| method | D8, breaching pit removal, stream+road burn, cost-accumulation | same + cost model v2, improved for **drained peatlands** (Kesälä et al.) |

**Units differ between vintages — do not assume.** A raw value of 196 is 0.196 m
in 2019, 1.96 m in 2023. Threshold ordering verified for 2023 (0.5 < 1 < 2 < 4 <
10 ha DTW at every pixel; wet-fraction 44% → 13% across a central P2 tile).

**Recommendation for Project 2 Module D:** use the **2023 CMv2** product (newer
DEM, matches the 2023 inventory round, peatland-improved), thresholds
`[0.5, 1.0, 2.0, 4.0, 10.0]`. Decision to confirm at Project 2 start.

---

## 4. National Land Survey (Maanmittauslaitos, NLS)

**Route — resolved:** Funet/CSC mirror `https://www.nic.funet.fi/index/geodata/mml/`,
CC BY 4.0, **no key**. The official NLS OGC API
(`avoin-paikkatieto.maanmittauslaitos.fi`) returns **HTTP 401 without an API key**
— avoided by using the mirror. If a keyed NLS endpoint ever becomes necessary,
stop and ask (permanent constraint).

| Product | Path (mirror) | Spec | Tier | Used by |
|---|---|---|---|---|
| **2 m elevation model** | `dem2m/2008_latest/{block}/{sub}/{tile}.tif` | 3 km tiles, 2 m, EPSG:3067, Float32, nodata −9999; `.tif.aux.xml` sidecars | DERIVE input | P2 D, P2 E |
| **ALS point cloud** | `laserkeilaus/2008_latest/{year}/{block}/{sub}/{tile}.laz` + national index shapefile `2008_latest.shp` (fields `label`, `data_id`, `path`) | LAZ, LAS 1.0–1.2, point format 1, EPSG:3067, 3 km tiles | DERIVE input | P1 A |
| Topographic database | `maastotietokanta/2025/{shp,gpkg}/` + per-mapsheet-block dirs; themes `MTK-virtavesi` (streams), `MTK-vakavesi` (lakes), `MTK-tie` (roads), `MTK-suo` (mires) | national GPKGs are 3–19 GB — use the per-block dirs | FETCH | P2 D (culvert burn), P2 E (hydrography comparison) |
| Laser scanning 5 p | — | **LICENSED AND PAID — DO NOT ATTEMPT** | — | — |
| Orthophotos | `orto/` | — | FETCH | optional |

**ALS — important findings (Module A):**
- Open ALS over the **Project 1 SE AOI is 2009–2015 only** (495 tiles: 2009×159,
  2010×90, 2011×30, 2015×216). **No post-2019 coverage** — the 2020+ 0.5p national
  programme has not reached SE Finland. P2 Central AOI: mostly 2010–2015 + 7 tiles
  from 2020.
- **Actual point density ~1.6 pts/m²** (2015 tile 1.62; 2009 tile 1.58) — not the
  nominal 0.5. A 16 m cell holds ~400 points, not ~128. k-NN / ABA feasibility
  (needs ~0.5) is more than satisfied.
- Consequence: an **~8-year gap** between the ALS (2015) and the Metsäkeskus stand
  `measurementdate` (~2023) / MS-NFI 2023. **Decision deferred** — Module A
  framing / whether to seek fresher ALS / whether to adjust the AOI. See
  TASK_00_FINDINGS.md; pros/cons/recommendation before Module A.

---

## 5. FMI (Finnish Meteorological Institute)

- Open WFS `https://opendata.fmi.fi/wfs`, no key. Stored query
  **`fmi::observations::weather::daily::simple`**. Default parameter set =
  `rrday` (precip, −1 = dry), `tday` (mean T), `snow` (depth, cm), `tmin`, `tmax`
  — all in one call.
- Query by `fmisid` + `starttime`/`endtime` (ISO Z). **Request span is capped**
  (~1 year works, 5 years → HTTP 400) → page by year.
- Used by: P1 C1 (climatic water balance), P2 D/D2/D3 (root-rot temperature rules,
  frozen-season length, dynamic DTW threshold).

**Project 2 long-record station — resolved:** **`fmisid 101537` — Viitasaari
Haapaniemi.** Continuous daily record from **1970** (~55 yr) with tmin/tday/tmax/
rrday/snow all present; ~15 km N of the AOI's north edge (Central Finland is
homogeneous at this scale). Station "begin" metadata (e.g. Jyväskylä airport 1945)
is *not* the WFS data start; many long-record nearby stations are precip/snow only
(Äänekoski Kalaniemi 101541, Jyväskylä Muuratjärvi 101352 — from 1959, no temp).
In-AOI fallbacks: 137208 Jyväskylä lentoasema (temp from ~2000), 101541.

**Gridded product:** no open *daily* gridded obs on the WFS (only
`fmi::observations::weather::monthly::grid`). FMI's 10 km daily climate grid
(1961–) exists as a dataset (Paituli / FMI climate service) — flagged as a
possible Module D2 enhancement, not the default; default is station interpolation.

**Project 1 stations:** 5 stations return daily obs for the SE AOI bbox;
fmisid/name enumeration deferred to Module C1 prep.

---

## 6. Copernicus Sentinel

- **Sentinel-2 L2A** — P1 B (change detection), P1 A (spectral features), P1 C2
  (stress time series). **Sentinel-1 GRD** — P1 B (cloud-independent cross-check).
  DERIVE ONLY. **Project 1 only** — Project 2 does not use Sentinel.
- **Access decision: CDSE** (Copernicus Data Space Ecosystem), not GEE. Keeps the
  project one locally-reproducible Python pipeline; STAC + CDSE S3 allow band-level
  partial reads (no bulk SAFE downloads); reuse the Baltic project's CDSE code. GEE
  is the documented fallback.
- Catalogue queried via CDSE OData
  (`catalogue.dataspace.copernicus.eu/odata/v1/Products`), no auth.

**Scene availability (SE AOI, ~2–3 MGRS tiles) — resolved, config windows viable:**

| year | S2 L2A JJA all | <40% cloud | <20% |
|---|---|---|---|
| 2020 | 180 | 73 | 52 |
| 2021 (config PRE) | 182 | 71 | 40 |
| 2022 | 182 | 58 | 31 |
| 2023 | 176 | 67 | 34 |
| 2024 (config POST) | 184 | 69 | 28 |
| 2025 | 268 | 108 | 59 |

Monthly <40%: 2021 Jun/Jul/Aug = 30/30/11; 2024 = 20/22/27. S1 GRD JJA: 2021 =
284, 2024 = 173. The `pipeline.yaml` composite windows (2021 pre / 2024 post, JJA,
`max_cloud_scene_pct: 40`, `min_scenes_per_composite: 5`) are viable with ~14×
margin — **keep as-is**.

---

## 7. SYKE / Finnish Environment Institute

**Route — resolved:** SYKE direct download tree, no key, EPSG:3067:
- `https://wwwd3.ymparisto.fi/d3/gis_data/spesific/` — vectors (shapefile `.zip`,
  daily updated for protected areas)
  - `luonnonsuojelualueet_valtio.zip` (state PAs, `LsAlueValtio.shp`, 1,091 nat.)
  - `luonnonsuojelualueet_yksityinen.zip` (private PAs, `LsAlueYks.shp`, 16,964)
  - `luonnonsuojelualueet_eramaa.zip` (wilderness, 12 — all Lapland)
  - `natura.zip` (`natura2000sac_alueet.shp` 1,641, `natura2000spa_alueet.shp` 458)
- `https://wwwd3.ymparisto.fi/d3/Static_rs/spesific/clc2018_fi20m.zip` — **CORINE
  Land Cover 2018, 20 m GeoTIFF** (273 MB). Latest at this route; CLC2024 in
  production at SYKE, not yet released. — **OPEN**: check CLC2024 at Project 2 start.
- `https://wwwd3.ymparisto.fi/d3/gis_data/spesific/valumaalueet.zip` — SYKE
  Valuma-aluejako (watershed hierarchy taso1–5 + outlet points). 259 MB;
  `/vsizip//vsicurl/` reads layer + AOI subset without full download.

The `paikkatiedot.ymparisto.fi/geoserver` has **WFS disabled** on almost every
workspace — use the download tree.

- Used by: P2 F (connectivity nodes: state + private + Natura PAs — ~240 polygons
  in the P2 AOI, ample), P2 E (CLC for RUSLE C factor).
- SYKE also mirrors DTW 8 m — not used (Luke 2 m, §3).

---

## 8. AOI composition (MS-NFI 2023, verified 2026-08-29)

| | Project 1 SE | Project 2 Central |
|---|---|---|
| forest land (maaluokka 1) | 56% of AOI | 71% of AOI |
| mean growing stock (forest land) | ~139 m³/ha | ~143 m³/ha |
| species by volume | pine 49% / spruce 28% / deciduous 23% | pine 48% / spruce 34% / deciduous 18% |
| peat share (päätyyppi 2–4) | ~9% | ~13% (Metsäkeskus soiltype cross-check: ~12% of stands) |

- **Project 1 SE is mixed pine–spruce, not spruce-dominant** (the original plan
  assumed spruce dominance). AOI kept; wording corrected. Spruce at 28% (~hundreds
  of km²) is ample for Module C. Modules A and B are species-agnostic.
- **Project 2 peatland is ~13%** — a meaningful minority (~440 km²), enough for
  the trafficability and Metsä Group Plus peatland-CCF work, but not
  peatland-dominated. AOI kept; wording calibrated.

**Module D1 validation catchment — selected:** SYKE Valuma-aluejako taso4
**`FI1-14.06.161`** (Kymijoki system, near Äänekoski), **148.2 km²**, bbox
EPSG:3067 **`[414920, 6945300, 429010, 6964880]`**, fully inside the P2 AOI,
near-headwater, ~37 M cells at 2 m. Fallback: `FI1-14.06.189`, 71.9 km².

---

## Attribution strings

Include in figure captions and JSON reports:

- Metsäkeskus: "Contains data from the Finnish Forest Centre, licensed CC BY 4.0"
- Luke: "Contains Natural Resources Institute Finland MS-NFI data, CC BY 4.0"
- NLS: "Contains data from the National Land Survey of Finland, CC BY 4.0"
- Copernicus: "Contains modified Copernicus Sentinel data [year]"
- FMI: "Contains Finnish Meteorological Institute open data, CC BY 4.0"
- SYKE: "Contains data from the Finnish Environment Institute (SYKE), CC BY 4.0"
