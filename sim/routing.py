"""Time-static multi-hop routing across a satellite topology.

Given satellite positions and an ISL adjacency matrix at a single instant,
build a graph with two virtual ground nodes and find the minimum-latency
path from source ground point to destination ground point.

Pure stdlib (``heapq``) Dijkstra, no NetworkX dependency.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from .isl import (
    EARTH_RADIUS_KM,
    SPEED_OF_LIGHT_KM_S,
    propagation_delay,
)


# ────────────────────────────────────────────────────────────────────────────
# Data classes
# ────────────────────────────────────────────────────────────────────────────

@dataclass
class PathHop:
    type: str            # "ground_to_sat" | "sat_to_sat" | "sat_to_ground"
    from_name: str
    to_name: str
    dist_km: float
    delay_ms: float


@dataclass
class LatencyPathResult:
    path: List[PathHop] = field(default_factory=list)
    total_one_way_ms: float = 0.0
    total_rtt_ms: float = 0.0
    num_hops: int = 0
    ground_visible_src: int = 0
    ground_visible_dst: int = 0
    uplink_ms: float = 0.0
    downlink_ms: float = 0.0
    isl_ms: float = 0.0
    switching_ms: float = 0.0


# ────────────────────────────────────────────────────────────────────────────
# Ground geometry helpers
# ────────────────────────────────────────────────────────────────────────────

def _ground_eci(lat_deg: float, lon_deg: float) -> np.ndarray:
    """Return a ground observer ECEF position (km) on Earth's surface."""
    lat = math.radians(float(lat_deg))
    lon = math.radians(float(lon_deg))
    return np.array([
        EARTH_RADIUS_KM * math.cos(lat) * math.cos(lon),
        EARTH_RADIUS_KM * math.cos(lat) * math.sin(lon),
        EARTH_RADIUS_KM * math.sin(lat),
    ])


def ground_visibility(
    lat_deg: float,
    lon_deg: float,
    sat_positions_km: np.ndarray,
    min_elev_deg: float = 10.0,
) -> np.ndarray:
    """Boolean array: which satellites are visible from the ground point."""
    obs = _ground_eci(lat_deg, lon_deg)
    obs_unit = obs / np.linalg.norm(obs)
    los = np.asarray(sat_positions_km) - obs
    los_norm = np.linalg.norm(los, axis=1)
    los_unit = np.where(los_norm[:, None] > 0, los / los_norm[:, None], 0.0)
    cos_zenith = np.einsum("ij,j->i", los_unit, obs_unit)
    cos_zenith = np.clip(cos_zenith, -1.0, 1.0)
    elev_deg = 90.0 - np.degrees(np.arccos(cos_zenith))
    return elev_deg >= float(min_elev_deg)


def ground_to_sat_range_km(
    lat_deg: float,
    lon_deg: float,
    sat_positions_km: np.ndarray,
) -> np.ndarray:
    """Slant range (km) from a ground point to each satellite."""
    obs = _ground_eci(lat_deg, lon_deg)
    return np.linalg.norm(np.asarray(sat_positions_km) - obs, axis=1)


# ────────────────────────────────────────────────────────────────────────────
# Graph & Dijkstra
# ────────────────────────────────────────────────────────────────────────────

def build_latency_graph(
    sat_positions_km: np.ndarray,
    adj_matrix: np.ndarray,
    switching_delay_ms: float = 1.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """Build weighted (n×n) adjacency matrix for min-latency routing.

    Edge weight = propagation_delay(dist) + switching_delay_ms (ms).
    Non-connected entries are ``inf``.
    Returns ``(weight, dist)``.
    """
    p = np.asarray(sat_positions_km, dtype=float)
    n = p.shape[0]
    diff = p[:, None, :] - p[None, :, :]
    dist = np.linalg.norm(diff, axis=2)
    weight = np.full((n, n), np.inf)
    if n == 0:
        return weight, dist
    mask = np.asarray(adj_matrix, dtype=bool)
    weight[mask] = (dist[mask] / SPEED_OF_LIGHT_KM_S) * 1000.0 + float(switching_delay_ms)
    np.fill_diagonal(weight, np.inf)
    return weight, dist


def _dijkstra(
    n_total: int,
    edges_from: list[list[tuple[int, float]]],
    src: int,
    dst: int,
) -> tuple[float, list[int]]:
    """Return (total_weight, node_path). Inf weight if unreachable."""
    dist = [math.inf] * n_total
    prev = [-1] * n_total
    dist[src] = 0.0
    pq: list[tuple[float, int]] = [(0.0, src)]
    visited = [False] * n_total
    while pq:
        d, u = heapq.heappop(pq)
        if visited[u]:
            continue
        visited[u] = True
        if u == dst:
            break
        if d > dist[u]:
            continue
        for v, w in edges_from[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    if not math.isfinite(dist[dst]):
        return math.inf, []
    # reconstruct path
    path = [dst]
    while path[-1] != src:
        p = prev[path[-1]]
        if p == -1:
            return math.inf, []
        path.append(p)
    path.reverse()
    return dist[dst], path


def find_min_latency_path(
    sat_positions_km: np.ndarray,
    adj_matrix: np.ndarray,
    src_lat_deg: float,
    src_lon_deg: float,
    dst_lat_deg: float,
    dst_lon_deg: float,
    min_elev_deg: float = 10.0,
    switching_delay_ms: float = 1.0,
    sat_names: Optional[list[str]] = None,
) -> Optional[LatencyPathResult]:
    """Find minimum-latency multi-hop path: ground → sat → … → sat → ground.

    Returns ``None`` if no path is possible (no visible satellites at either
    side, or no connected route across the ISL mesh).
    """
    p = np.asarray(sat_positions_km, dtype=float)
    n = p.shape[0]
    if n == 0:
        return None

    src_vis = ground_visibility(src_lat_deg, src_lon_deg, p, min_elev_deg=min_elev_deg)
    dst_vis = ground_visibility(dst_lat_deg, dst_lon_deg, p, min_elev_deg=min_elev_deg)
    n_src_vis = int(src_vis.sum())
    n_dst_vis = int(dst_vis.sum())

    if n_src_vis == 0 or n_dst_vis == 0:
        return LatencyPathResult(
            ground_visible_src=n_src_vis,
            ground_visible_dst=n_dst_vis,
        )

    src_ranges = ground_to_sat_range_km(src_lat_deg, src_lon_deg, p)
    dst_ranges = ground_to_sat_range_km(dst_lat_deg, dst_lon_deg, p)

    weight, dist = build_latency_graph(
        p, adj_matrix, switching_delay_ms=switching_delay_ms
    )

    # Build adjacency list for Dijkstra: n satellite nodes + virtual src(n) + virtual dst(n+1)
    n_total = n + 2
    src_node = n
    dst_node = n + 1
    edges: list[list[tuple[int, float]]] = [[] for _ in range(n_total)]

    # ISL edges
    rows, cols = np.where(np.isfinite(weight))
    for r, c in zip(rows, cols):
        edges[int(r)].append((int(c), float(weight[r, c])))

    # Ground uplink edges (src → visible sats): only propagation (no switching delay)
    for i in np.where(src_vis)[0]:
        edges[src_node].append((int(i), propagation_delay(float(src_ranges[i]))))

    # Ground downlink edges (visible sats → dst)
    for i in np.where(dst_vis)[0]:
        edges[int(i)].append((dst_node, propagation_delay(float(dst_ranges[i]))))

    total_ms, node_path = _dijkstra(n_total, edges, src_node, dst_node)
    if not math.isfinite(total_ms) or not node_path:
        return LatencyPathResult(
            ground_visible_src=n_src_vis,
            ground_visible_dst=n_dst_vis,
        )

    # Reconstruct hops
    hops: list[PathHop] = []
    uplink_ms = downlink_ms = isl_ms = switching_ms = 0.0

    def _name(idx: int) -> str:
        if sat_names is not None and 0 <= idx < len(sat_names):
            return sat_names[idx]
        return f"sat_{idx}"

    for a, b in zip(node_path[:-1], node_path[1:]):
        if a == src_node:
            d = float(src_ranges[b])
            dly = propagation_delay(d)
            hops.append(PathHop("ground_to_sat", "SRC", _name(b), d, dly))
            uplink_ms += dly
        elif b == dst_node:
            d = float(dst_ranges[a])
            dly = propagation_delay(d)
            hops.append(PathHop("sat_to_ground", _name(a), "DST", d, dly))
            downlink_ms += dly
        else:
            d = float(dist[a, b])
            dly = float(weight[a, b])
            hops.append(PathHop("sat_to_sat", _name(a), _name(b), d, dly))
            isl_ms += dly - float(switching_delay_ms)
            switching_ms += float(switching_delay_ms)

    return LatencyPathResult(
        path=hops,
        total_one_way_ms=float(total_ms),
        total_rtt_ms=float(total_ms) * 2.0,
        num_hops=len(hops),
        ground_visible_src=n_src_vis,
        ground_visible_dst=n_dst_vis,
        uplink_ms=uplink_ms,
        downlink_ms=downlink_ms,
        isl_ms=isl_ms,
        switching_ms=switching_ms,
    )


# ────────────────────────────────────────────────────────────────────────────
# Great-circle & fiber baseline
# ────────────────────────────────────────────────────────────────────────────

def great_circle_distance_km(
    lat1_deg: float, lon1_deg: float, lat2_deg: float, lon2_deg: float
) -> float:
    """Haversine great-circle distance (km)."""
    R = EARTH_RADIUS_KM
    lat1 = math.radians(float(lat1_deg))
    lat2 = math.radians(float(lat2_deg))
    dlat = lat2 - lat1
    dlon = math.radians(float(lon2_deg) - float(lon1_deg))
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2.0 * R * math.asin(min(1.0, math.sqrt(a)))


def fiber_latency_ms(
    lat1_deg: float, lon1_deg: float,
    lat2_deg: float, lon2_deg: float,
    routing_factor: float = 1.4,
) -> float:
    """Estimated one-way fiber latency (ms)."""
    d = great_circle_distance_km(lat1_deg, lon1_deg, lat2_deg, lon2_deg) * float(routing_factor)
    return (d / 200000.0) * 1000.0
