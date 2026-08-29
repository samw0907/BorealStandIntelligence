# boreal-stand-intelligence/fi_forest_data/aoi.py
"""Area of interest handling.

Defines the AOI value object used across the pipeline: name, EPSG:3067 bounding
box, and helpers to produce a polygon, to enumerate the NLS TM35FIN map-sheet
tiles the bbox touches (needed for DTW / 2 m DEM / ALS, which are mapsheet-tiled;
MS-NFI 2023 is a single national file windowed directly, per TASK 00), and to
verify that a set of named data sources covers the AOI. Loaded from
config/aoi_southeast.yaml.

Public interface (planned):
    class AOI: name, bbox_3067, crs="EPSG:3067",
        to_polygon(), mapsheet_tiles(), verify_coverage(sources)

No implementation yet — scaffold only.
"""
