# boreal-stand-intelligence/fi_forest_data/validate.py
"""Configuration schema validation.

Validates config/pipeline.yaml and the referenced AOI file against a schema.
A missing or out-of-range parameter fails the build rather than defaulting
silently. Run in CI and importable as a module; also runnable as
`python -m fi_forest_data.validate config/pipeline.yaml`.

No implementation yet — scaffold only.
"""
