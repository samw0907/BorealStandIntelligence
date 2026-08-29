# DATA_SOURCES.md

Every data source across both projects. Endpoints marked **CONFIRMED** were checked
against the live service or official documentation on 2026-08-26. Items marked
**TO VERIFY** are known to exist but their exact parameters have not been checked —
TASK 00 resolves these and replaces the markers with confirmed values.

Do not write module code that depends on a TO VERIFY item until it is resolved.

Coordinate system throughout: **EPSG:3067 (ETRS-TM35FIN)**.
Licence for Metsäkeskus, Luke and NLS data: **CC BY 4.0** — attribution required
on all derived outputs.

---

## 1. Metsäkeskus (Finnish Forest Centre) — open forest and nature data

Base: `https://avoin.metsakeskus.fi/rajapinnat/`
Service type: GeoServer. WFS, WMS and WCS. Plus a metsätietostandardi REST
endpoint at `/rest/mvrest/`.

**CONFIRMED**: the GeoServer responds at
`https://avoin.metsakeskus.fi/rajapinnat/v2/stand/ows` (returns a valid OWS
ExceptionReport when called without service parameters, which confirms it is live
and is GeoServer).

**TO VERIFY for every layer below**: exact `typeName`, available attribute names
and types, supported output formats, whether paging is required, and any feature
count limit per request.

| Layer | Path | Tier | Used by |
|---|---|---|---|
| Forest stands (metsävarakuviot) | `v2/stand/ows` | FETCH | P1 A, P1 B, P2 D, P2 E |
| Valuable habitats, Forest Act §10 | `v2/habitat/ows` | FETCH | P2 E, P2 F |
| Grid cells 16 m (hila) | `v2/gridcell/ows` | FETCH | P1 A |
| Forest use declarations (metsänkäyttöilmoitus) | `v1/forestusedeclaration/ows` | FETCH | P1 B, P1 C, P2 D |
| Canopy height model (latvusmalli) | `v1/CHM_newest/ows` | BENCHMARK | P1 A |
| Canopy height model area index | `v1/CHM_newest_area_index/ows` | FETCH | P1 A |
| Forest mask (metsämaski) | `v2/forestmask/ows` | FETCH | P1 B |
| Trafficability (korjuukelpoisuus) | `v1/Korjuukelpoisuus/ows` | BENCHMARK | P2 D |
| Surface water flow model | `v1/Pintavesien_virtausmalli/ows` | BENCHMARK | P2 E |
| D8 flow direction | `v1/D8_flow_direction/ows` | BENCHMARK | P2 D |
| Flow accumulation | `v1/FA_flow_accumulation/ows` | BENCHMARK | P2 D |
| Flow network 16 m | `v1/Virtausverkko_16m/ows` | BENCHMARK | P2 E |
| Wetness index 0.5 ha | `v1/Kosteusindeksi_0_5ha/ows` | FETCH + BENCHMARK | P2 D |
| Wetness index 1 ha | `v1/Kosteusindeksi_1ha/ows` | FETCH + BENCHMARK | P2 D |
| Wetness index 4 ha | `v1/Kosteusindeksi_4ha/ows` | FETCH + BENCHMARK | P2 D |
| Wetness index 10 ha | `v1/Kosteusindeksi_10ha/ows` | FETCH + BENCHMARK | P2 D |
| RUSLE erosion model | `v1/RUSLE-eroosiomalli/ows` | BENCHMARK | P2 E |
| Environmental support sites (ympäristötuki) | subsidy layer group | FETCH | P2 F |

**TO VERIFY**: exact paths for the subsidy layer group (nuoren metsän hoito,
terveyslannoitus, suometsänhoito, metsätien tekeminen, luonnonhoito,
ympäristötuki, metsitystuki) and the moose damage (riistavahinko) layer. These
exist and were listed in Metsäkeskus documentation but paths were not recorded.

**TO VERIFY, critical for Project 1 module A**: which stand attribute fields carry
total volume, volume by species (pine / spruce / deciduous), mean diameter, mean
height, basal area, stand age, site type, soil main type — and crucially **the
inventory or laser scanning date field**, since the whole staleness analysis
depends on it. If no date field exists on the stand layer, find where it lives.

**TO VERIFY, critical for module B**: which fields on the forest use declaration
layer carry felling type (regeneration vs thinning vs salvage), declaration date,
and validity period.

**Wetness index note**: the four thresholds are **DTW (depth-to-water)** per Murphy
et al. 2007–2009, computed by Luke from the NLS 2 m DEM. Method fully documented
in `docs/METSA_GIS_RESEARCH_FINDINGS.md` Part G1. Unit is metres; lower is wetter;
below ~1 m is generally considered wet. **TO VERIFY**: raster resolution and
whether values are stored scaled (the separate TWI 16 m product stores values
multiplied by 1000 as integers — confirm whether DTW does anything similar).

---

## 2. Luke (Natural Resources Institute Finland)

### 2a. MS-NFI multi-source national forest inventory rasters

- Most recent set: **2023**. Earlier sets 2021, 2019, 2017, 2015, 2013 available.
- **16 m x 16 m**, EPSG:3067, GeoTIFF, delivered by **UTM200 map sheets**
- **45 themes**: volumes by tree species and timber assortment, biomass by species
  group and tree compartment, canopy cover, mean height, site type, mineral/peat
  main type, FAO FRA class
- Nodata: **32766** = forestry land without satellite cover, **32767** = not
  forestry land or outside country. Different meanings, do not collapse.
- Download: `kartta.luke.fi`
- Tier: FETCH (features for P1 A, soil and species for P2 D and E), also the
  benchmark target for P1 A volume estimates

**TO VERIFY**: exact download mechanism — whether there is a direct HTTP pattern
per map sheet or whether it requires the map interface. Which UTM200 sheets cover
each AOI bbox. The precise theme filenames for: total volume, pine volume, spruce
volume, deciduous volume, mean height, canopy cover, site fertility class,
mineral/peat main type, and standing deadwood volume.

**TO VERIFY**: whether standing deadwood volume is actually among the 45 themes.
Project 2 module E's deadwood deficit analysis depends on it. If it is not
available, that module component needs rescoping — raise it rather than
substituting a proxy silently.

### 2b. DTW depth-to-water rasters

- Same product distributed via Luke open data, **Paituli** (`paituli.csc.fi`),
  Metsäkeskus and Metsähallitus
- Four thresholds: 0.5, 1, 4, 10 ha
- Covers all Finland except Lapland, governed by NLS DEM availability as of
  Nov 2019. Both AOIs are well inside coverage.
- SYKE distributes 8 m mosaics

**TO VERIFY**: Paituli download path and whether it is easier than the Metsäkeskus
WCS route. Native resolution of the Luke product.

---

## 3. National Land Survey (Maanmittauslaitos, NLS)

| Product | Status | Tier | Used by |
|---|---|---|---|
| **2 m elevation model** | Open, CC BY 4.0 | DERIVE input | P2 D (DTW reimplementation), P2 E (RUSLE) |
| **Laser scanning 0.5 p** | Open, CC BY 4.0, 2020 onwards | DERIVE input | P1 A (ALS height metrics) |
| Laser scanning 5 p | **LICENSED AND PAID — DO NOT ATTEMPT** | — | — |
| Topographic database (hydrography, roads) | Open | FETCH | P2 E (mapped hydrography comparison), P2 D (culvert burning) |
| Orthophotos | Open | FETCH | optional |

**TO VERIFY**: download mechanism and whether an API key via OmaTili is required.
Some NLS endpoints need one. Which tiles cover each AOI. File format and tiling
scheme for the 0.5 p point cloud (expected LAZ).

**Legacy note**: a separate 0.5 p product covers 2008–2019. For Project 1, the
2020-onwards product is the one to use, matching the current Metsäkeskus inventory
round.

---

## 4. FMI (Finnish Meteorological Institute)

- Open data WFS at `opendata.fmi.fi`
- Needed: daily minimum and mean temperature, daily precipitation, snow depth
- Used by: P1 C1 (climatic water balance), P2 D (root rot temperature rules,
  frozen season length, dynamic DTW threshold selection)

**TO VERIFY**: WFS stored query names and parameter syntax for daily observations.
Which stations fall within or near each AOI, and their record length — the frozen
season trend analysis needs a long record, so identify the longest continuous
station in or near the Project 2 AOI. Whether a gridded product exists that would
be better than station interpolation.

---

## 5. Copernicus Sentinel

- **Sentinel-2 L2A** — P1 B (change detection), P1 A (spectral features),
  P1 C2 (stress time series)
- **Sentinel-1 GRD** — P1 B (cloud-independent cross-check)
- Access: CDSE, or GEE if that proves simpler. Both AOIs are small enough that
  either works.

Tier: DERIVE ONLY throughout.

Existing portfolio code exists for both — Baltic algal bloom used CDSE API
download plus rasterio, Prey Lang used GEE. Reuse rather than rewrite.

**TO VERIFY**: cloud-free scene availability per AOI per season. Southeastern
Finland has the best statistics in the country but the growing season is short.
Confirm enough usable scenes exist for the composite windows before committing to
the temporal design.

---

## 6. SYKE / Finnish Environment Institute

- Protected areas, CORINE land cover, water bodies, peatland data
- Also distributes DTW 8 m mosaics
- Used by: P2 F (connectivity nodes), P2 E (land cover for RUSLE C factor)

**TO VERIFY**: current download endpoints. SYKE data distribution has moved
between portals; confirm the live route.

---

## Attribution strings

Include in figure captions and JSON reports:

- Metsäkeskus: "Contains data from the Finnish Forest Centre, licensed CC BY 4.0"
- Luke: "Contains Natural Resources Institute Finland MS-NFI data, CC BY 4.0"
- NLS: "Contains data from the National Land Survey of Finland, CC BY 4.0"
- Copernicus: "Contains modified Copernicus Sentinel data [year]"
- FMI: "Contains Finnish Meteorological Institute open data, CC BY 4.0"
