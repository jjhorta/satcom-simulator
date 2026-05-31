"""
sim/exports/geojson.py — Export simulation data as GeoJSON for QGIS.

Functions:
  - write_heatmap_geojson()  — grid of Polygon cells with availability_pct
  - write_route_geojson()    — LineString route with waypoint properties
  - write_coverage_geojson() — Points with connectivity_pct
  - write_orbit_geojson()    — Satellite positions as Points (snapshot)
"""

import json, os
import numpy as np

OUTPUT_ENCODING = "utf-8"
CRS = {"type": "name", "properties": {"name": "EPSG:4326"}}


def write_heatmap_geojson(
    lat_grid: np.ndarray,
    lon_grid: np.ndarray,
    coverage_grid: np.ndarray,
    filename: str,
    title: str = "Coverage Heatmap",
    cell_res: float = 5.0,
):
    """Write a heatmap grid as GeoJSON Polygon features.

    Each cell in the grid becomes a rectangle polygon with its
    availability percentage as a property. QGIS styles this
    beautifully with Graduated or Rule-based rendering.

    Args:
        lat_grid:   (M, N) latitude grid
        lon_grid:   (M, N) longitude grid
        coverage_grid: (M, N) availability values (0-100)
        filename:   Output .geojson path
        title:      Layer title
        cell_res:   Grid resolution in degrees
    """
    features = []
    half = cell_res / 2

    # Subsample for large grids (>10k cells) to keep file size manageable
    n_lat, n_lon = coverage_grid.shape
    step = max(1, int(np.sqrt(n_lat * n_lon / 10000)))

    for i in range(0, n_lat, step):
        for j in range(0, n_lon, step):
            lat = lat_grid[i, j]
            lon = lon_grid[i, j]
            avail = float(coverage_grid[i, j])

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [lon - half, lat - half],
                        [lon + half, lat - half],
                        [lon + half, lat + half],
                        [lon - half, lat + half],
                        [lon - half, lat - half],
                    ]],
                },
                "properties": {
                    "availability_pct": round(avail, 1),
                    "latitude": round(float(lat), 2),
                    "longitude": round(float(lon), 2),
                    "tier": (
                        "critical" if avail >= 95 else
                        "premium" if avail >= 70 else
                        "standard" if avail >= 50 else
                        "basic" if avail >= 30 else
                        "low" if avail >= 10 else
                        "dead"
                    ),
                },
            }
            features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "crs": CRS,
        "properties": {"title": title, "generated_by": "Constellation Simulator"},
        "features": features,
    }

    _write(geojson, filename)
    print(f"  💾 GeoJSON saved: {filename} ({len(features)} cells)")


def write_route_geojson(
    waypoints: list,
    filename: str,
    route_name: str = "route",
):
    """Write a route analysis as GeoJSON with LineString + Points.

    The route geometry is a LineString connecting all waypoints.
    Each waypoint also appears as a Point with its connectivity.

    Args:
        waypoints: list of dicts with keys:
            sequence, waypoint, latitude, longitude, connectivity_pct
        filename:  Output .geojson path
        route_name: Route identifier
    """
    features = []

    # LineString connecting all waypoints
    coords = [(wp["longitude"], wp["latitude"]) for wp in waypoints]
    features.append({
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coords},
        "properties": {
            "type": "route_trace",
            "route": route_name,
            "waypoints": len(waypoints),
            "avg_connectivity_pct": round(
                sum(w["connectivity_pct"] for w in waypoints) / len(waypoints), 1
            ) if waypoints else 0,
        },
    })

    # Individual waypoint Points
    for wp in waypoints:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [wp["longitude"], wp["latitude"]],
            },
            "properties": {
                "type": "waypoint",
                "sequence": wp["sequence"],
                "name": wp["waypoint"],
                "connectivity_pct": round(wp["connectivity_pct"], 1),
            },
        })

    geojson = {
        "type": "FeatureCollection",
        "crs": CRS,
        "properties": {"title": f"Route Analysis: {route_name}"},
        "features": features,
    }

    _write(geojson, filename)
    print(f"  💾 GeoJSON saved: {filename} ({len(features)} features)")


def write_coverage_geojson(
    results: list,
    filename: str,
    dataset_name: str = "coverage",
):
    """Write batch coverage analysis as GeoJSON Points.

    Args:
        results: list of dicts with keys:
            location, latitude, longitude, connectivity_pct
        filename: Output .geojson path
        dataset_name: Description
    """
    features = []
    for r in results:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [r["longitude"], r["latitude"]],
            },
            "properties": {
                "location": r["location"],
                "connectivity_pct": round(r["connectivity_pct"], 1),
                "latitude": round(r["latitude"], 4),
                "longitude": round(r["longitude"], 4),
                "tier": (
                    "critical" if r["connectivity_pct"] >= 95 else
                    "premium" if r["connectivity_pct"] >= 70 else
                    "standard" if r["connectivity_pct"] >= 50 else
                    "basic" if r["connectivity_pct"] >= 30 else
                    "low" if r["connectivity_pct"] >= 10 else
                    "dead"
                ),
            },
        })

    geojson = {
        "type": "FeatureCollection",
        "crs": CRS,
        "properties": {"title": f"Coverage Analysis: {dataset_name}"},
        "features": features,
    }

    _write(geojson, filename)
    print(f"  💾 GeoJSON saved: {filename} ({len(features)} locations)")


def _write(data: dict, filename: str):
    """Write GeoJSON to file with consistent formatting."""
    out = filename
    if not out.endswith(".geojson"):
        out = os.path.splitext(out)[0] + ".geojson"
    with open(out, "w", encoding=OUTPUT_ENCODING) as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
