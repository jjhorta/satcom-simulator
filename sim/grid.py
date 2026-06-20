"""
H3 hexagonal grid integration and geospatial shape operations.

Provides grid generation in both lat/lon (default) and H3 hexagonal formats,
plus custom shape tools for defining analysis regions.
"""

import numpy as np
from typing import Literal

GridMode = Literal["latlon", "h3"]

try:
    import h3
    H3_AVAILABLE = True
except ImportError:
    H3_AVAILABLE = False

try:
    from shapely.geometry import Point, Polygon as ShapelyPolygon, shape as shapely_shape
    from shapely.prepared import prep
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False


def generate_grid(
    grid_mode: GridMode = "latlon",
    resolution: float | int = 5.0,
    bounds: tuple[float, float, float, float] = (-180, -90, 180, 90),
    h3_res: int = 4,
) -> list[dict]:
    """
    Generate a grid of points in lat/lon or H3 hexagonal format.

    Args:
        grid_mode: 'latlon' for rectangular grid, 'h3' for hexagonal grid
        resolution: lat/lon grid resolution in degrees (used only for latlon)
        bounds: (min_lon, min_lat, max_lon, max_lat)
        h3_res: H3 resolution (0-8, where 4≈390 km² per cell)

    Returns:
        List of dicts with keys: 'lat', 'lon' (centroid), 'cell_id' (h3 only),
                                 'vertices' (h3 only)
    """
    if grid_mode == "latlon":
        return _latlon_grid(resolution, bounds)
    elif grid_mode == "h3":
        if not H3_AVAILABLE:
            raise ImportError("h3 package not installed. Run: pip install h3")
        return _h3_grid(h3_res, bounds)
    else:
        raise ValueError(f"Unknown grid mode: {grid_mode}")


def _latlon_grid(
    resolution: float,
    bounds: tuple[float, float, float, float],
) -> list[dict]:
    """Generate rectangular lat/lon grid."""
    min_lon, min_lat, max_lon, max_lat = bounds
    lats = np.arange(min_lat + resolution / 2, max_lat, resolution)
    lons = np.arange(min_lon + resolution / 2, max_lon, resolution)
    points = []
    for lat in lats:
        for lon in lons:
            points.append({"lat": round(float(lat), 4), "lon": round(float(lon), 4)})
    return points


def _h3_grid(
    resolution: int,
    bounds: tuple[float, float, float, float],
) -> list[dict]:
    """Generate H3 hexagonal grid covering a bounding box."""
    min_lon, min_lat, max_lon, max_lat = bounds
    # Get all H3 cells at the given resolution that intersect the bounding box
    cells = h3.geo_to_cells({
        "type": "Polygon",
        "coordinates": [[
            [min_lon, min_lat],
            [max_lon, min_lat],
            [max_lon, max_lat],
            [min_lon, max_lat],
            [min_lon, min_lat],
        ]],
    }, res=resolution)
    points = []
    for cell in sorted(cells):
        centroid = h3.cell_to_latlng(cell)
        vertices = h3.cell_to_boundary(cell)
        points.append({
            "cell_id": cell,
            "lat": round(float(centroid[0]), 6),
            "lon": round(float(centroid[1]), 6),
            "vertices": [{"lat": float(v[0]), "lon": float(v[1])} for v in vertices],
        })
    return points


def h3_to_geojson(
    cells: list[dict],
    properties_key: str | None = None,
    properties_values: list | None = None,
) -> dict:
    """
    Convert H3 grid cells to a GeoJSON FeatureCollection.

    Args:
        cells: List of grid cells as returned by _h3_grid
        properties_key: Optional property name (e.g. 'value')
        properties_values: Optional list of values (same length as cells)

    Returns:
        GeoJSON dict
    """
    features = []
    for i, cell in enumerate(cells):
        coords = [[v["lon"], v["lat"]] for v in cell["vertices"]]
        # Close the ring
        coords.append(coords[0])
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords],
            },
            "properties": {
                "cell_id": cell["cell_id"],
                "lat": cell["lat"],
                "lon": cell["lon"],
            },
        }
        if properties_key and properties_values:
            feature["properties"][properties_key] = properties_values[i]
        features.append(feature)

    return {"type": "FeatureCollection", "features": features}


def latlon_to_geojson(
    points: list[dict],
    properties_key: str | None = None,
    properties_values: list | None = None,
) -> dict:
    """
    Convert lat/lon grid points to a GeoJSON FeatureCollection.

    Args:
        points: List of dicts with 'lat', 'lon'
        properties_key: Optional property name
        properties_values: Optional list of values (same length as points)

    Returns:
        GeoJSON dict
    """
    features = []
    for i, pt in enumerate(points):
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [pt["lon"], pt["lat"]],
            },
            "properties": {},
        }
        if properties_key and properties_values:
            feature["properties"][properties_key] = properties_values[i]
        features.append(feature)

    return {"type": "FeatureCollection", "features": features}


class ShapeTool:
    """
    Custom geographical region definition and analysis boundaries.
    """

    def __init__(self):
        self.shapes: list[dict] = []

    def add_polygon(self, name: str, vertices: list[tuple[float, float]]) -> None:
        """Add a polygon shape defined by (lat, lon) vertices."""
        self.shapes.append({
            "type": "Polygon",
            "name": name,
            "vertices": [{"lat": float(v[0]), "lon": float(v[1])} for v in vertices],
        })

    def add_circle(self, name: str, center_lat: float, center_lon: float, radius_km: float, segments: int = 36) -> None:
        """Add a circular shape with given radius."""
        import math
        vertices = []
        for i in range(segments):
            bearing = 2 * math.pi * i / segments
            # Approximate destination point from center + radius + bearing
            lat1 = math.radians(center_lat)
            lon1 = math.radians(center_lon)
            angular_radius = radius_km / 6378.137
            lat2 = math.asin(math.sin(lat1) * math.cos(angular_radius) +
                             math.cos(lat1) * math.sin(angular_radius) * math.cos(bearing))
            lon2 = lon1 + math.atan2(math.sin(bearing) * math.sin(angular_radius) * math.cos(lat1),
                                     math.cos(angular_radius) - math.sin(lat1) * math.sin(lat2))
            vertices.append((math.degrees(lat2), math.degrees(lon2)))
        self.shapes.append({
            "type": "Circle",
            "name": name,
            "center": {"lat": center_lat, "lon": center_lon},
            "radius_km": radius_km,
            "vertices": [{"lat": float(v[0]), "lon": float(v[1])} for v in vertices],
        })

    def add_corridor(self, name: str, waypoints: list[tuple[float, float]], width_km: float) -> None:
        """Add a corridor shape along waypoints with given width."""
        self.shapes.append({
            "type": "Corridor",
            "name": name,
            "waypoints": [{"lat": float(w[0]), "lon": float(w[1])} for w in waypoints],
            "width_km": width_km,
        })

    def shapes_to_geojson(self) -> dict:
        """Export all shapes as GeoJSON FeatureCollection."""
        features = []
        for shape in self.shapes:
            if shape["type"] == "Polygon":
                coords = [[(v["lon"], v["lat"]) for v in shape["vertices"]]]
                coords[0].append(coords[0][0])
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": coords},
                    "properties": {"name": shape["name"], "type": "Polygon"},
                })
            elif shape["type"] == "Circle":
                coords = [[(v["lon"], v["lat"]) for v in shape["vertices"]]]
                coords[0].append(coords[0][0])
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": coords},
                    "properties": {
                        "name": shape["name"],
                        "type": "Circle",
                        "center_lat": shape["center"]["lat"],
                        "center_lon": shape["center"]["lon"],
                        "radius_km": shape["radius_km"],
                    },
                })
            elif shape["type"] == "Corridor":
                coords = [[(w["lon"], w["lat"]) for w in shape["waypoints"]]]
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": coords},
                    "properties": {
                        "name": shape["name"],
                        "type": "Corridor",
                        "width_km": shape["width_km"],
                    },
                })
        return {"type": "FeatureCollection", "features": features}

    def to_dict(self) -> list[dict]:
        """Export shapes as serializable list of dicts."""
        return self.shapes

    @classmethod
    def from_dict(cls, shapes: list[dict]) -> "ShapeTool":
        tool = cls()
        tool.shapes = shapes
        return tool


# ── Shape filtering ───────────────────────────────────────────────

def load_shape_geojson(path: str) -> dict | None:
    """Load a GeoJSON FeatureCollection or single Feature from file."""
    import json
    try:
        with open(path) as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"  Could not load shape {path}: {e}")
        return None


def filter_grid_by_shape(
    grid_points: list[dict],
    shape_geojson: dict,
    invert: bool = False,
) -> list[dict]:
    """
    Filter grid points to only those INSIDE (or outside) a GeoJSON shape.

    Args:
        grid_points: List of dicts with 'lat', 'lon'
        shape_geojson: GeoJSON FeatureCollection or Feature
        invert: If True, return points OUTSIDE the shape

    Returns:
        Filtered list of grid points
    """
    if not SHAPELY_AVAILABLE:
        print("  WARNING: shapely not installed. Using full grid.")
        return grid_points

    try:
        # Normalise to list of features
        if shape_geojson.get("type") == "FeatureCollection":
            features = shape_geojson["features"]
        elif shape_geojson.get("type") == "Feature":
            features = [shape_geojson]
        else:
            print(f"  WARNING: Unknown GeoJSON type: {shape_geojson.get('type')}")
            return grid_points

        # Build a prepared multipolygon from all features
        polygons = []
        for feat in features:
            try:
                geom = shapely_shape(feat.get("geometry", {}))
                if geom.geom_type in ("Polygon", "MultiPolygon"):
                    polygons.append(geom)
            except Exception:
                continue

        if not polygons:
            print("  WARNING: No valid Polygon geometries found in shape")
            return grid_points

        # Union all polygons
        if len(polygons) == 1:
            boundary = polygons[0]
        else:
            from shapely.ops import unary_union
            boundary = unary_union(polygons)

        prepared = prep(boundary)
        filtered = []
        for pt in grid_points:
            point = Point(pt["lon"], pt["lat"])
            inside = prepared.contains(point)
            if invert:
                inside = not inside
            if inside:
                filtered.append(pt)

        print(f"  Shape filter: {len(grid_points)} -> {len(filtered)} points "
              f"({'inside' if not invert else 'outside'} shape)")
        return filtered

    except Exception as e:
        print(f"  WARNING: Shape filtering failed: {e}. Using full grid.")
        return grid_points
