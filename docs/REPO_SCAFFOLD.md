# REPO_SCAFFOLD.md

Structure, interface contracts, configuration schema and acceptance criteria for
both projects. This is the "what shape" document. The project plans say what to
compute; this says what the code and outputs must look like.

---

## Two repos, one working directory

```
finnish-forest/                        # working dir, NOT a git repo
  CLAUDE.md                            # operative during development
  docs/                                # working copies of planning documents
  .venv/
  boreal-stand-intelligence/           # REPO 1
  regenerative-harvest-planning/       # REPO 2
```

### REPO 1 — `boreal-stand-intelligence`

```
boreal-stand-intelligence/
  CLAUDE.md
  README.md                            # project and results, written last
  requirements.txt
  pyproject.toml                       # minimal packaging: pip install -e . --no-deps
  .flake8
  Dockerfile
  docker-compose.yml                   # pipeline + test services
  .dockerignore
  .github/workflows/ci.yml
  docs/
    PROJECT_1_BOREAL_STAND_INTELLIGENCE.md
    METSA_GIS_RESEARCH_FINDINGS.md
    DATA_SOURCES.md
    REPO_SCAFFOLD.md
    TASK_00_DISCOVERY.md
  config/
    aoi_southeast.yaml
    pipeline.yaml
  fi_forest_data/                      # data access module
    __init__.py
    aoi.py
    metsakeskus.py
    luke.py
    nls.py
    fmi.py
    sentinel.py
    io.py                              # COG writing, run metadata, attribution
    validate.py                        # config schema validation
  src/
    __init__.py
    b_harvest_detection.py
    a_stand_estimation.py
    c1_beetle_susceptibility.py
    c2_beetle_stress.py
    figures.py
    run.py
  tests/
  data/                                # gitignored
  outputs/                             # gitignored
```

### REPO 2 — `regenerative-harvest-planning`

Identical shape. `fi_forest_data/` is copied across from Repo 1 when Project 2
starts, with any Project 2 additions noted in that repo's README. `src/` contains
`d1_dtw_derive.py`, `d2_dtw_extend.py`, `d3_rootrot_rules.py`,
`e_plus_site_planning.py`, `f_connectivity.py`, `figures.py`, `run.py`.
`config/` contains `aoi_central.yaml` and `pipeline.yaml`. `docs/` carries
`PROJECT_2_REGENERATIVE_HARVEST_PLANNING.md` plus the same shared documents.

Module filenames carry their letter prefix so the mapping to the project plans is
unambiguous.

### Why the data access module is copied, not shared

Both repos need code to fetch Metsäkeskus, Luke, NLS and FMI data — roughly 500
lines. Sharing it as an installed package would prevent drift between copies, but
these are portfolio pieces built in sequence and then frozen, so there is no
maintenance window in which drift could happen. Each repo staying independently
clonable is worth more than the theoretical tidiness. Copy it, and note in Repo 2's
README that the module originated in Repo 1.

### Which document to load per task

| Task | Load alongside CLAUDE.md |
|---|---|
| Repo creation | this file |
| TASK 00 discovery | `DATA_SOURCES.md`, `TASK_00_DISCOVERY.md` |
| Module B | `PROJECT_1` (B section), `SAR_METHODOLOGY_FUNDAMENTALS.md`, this file |
| Module A | `PROJECT_1` (A section), `RESEARCH` Part G2 |
| Module C | `PROJECT_1` (C section), `RESEARCH` Part E2 |
| Module D | `PROJECT_2` (D section), `RESEARCH` Parts G1 and E1 |
| Modules E, F | `PROJECT_2`, `RESEARCH` Parts C2 and C3 |
| Posters | both project plans, `GIS_PROJECT_CONTEXT.md` for house style |

Run `/clear` between tasks rather than letting one session sprawl.

---

## Per-repo CLAUDE.md template

Each repo gets a short CLAUDE.md for anyone cloning it alone. Keep under about 60
lines — the working-directory CLAUDE.md is operative during development.

```markdown
# CLAUDE.md — <repo name>

<One paragraph: what this repo is and which project it belongs to.>

Part of a two-project portfolio piece targeting Metsä Group. Companion repo:
`<the other project repo>`.

## Hard constraints
- Machine learning is not the default approach. Methods are k-NN imputation,
  area-based regression, logistic regression, and documented operational
  methods. ML is not forbidden, but introducing it is a design decision to
  raise and agree first, not a silent substitution. See docs/.
- Do not attempt NLS 5 p laser scanning data — licensed and paid.
- EPSG:3067 throughout. Reproject once at ingest.
- MS-NFI nodata 32766 and 32767 have different meanings. Do not collapse them.
- CC BY 4.0 attribution required on all outputs.
- No emojis. Comments sparingly, plus a file path comment at the top of each file.
- Never delete data, drop a database, or force-push without stopping first and
  explaining the risk in detail.

## AOI
EPSG:3067 bbox: <bbox>

## Where things are
- `docs/PROJECT_*.md` — the plan
- `docs/METSA_GIS_RESEARCH_FINDINGS.md` — background and published methods
- `docs/DATA_SOURCES.md` — endpoints, schemas, field mappings
- `docs/REPO_SCAFFOLD.md` — module contracts, config schema, acceptance criteria

## Status
<current module, current state>
```

## fi_forest_data — public interface

Keep this small and stable. Both projects depend on it, so changes ripple.

```python
# fi_forest_data/aoi.py
class AOI:
    name: str
    bbox_3067: tuple[float, float, float, float]
    crs: str = "EPSG:3067"

    def to_polygon(self) -> shapely.Polygon: ...
    def utm200_sheets(self) -> list[str]: ...      # for MS-NFI sheet selection
    def verify_coverage(self, sources: list[str]) -> dict: ...
```

```python
# fi_forest_data/metsakeskus.py
def fetch_layer(layer_key: str, aoi: AOI, version: str) -> gpd.GeoDataFrame: ...
def fetch_raster(layer_key: str, aoi: AOI, version: str) -> str: ...  # path to COG
```

```python
# fi_forest_data/luke.py
def fetch_msnfi(theme: str, aoi: AOI, year: int = 2023) -> str: ...
def fetch_dtw(threshold_ha: float, aoi: AOI) -> str: ...
```

```python
# fi_forest_data/nls.py
def fetch_dem(aoi: AOI, resolution_m: int = 2) -> str: ...
def fetch_als(aoi: AOI, subset: shapely.Polygon | None = None) -> list[str]: ...
def fetch_topographic(theme: str, aoi: AOI) -> gpd.GeoDataFrame: ...
```

```python
# fi_forest_data/fmi.py
def fetch_daily(station_id: str, start: date, end: date,
                variables: list[str]) -> pd.DataFrame: ...
def stations_near(aoi: AOI, max_distance_km: float) -> pd.DataFrame: ...
```

```python
# fi_forest_data/io.py
def write_cog(array, profile, path: str, attribution: str) -> None: ...
def run_metadata(config: dict, fetch_dates: dict) -> dict: ...
```

Rules for this package:
- Every fetch caches to `data/raw/` and returns from cache on repeat calls.
- Every fetch records source, endpoint version and fetch date into run metadata.
- Reprojection to EPSG:3067 happens here at ingest, once, and nowhere else.
- No analysis logic. This layer only gets data and hands it over.

---

## Configuration schema

Everything parameterised. No magic numbers in module code.

```yaml
# boreal-stand-intelligence/config/pipeline.yaml
aoi: config/aoi_southeast.yaml

sentinel2:
  source: cdse                        # cdse | gee
  composite_windows:
    pre:  {start: "2021-06-01", end: "2021-08-31"}
    post: {start: "2024-06-01", end: "2024-08-31"}
  max_cloud_scene_pct: 40
  cloud_mask: scl                     # SCL classes to exclude listed below
  scl_exclude: [3, 8, 9, 10, 11]
  min_scenes_per_composite: 5
  indices: [ndvi, evi, nbr, ndre, ndmi]

sentinel1:
  enabled: true
  orbit: ascending
  polarisations: [VV, VH]

module_b_harvest_detection:
  change_metric: dnbr                 # dnbr | dndmi | s1_logratio | combined
  threshold_sweep: {min: 0.05, max: 0.60, step: 0.01}
  zonal_stat: mean
  pixel_mode: centroid
  min_stand_area_ha: 0.5
  felling_types_scored: [regeneration, thinning, salvage]

module_a_stand_estimation:
  method: [aba_regression, knn_imputation]
  als:
    height_normalise: true
    cell_size_m: 16
    percentiles: [25, 50, 75, 90, 95]
    canopy_threshold_m: 2.0
    min_points_per_cell: 30
  knn:
    k_values: [1, 3, 5, 7, 10]
    distance: euclidean
    weight_power: 1.0                 # g in inverse-distance weighting
    stratify_by: soil_main_type       # mineral vs peat, as MS-NFI does
    max_geographic_distance_km: 50
  cv:
    method: spatial_block
    block_size_km: 5
    n_folds: 5
  exclude_stale_stands: true          # flagged by module B, analysed separately

module_c_beetle:
  susceptibility:
    method: logistic_regression
    predictors: [spruce_volume_share, mean_height, stand_age, site_fertility,
                 edge_exposure_m, prior_damage_distance_m, climatic_water_balance]
  stress:
    indices: [ndre, ndmi]
    baseline_years: 3
    departure_threshold_sd: 2.0
```

```yaml
# regenerative-harvest-planning/config/pipeline.yaml
aoi: config/aoi_central.yaml

module_d1_dtw_derive:
  validation_catchment_bbox_3067: [null, null, null, null]   # set in TASK 00
  dem_resolution_m: 2
  culvert_burn: true
  pit_removal: carve
  flow_algorithm: dinf
  channel_thresholds_ha: [0.5, 1.0, 4.0, 10.0]

module_d2_dtw_extend:
  weather_term:
    enabled: true
    fmi_station_id: null              # set in TASK 00
    antecedent_precip_days: [7, 14, 30]
    snowmelt_detection: snow_depth_delta
    interpolate_between_thresholds: true
  soil_term:
    enabled: true
    source: msnfi_soil_main_type
    peat_bearing_penalty: 0.5         # calibrate against korjuukelpoisuus

module_d3_rootrot:
  mandatory_period: {start: "05-01", end: "11-30"}
  mineral_soil_conifer_volume_share_min: 0.50
  peat_soil_spruce_volume_share_min: 0.50
  exemption_min_temp_c: -10.0
  exemption_lookback_days: 21
  spore_dispersal_mean_temp_c: 5.0
  urea_watercourse_setback_m: 10

module_e_plus:
  buffer_widths_m: [10, 20, 30]
  dtw_wet_threshold_m: 1.0
  retention_trees_per_ha: 30
  retention_min_dbh_cm: 15
  deadwood_trees_per_ha: 20
  biodiversity_stumps_per_ha: 10
  ccf_peatland: {soil: peat, dominant_species: spruce, drained: true,
                 fertility_min: lush}

module_f_connectivity:
  node_sources: [protected_areas, habitat_s10, ymparistotuki, old_stands]
  old_stand_age_min_years: 120
  resistance_sensitivity_runs: 20
```

`fi_forest_data/validate.py` validates these against a schema in CI. A missing or
out-of-range parameter fails the build rather than defaulting silently.

---

## Output conventions

```
outputs/
  {project}/{module}/{run_id}/
    rasters/*.tif          # COG, DEFLATE
    vectors/*.gpkg
    tables/*.csv
    figures/*.png
    report.json
    run_metadata.json
```

`run_id` is `{YYYYMMDD}_{HHMMSS}_{git_short_sha}`.

`run_metadata.json` records: config hash, git SHA, every data source with its
endpoint version and fetch date, AOI bbox, package versions.

`report.json` carries the module's analytical results — the numbers that go in the
poster and the talking points.

Figures follow the existing portfolio style (Prey Lang and Baltic posters):
matplotlib, no emojis, attribution in the caption, legend classes named in English.

---

## Acceptance criteria

A module is done when every item below exists in its output directory.

### P1 module B — harvest detection
- Precision, recall and F1 by felling type (regeneration, thinning, salvage)
- F1 by stand area class, showing where small stands fail
- Threshold sweep curve per felling type, with optimal thresholds marked
- Count and area of declared-but-not-detected, and detected-but-not-declared
- Stated minimum reliably detectable stand area and thinning intensity
- Per-stand `inventory_stale` boolean flag, written to GeoPackage, consumed by A
- AOI harvest map figure

### P1 module A — stand estimation
- RMSE, bias, relative RMSE by species and volume class, for both ABA regression
  and k-NN, side by side
- Chosen k with the tuning table behind it
- Agreement statistics between our ALS metrics and the Metsäkeskus latvusmalli,
  with a stated conclusion on what the paid 5 p data buys
- Agreement between our volume estimates and MS-NFI 2023
- Performance with and without MS-NFI features (circularity check)
- Performance on stale-label stands versus clean stands, expressed in m³/ha
- Explicit statement of which attributes are estimable and which are not
- A working demonstration: arbitrary polygon in, estimates out

### P1 module C — bark beetle
- C1: logistic regression coefficient table with confidence intervals
- C1: precision-recall curve and average precision, not accuracy
- C1: driver ranking compared against published Finnish findings
- C2: days-early distribution, detection date versus declared salvage date
- README statement of the known-hard-problem baseline, placed before results

### P2 module D — harvest windows
- Agreement statistics, our DTW versus official DTW, on the validation catchment
- Confusion matrix, our trafficability classification versus Metsäkeskus
  korjuukelpoisuus 6 classes
- Frozen-ground season length by year over the full FMI record, with trend
- Stand × date obligation matrix, and harvestable-window length per stand
- The awkward set: stands where trafficability and root rot exemption windows do
  not overlap, with count and area
- Concordance between predicted workable windows and declared harvest timing
- Before/after comparison showing what the D2 extension changes versus static DTW

### P2 module E — Metsä Group Plus
- Hectares of buffer captured by the derived stream network but missed by mapped
  hydrography
- Continuous-cover-eligible peatland area against the +30% target
- Retention and deadwood deficit per stand and in aggregate
- The Plus-versus-root-rot conflict set, with count and area
- Per-stand Plus site plan GeoPackage

### P2 module F — connectivity
- Connectivity metric maps for the baseline parameterisation
- Sensitivity sweep results across parameterisations
- The robust set: stands ranked high across all runs, separated from
  single-parameter artefacts
- README statement that this is exploratory prioritisation, not a recommendation

### Posters
One per project, A0 landscape, matching the Prey Lang and Baltic layout: title
block, main map, detail insets, study area panel, methodology panel, key findings
panel, metric chart, code and data footer with attribution.
Project 1 poster subject: module B. Project 2 poster subject: module D or E.


---

## Environment detail

Python 3.11+. One shared virtual environment at the working directory root serves
both repos during development.

Core: rasterio, geopandas, shapely, pyproj, numpy, pandas, scipy, matplotlib,
requests, pyyaml, rasterstats.
Terrain and hydrology: whitebox (WhiteboxTools) or richdem, pysheds.
Point clouds: laspy, PDAL.
Statistics: statsmodels for logistic regression. scikit-learn is used for
`NearestNeighbors` as a k-NN utility; wider use as an ML framework is a design
decision to raise first, not a default.
Optional: earthengine-api if GEE is chosen over CDSE for Sentinel-2.

Each repo gets its own Dockerfile, docker-compose.yml and GitHub Actions
workflow running flake8, config schema validation and unit tests, matching the
existing portfolio repos. Each repo also carries a minimal `pyproject.toml` so
`pip install -e . --no-deps` makes `fi_forest_data` and `src` importable from
any working directory (as SARFloodAnalysis does); runtime dependencies stay in
`requirements.txt`. Lint config lives in `.flake8` (`max-line-length = 120`).

One shared virtualenv at the working directory root serves both repos during
development:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r boreal-stand-intelligence/requirements.txt
pip install -e boreal-stand-intelligence --no-deps
```
