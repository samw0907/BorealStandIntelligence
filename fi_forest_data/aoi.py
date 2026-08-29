# boreal-stand-intelligence/fi_forest_data/aoi.py
"""Area of interest.

The AOI value object used across the pipeline: a name, an EPSG:3067 bounding box,
and a few geometry helpers. Loaded from a small YAML file such as
config/aoi_southeast.yaml. Kept deliberately minimal and stable because both
projects depend on it.

Product-specific map-sheet tiling (DTW, 2 m DEM, ALS) is resolved inside the
relevant fetch function using that product's own tile index, not here, so this
object stays pure geometry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pyproj import Transformer
from shapely.geometry import box, Polygon

_TM35FIN = "EPSG:3067"


@dataclass(frozen=True)
class AOI:
    """A rectangular working extent in ETRS-TM35FIN (EPSG:3067)."""

    name: str
    bbox_3067: tuple[float, float, float, float]
    crs: str = _TM35FIN
    description: str = ""
    _tags: dict = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        minx, miny, maxx, maxy = self.bbox_3067
        if not (minx < maxx and miny < maxy):
            raise ValueError(f"AOI {self.name}: bbox is not min < max: {self.bbox_3067}")
        if self.crs != _TM35FIN:
            raise ValueError(f"AOI {self.name}: crs must be {_TM35FIN}, got {self.crs}")

    @classmethod
    def from_yaml(cls, path: str | Path) -> "AOI":
        """Load an AOI from a YAML file with keys name, bbox_3067, crs, description."""
        path = Path(path)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        try:
            bbox = tuple(float(v) for v in data["bbox_3067"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{path}: bbox_3067 must be a list of four numbers") from exc
        if len(bbox) != 4:
            raise ValueError(f"{path}: bbox_3067 must have four values, got {len(bbox)}")
        return cls(
            name=str(data.get("name") or path.stem),
            bbox_3067=bbox,  # type: ignore[arg-type]
            crs=str(data.get("crs", _TM35FIN)),
            description=str(data.get("description", "")),
        )

    def to_polygon(self) -> Polygon:
        """The AOI as a shapely rectangle in EPSG:3067."""
        return box(*self.bbox_3067)

    def bbox_wgs84(self) -> tuple[float, float, float, float]:
        """The bbox as (min_lon, min_lat, max_lon, max_lat), for STAC and FMI queries."""
        t = Transformer.from_crs(_TM35FIN, "EPSG:4326", always_xy=True)
        minx, miny, maxx, maxy = self.bbox_3067
        lon0, lat0 = t.transform(minx, miny)
        lon1, lat1 = t.transform(maxx, maxy)
        return (min(lon0, lon1), min(lat0, lat1), max(lon0, lon1), max(lat0, lat1))

    def area_km2(self) -> float:
        minx, miny, maxx, maxy = self.bbox_3067
        return (maxx - minx) * (maxy - miny) / 1e6
