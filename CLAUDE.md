# CLAUDE.md — boreal-stand-intelligence

Project 1 of a two-project portfolio piece. This repo rebuilds three published
Metsa geospatial data products from open data: growing stock estimation
(Module A), harvest change detection (Module B), and bark beetle / insect damage
mapping (Module C). Batch analytical pipeline, validated against official
products and ground truth, static figures and JSON reports.

Part of a two-project portfolio piece targeting Metsa Group. Companion repo:
`regenerative-harvest-planning`.

## Hard constraints
- Machine learning is not the default approach. Methods are k-NN imputation,
  area-based regression, logistic regression, and documented operational
  methods. ML is not forbidden, but introducing it is a design decision to
  raise and agree first, not a silent substitution. See docs/.
- Do not attempt NLS 5 p laser scanning data — licensed and paid. Only the
  0.5 p product is open.
- EPSG:3067 (ETRS-TM35FIN) throughout. Reproject once at ingest, never
  mid-pipeline.
- MS-NFI nodata 32766 (forestry land without satellite cover) and 32767 (not
  forestry land or outside country) have different meanings. Do not collapse
  them.
- CC BY 4.0 attribution required on all outputs derived from Metsakeskus, Luke
  and NLS data. Include the attribution string in figure captions and JSON
  reports.
- Pin Metsakeskus endpoint versions (they are in the URL path, `/v1/`, `/v2/`).
  Record the fetch date in run metadata.
- No emojis anywhere. Comments sparingly, plus a file path comment at the top of
  each file.
- Never delete data, drop a database, force-push or rewrite history without
  stopping first and explaining the risk in detail.
- Never read, write or create .env or credentials files. Local git only.

## Method constraint, stated positively
Every method here is a documented operational method (area-based approach, k-NN
imputation), transparent statistics (logistic regression, F1 threshold sweep),
or a deterministic rule engine. If a task seems to need something else, raise it.

## Three-tier data rule
Every input is FETCH (registers and legal records), DERIVE AND BENCHMARK (an
official product exists with a published method — derive on a validation subset,
quantify agreement, then consume the official product at full AOI scale), or
DERIVE ONLY (no official product; this is where the analysis lives). State the
tier in the module docstring. Do not reprocess a full AOI where the benchmark
pattern applies.

## AOI
Project 1, southeastern Finland (Puumala - Ruokolahti - southern Savonlinna).
EPSG:3067 bbox: [553000, 6780000, 610000, 6851000] — 57 x 71 km, ~4,047 km².
Fixed. See config/aoi_southeast.yaml.

## Where things are
- `docs/PROJECT_1_BOREAL_STAND_INTELLIGENCE.md` — the plan
- `docs/METSA_GIS_RESEARCH_FINDINGS.md` — background and published methods
- `docs/DATA_SOURCES.md` — endpoints, schemas, field mappings
- `docs/REPO_SCAFFOLD.md` — module contracts, config schema, acceptance criteria
- `docs/TASK_00_DISCOVERY.md` — the discovery task that verifies DATA_SOURCES.md
- `fi_forest_data/` — data access layer (fetch, cache, reproject; no analysis)
- `src/` — analysis modules, letter-prefixed to match the project plan

## Local setup
Shared `.venv` at the working directory root. From this repo:
`pip install -r requirements.txt && pip install -e . --no-deps`. The editable
install makes `fi_forest_data` and `src` importable from anywhere. `Dockerfile`
and `docker-compose.yml` give a reproducible run; CI runs flake8, config
validation and pytest.

## Status
Scaffolding complete. **TASK 00 discovery complete (2026-08-29)** —
`docs/DATA_SOURCES.md` verified against the live services, `docs/TASK_00_FINDINGS.md`
records the deviations and open decisions. `config/pipeline.yaml` needed no changes.
Next: **Module B** (harvest detection). Then A, then C.

Open decisions to settle at the right time (TASK_00_FINDINGS.md): D1 ALS vintage
(open ALS over this AOI is 2009–2015 only) — decide before Module A. The SE AOI is
mixed pine–spruce (spruce ~28%), not spruce-dominant; no method impact.
