# boreal-stand-intelligence/fi_forest_data/io.py
"""Output writing, run metadata and attribution.

Writes cloud-optimised GeoTIFFs (DEFLATE) with an embedded attribution string,
and assembles the run_metadata.json record: config hash, git SHA, every data
source with its endpoint version and fetch date, AOI bbox, package versions.
CC BY 4.0 attribution is required on all outputs derived from Metsakeskus, Luke
and NLS data.

Public interface (planned):
    write_cog(array, profile, path, attribution) -> None
    run_metadata(config, fetch_dates) -> dict

No implementation yet — scaffold only.
"""
