# boreal-stand-intelligence/src/run.py
"""Pipeline entry point.

Loads and validates config/pipeline.yaml, resolves the AOI, and runs the
requested modules (B, A, C1, C2) in order, writing outputs under
outputs/{project}/{module}/{run_id}/ where run_id is
{YYYYMMDD}_{HHMMSS}_{git_short_sha}. Each module writes rasters, vectors,
tables, figures, report.json and run_metadata.json.

No implementation yet — scaffold only.
"""
