# boreal-stand-intelligence/fi_forest_data/aoi.py
"""Area of interest handling.

Defines the AOI value object used across the pipeline: name, EPSG:3067 bounding
box, and helpers to produce a polygon, to enumerate the UTM200 map sheets the
bbox touches (for MS-NFI sheet selection), and to verify that a set of named
data sources covers the AOI. Loaded from config/aoi_southeast.yaml.

Public interface (planned):
    class AOI: name, bbox_3067, crs="EPSG:3067",
        to_polygon(), utm200_sheets(), verify_coverage(sources)

No implementation yet — scaffold only.
"""
