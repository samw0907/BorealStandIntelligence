# Metsä Group — GIS & Remote Sensing Research Findings
Created: 2026-08-26. Research base for CAREER_PROJECT_BACKLOG.md Track 2 (Forestry).
Purpose: this document exists so the Metsä/Finnish-forestry research is never repeated.
Project plans that consume it: PROJECT_1_BOREAL_STAND_INTELLIGENCE.md,
PROJECT_2_REGENERATIVE_HARVEST_PLANNING.md

Trigger: networking event with Metsä, 17 September 2026.

---

## PART A — Who Metsä Group is, structurally

Metsäliitto Cooperative is the parent, owned by roughly 90,000–100,000 Finnish
forest-owning members. Group sales ~EUR 6bn, ~9,500 employees, ~30 countries.
HQ: Revontulenpuisto 2, Espoo (local to Sam).

Business areas:
- **Metsä Forest** — wood supply and forest services. THIS IS THE GIS-HEAVY ARM.
  Buys wood from owner-members, plans and executes harvesting, sells forest
  management services, feeds the mills.
- Metsä Fibre — pulp and sawn timber. Äänekoski bioproduct mill (6.5 Mm³/yr wood:
  4.5 Mm³ softwood + 2 Mm³ birch, running since 2017), Kemi bioproduct mill
  (7.6 Mm³/yr pulpwood, from 2023), Rauma sawmill.
- Metsä Board — paperboard. Metsä Wood — construction products.
  Metsä Tissue — tissue and greaseproof. Metsä Spring — venture arm.

Key point for positioning: Metsä Forest is where geospatial work lives, and its
customers are internal (mill wood supply) plus ~100,000 forest owners. The
procurement radius around a specific mill is a real operational unit.

---

## PART B — What Metsä actually does with geospatial data

Sourced from Metsä Forest's own "Data and technology" section and Metsäverkko
documentation. This is their published operational stack, not inference.

### B1. AI growing stock estimation — their flagship tool

Direct paraphrase of their description:

- An in-house application uses **open spatial datasets plus AI/machine learning**
  to assess growing stock.
- Workflow: the forest specialist **draws the felling site polygon on a digital
  map**; the application returns the site's key growing stock data — **log wood
  percentage, sturdiness per tree species, quality, and diameter distribution**.
- Purpose: **reliable wood trade offers without a forest visit**. Frees specialist
  time for owner-member contact.
- Critically: the open-data model is **supplemented with measurement data from
  harvesters and from log measuring devices at Metsä Fibre's sawmills**.
- Built in-house, idea to production in ~2 years, accuracy improving via ML.

STRATEGIC IMPLICATION: the open-data half is fully reproducible. The closed-loop
calibration against measured harvester outturn and sawmill log measurement is
their genuine moat. The honest framing for this project: rebuild the open half,
name the missing half precisely, explain why it matters. This project targets
Metsa Group only.

### B2. Satellite + AI damage maps in Metsäverkko

- Metsäverkko (owner-member web/mobile service) carries **continuously updating
  insect damage and storm damage map layers based on satellite imagery and AI**.
  Confirmed independently (XAMK/Metsäkeskus presentation material notes that both
  Metsä Group's and the forest management associations' web services carry these).
- The insect damage layer detects **stress-related change before it is visible to
  the human eye**. Displayed only over the owner's own holdings. Red shading
  prompts a field check and contact with the forest specialist.
- Context: Metsäkeskus separately runs national forest damage monitoring, using
  free 10 m imagery for felling legality and, from 2024, **higher-resolution
  imagery down to 0.5 m** for detecting dead trees and tree groups.

### B3. Other published data/technology items

- AI-based **fixed pricing for young stand management**.
- **Satellite positioning of forest machinery** (efficiency).
- **Power line proximity** layer for forest work safety.
- **MetsäTrace** — cloud solution managing EUDR reference data, linked to Metsä's
  ERP and to the EU TRACES system. Finland-side reference number transfer uses
  ForestHub and Forest Webhub.

---

## PART C — Strategic and regulatory drivers

### C1. Regenerative forestry (the headline programme)

Goal: **verifiably strengthen the state of forest nature by 2030.**

The ten stated principles: native tree species; diversification of tree species;
increasing old trees; increasing varied decayed wood; diversification of
structural features; protection of valuable habitats; improved peatland
management and water protection; special measures for herb-rich forests, ridge
(sunlit) areas and burned areas; species-specific measures; **improving the
biodiversity network**.

CRITICAL QUOTE FOR PROJECT FRAMING — from their "Objectives and indicators"
section: key biodiversity measures include tree species ratios, decaying trees and
forest age structure; indicators must be **common across actors and scientifically
justified**; the monitoring system **should make use of existing inventory data and
monitoring**; and both new technology and field species inventories are required.

That is an explicit, published statement of an unmet analytical need. Any project
that derives regenerative-forestry indicators from existing national inventory
data is aimed straight at it.

"Improving the biodiversity network" is landscape connectivity, named as a
principle. This is the hook for the connectivity module.

### C2. Metsä Group Plus — quantified and spatially explicit

A wood-trade-specific management model for owner-members, with a per-hectare bonus
compensating lost timber income. Measures agreed per trade.

| Measure | Current practice | Metsä Group Plus |
|---|---|---|
| Retention trees (regeneration felling) | Per certification; ≥20 dead trees/ha | **30/ha, >15 cm dbh at 1.3 m** |
| High biodiversity stumps | 4/ha | **10/ha** (crowns left in forest) |
| Waterway buffer zone | Depends on waterway | **10–30 m** |
| Protective thicket (young stand mgmt) | 1 per 3 ha | **1 per 1 ha** |
| Lush drained spruce-dominated peatland | Regeneration felling | **Continuous cover (group/selection cutting), no ditch repair, no regeneration obligation** |
| Retention tree group burning | — | Metsä-funded on suitable sites |

Every one of these is directly implementable as a spatial rule.

### C3. 2030 sustainability targets (forest-relevant)

- 100% of regeneration felling sites have retention trees
- 100% of felling sites have high biodiversity stumps
- 0% of sites have spruce remaining as the only species after young stand management
- **10,000 measures to increase natural biodiversity**
- +30% forest regeneration and young stand management
- +50% forest fertilisation
- **+30% share of continuous cover forestry in peatland forest regeneration**
- Rationale given for the peatland target: greenhouse gas emissions are highest in
  lush peatlands, so continuous cover forestry is encouraged there.

The 10,000-measures target implies a siting question: where do measures deliver
most benefit? That is a spatial prioritisation problem nobody has published an
answer to.

### C4. EUDR

Applies from **30 December 2026** — three months after the networking event, so it
is live and unresolved for them. Due diligence system covers information
collection (wood origin and production chain verification), risk assessment
(EUDR country risk classes plus FSC/PEFC chain-of-custody), risk mitigation.
MetsäTrace handles reference data; TRACES had a production break as of the May
2026 Commission update package.

Relevance: geolocation of plots and plot-level legality/deforestation evidence are
inherently geospatial. Lower priority than the operational modules for a Finnish
audience (Finland is low-risk), but a strong talking point.

---

## PART D — The Finnish open data landscape

This is the single biggest enabler. Everything below is free and, except where
noted, CC BY 4.0. Coordinate system throughout: **EPSG:3067 (ETRS-TM35FIN)**.

### D1. Metsäkeskus (Finnish Forest Centre) — avoin.metsakeskus.fi

Live GeoServer confirmed responding 2026-08-26. WMS / WCS / WFS plus a
metsätietostandardi REST endpoint at `/rest/mvrest/`.

Core layers (`https://avoin.metsakeskus.fi/rajapinnat/...`):

| Dataset | Endpoint | Notes |
|---|---|---|
| Forest stands (metsävarakuviot) | `v2/stand/ows` | Species volumes, age, site type, treatment proposals |
| Valuable habitats (Forest Act §10) | `v2/habitat/ows` | Legally protected habitat polygons |
| Grid cells 16 m (hila) | `v2/gridcell/ows` | Inventory unit; within-stand variation |
| **Forest use declarations (metsänkäyttöilmoitus)** | `v1/forestusedeclaration/ows` | Legally required pre-harvest notification, with geometry |
| Canopy height model (latvusmalli) | `v1/CHM_newest/ows` | ALS-derived; also `CHM_newest_area_index` |
| Forest mask | `v2/forestmask/ows` | |
| **Trafficability (korjuukelpoisuus)** | `v1/Korjuukelpoisuus/ows` | Raster, terrain bearing capacity, **6 classes**, computed from ALS + NLS terrain database |

Surface water movement stack (all v1):
`Pintavesien_virtausmalli` (surface flow model), `D8_flow_direction`,
`FA_flow_accumulation`, `Virtausverkko_16m` (flow network 16 m),
`Kosteusindeksi_0_5ha / 1ha / 2ha / 4ha / 10ha` (wetness index at five catchment
thresholds), `RUSLE-eroosiomalli`.

Subsidy / nature-management layers (Metka and Kemera eras), stand or line/point
geometry: young stand management, health fertilisation, peatland forest management
(suometsänhoito), forest road construction, nature management (luonnonhoito),
**environmental support (ympäristötuki — voluntary conservation sites)**,
afforestation, and **moose damage compensation claims**.

NOTE: Metsäkeskus is mid-way through a data model reform ("tietomallin uudistus")
that will change open forest data distribution. Version pinning matters — the
version is in the URL path (`/v1/`, `/v2/`).

### D2. Luke (Natural Resources Institute Finland) — MS-NFI

Multi-source National Forest Inventory raster maps, most recent set **2023**
(eighth freely available set; also 2021, 2019, 2017, 2015, 2013...).
- **16 m × 16 m pixels**, EPSG:3067, GeoTIFF, delivered by UTM200 map sheets
- **45 themes**: volumes by tree species and timber assortment, biomass by species
  group and tree compartment, canopy cover, mean height, site type, mineral/peat
  main type, FAO FRA class
- Produced from NFI field plots (51,833 plots in the 2021 product) + Sentinel-2 +
  Landsat 8 + NLS topographic database
- Nodata conventions: 32766 = forestry land without satellite cover;
  32767 = not forestry land or outside country
- Download: kartta.luke.fi

Multi-date MS-NFI (2013→2023, consistent 16 m) is a ready-made change baseline.

### D3. National Land Survey (Maanmittauslaitos, NLS)

- **Laser scanning 0.5 p — OPEN** (CC BY 4.0). Thinned from the 5 p national
  programme data, 2020 onwards. Plus a legacy 0.5 p 2008–2019 product.
- **Laser scanning 5 p — LICENSED AND PAID.** Requires strong identification and
  purchase. THIS IS A HARD CONSTRAINT: raw high-density point clouds are not
  available for a portfolio project.
- WORKAROUND: the Metsäkeskus canopy height model (D1) is derived from the 5 p
  data and is open. Use it for canopy structure instead of processing point clouds.
- DEM, topographic database (roads, buildings, hydrography themes), property
  register map, orthophotos. GeoPackage/GeoJSON download via Karttapaikka.
- INSPIRE WMS/WFS available; some endpoints need an API key via OmaTili.

### D4. Other

- **FMI open data** (opendata.fmi.fi) — weather observations and climate. Needed
  for the root rot temperature rules and drought/temperature-sum work.
- **SYKE / Finnish Environment Institute** — protected areas, CORINE land cover,
  water bodies, peatland data.
- **Copernicus** — Sentinel-1 and Sentinel-2, via CDSE or GEE.

### D5. The national inventory cycle (matters for data currency)

- Metsäkeskus inventory is ALS + aerial imagery + field plots. Second nationwide
  remote-sensing-based round started 2020, following the national laser scanning
  and aerial imagery programme coordinated by NLS.
- **Laser scanning cycle: 6 years**, ~5 points/m², last areas scanned 2025.
  Individual survey blocks ~300,000 ha. Northernmost Lapland at half the rate.
- **Aerial imagery every 3 years** (scanning year and mid-cycle).
- Inventory unit is the **16 m grid cell**; new in this round is a
  crown-delineated tree group unit, combined to produce stand-level attributes.
- **Between inventories the data is updated with growth models**, and harvests are
  back-filled: if a thinning occurred, the stand is thinned in the database using
  standard thinning models. Metsäkeskus states plainly that this does not produce
  fully correct remaining-stock information, but prioritises speed of update for
  wood procurement planning.

THIS IS THE MOST IMPORTANT METHODOLOGICAL FINDING IN THIS DOCUMENT.
The "ground truth" for any stand-attribute model is itself partly modelled for any
stand touched since its last scan. Detecting those stands and handling them
explicitly is a real contribution, and it is the reason harvest detection must
precede stand-attribute modelling rather than follow it.

---

## PART E — Domain rules worth knowing (they are deterministic and spatial)

### E1. Root rot (juurikääpä, Heterobasidion) and stump treatment

Governed by the Forest Damages Prevention Act. Two species: Heterobasidion
parviporum on spruce, H. annosum on pine. Spreads mainly via fresh stump surfaces;
spores disperse when mean temperature exceeds about +5 °C. Range expanding north
with warming.

Treatment is **mandatory** where, on the risk area:
- mineral soil: pine and/or spruce together exceed **50% of stand volume** before
  felling
- peat soil: spruce exceeds **50% of stand volume** before felling

Timing: **1 May to 30 November**. May be needed earlier in a warm spring once daily
mean temperature stays above +5 °C; continue in autumn until frosts.

Exemption: not required if the **minimum temperature in the felling site's
municipality has been below −10 °C during the three weeks preceding felling**.

Practical constraints: all conifer stumps over 10 cm diameter must be treated; the
agent must cover at least 85% of each cut surface; application within 3 hours of
felling. **Urea must not be used within 10 m of watercourses and small waters.**

Recommendation (broader than the legal minimum): treat spruce root rot across the
whole spruce range; treat pine root rot south of Lapland. Continuous cover forestry
is best done in winter (less stem damage, low root rot risk) and is **not
recommended where root rot is present or risk is high**.

Every element of this is computable from stand data + soil type + FMI temperature
+ hydrography. It produces a per-stand, per-date obligation map.

### E2. Spruce bark beetle (Ips typographus / kirjanpainaja)

- Damage in Finland **clusters in spatial hotspots**; drivers are stand structure,
  landscape context and climate. Active Finnish research (UEF, Luke) with 2025–26
  publications, including a stand-level damage probability model built over
  ~2 million stands / ~11.4 M ha using inventory, disturbance history and climate.
- Salvage logging records (2012–2020, 4,691 SBB cases) have been used as the
  response variable in published Finnish work — and salvage felling is recorded in
  the forest use declaration system, which is open.
- Known predisposing factors from the literature: spruce dominance and maturity,
  drought, **forest edge microclimate ("sun effect")**, prior windthrow providing
  breeding material, proximity to existing infestations, local population size.
- Long-term Finnish monitoring site: Ruokolahti, southeastern Finland
  (61°29'N, 29°03'E) — storm-hit 2010, outbreak from ~2014.
- HONESTY REQUIREMENT: a critical review of 26 early-detection studies concluded
  that **timeliness and accuracy remain insufficient for efficient management
  regardless of platform, sensor or resolution**. Trees begin drying before visible
  mortality, which is why detection is attempted, but nobody has solved it. Any
  claim of successful early detection must be stated against this baseline.

### E3. Trafficability

Metsäkeskus korjuukelpoisuus is a **modelled** raster in 6 bearing-capacity
classes, computed from ALS and the NLS terrain database — not measured, and not
dynamic. Real operational decisions depend on current soil moisture and ground
frost. Warming winters shortening the frozen-ground harvesting season is a live
Finnish wood supply problem.

---

## PART F — What this means for positioning

Metsä's three published AI/satellite products map exactly onto three analyses:
growing stock estimation, harvest/storm change detection, insect damage. Rebuilding
those from open data alone is a direct, legible demonstration.

Their regenerative forestry programme has a stated, unmet monitoring need, a set of
quantified spatial rules (Metsä Group Plus), and a siting question (10,000
measures). That is a second, distinct demonstration aimed at a different set of
people in the same organisation.

At a networking event you will meet both wood-supply/data people and
sustainability people. Two projects, not one, gives a relevant answer to each.

---

## PART G — Methods that already exist and are documented (added 2026-08-26)

Researched after a decision to derive rather than only download. These are the
published methods behind the official products, which makes them reimplementable
and benchmarkable.

### G1. DTW (depth-to-water) — the wetness index method

Murphy et al. 2007, 2008, 2009. As implemented by Luke for Finland:

1. Base data: **NLS 2 m elevation model** (open).
2. Pre-processing for continuous flow: road and channel crossings (culverts) are
   lowered in the surface model to channel level, so flow routes are correct.
3. Remaining pits removed by **carving** (Lindsay 2016).
4. Flow direction and flow accumulation via **D-infinity** (Tarboton 1997).
   Slope taken from the ORIGINAL, unmodified surface.
5. Channel network initiated at **four thresholds: 0.5, 1, 4, 10 ha**. The
   threshold is the contributing area at which rainfall is sufficient to produce a
   visible surface channel.
6. DTW = slope-weighted cumulative distance to the nearest channel, **in metres**.
   Lower = wetter. Below ~1 m is generally considered wet.

Threshold interpretation (this is the key to the extension):
- 0.5 ha — very wet: after snowmelt, or heavy/prolonged rain
- 1 ha — wet, wetter than average
- 4 ha — drier late-summer conditions
- 10 ha — drier than average

STATED LIMITATION, in Luke's own product description: DTW is based **entirely on
the elevation model, so soil type and weather conditions are not taken into
account, and this causes uncertainty** (citing Ågren et al. 2015, Lidberg et al.
2020).

Documented operational uses: delineating stream buffer zones, avoiding rut damage
(urapainumat) in harvesting, planning small-water crossing points, identifying
moist habitats of biodiversity value. Hilli & Mykrä et al. 2022 studied DTW for
stream buffer design and found the DTW 0.8–1.2 m band characterised by species
typical of upland forest, i.e. the wet zone ends around there.

Availability: Luke open data portal, Paituli (paituli.csc.fi), Metsäkeskus and
Metsähallitus systems. Covers all Finland except Lapland, governed by NLS DEM
availability as of Nov 2019. SYKE distributes 8 m mosaics at four thresholds.

A separate **TWI 16 m** product also exists (Luke/Metsäkeskus), D-infinity based,
with values multiplied by 1000 and stored as integers.

### G2. Forest attribute estimation — the Finnish operational method is k-NN

The Finnish MS-NFI uses a **non-parametric k-nearest neighbour method**
(Tomppo 1990/1991; Tomppo & Halme 2004), and from MS-NFI-9 onward an
**improved k-NN (ik-NN)**. Reported parameterisation: **k = 5 used most
frequently**.

Mechanics: for each target pixel, find the k nearest NFI field plots in
n-dimensional feature space (Euclidean distance over remote sensing features);
estimate stand variables as a distance-weighted average of those neighbours,
weights being inverse Euclidean distance raised to a power g. Training data are
restricted to the same satellite image and **map stratum (mineral soil vs
peatland)**, and to within an upper limit of geographical distance from the target
pixel. Estimation parameters chosen operationally include image features, distance
measure, k, DEM use, stratification, and the geographical reference area.

Metsäkeskus grid-cell inventory works the same way in principle: selected laser and
aerial image features are used to find the best-matching field plots for each 16 m
cell, and attributes are estimated from them.

FEASIBILITY CONFIRMATION AT OPEN-DATA POINT DENSITY: Tuominen et al. 2014 (Silva
Fennica) estimated total growing stock volume, species-specific volumes (pine,
spruce, deciduous), mean diameter and mean height by k-NN from ALS with a
**returned pulse density of 0.54 per square metre** — essentially the same as the
open NLS 0.5 p product. Ground elevation per lidar point was interpolated from the
two nearest ground pulses with inverse distance weighting.

Sample size guidance from the literature: typically 300–700 plots per inventory
area for a comprehensive variable set; as few as 50–100 can suffice when only
growing stock volume is needed.

IMPLICATION: machine learning is not required here, and introducing it by
default would be less faithful to the domain, not more sophisticated. The
correct default methods are the area-based approach with regression, and
k-NN / k-MSN imputation. Both are transparent and both are what the Finnish
sector actually runs. ML stays available to raise per module if a specific
need emerges.
