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


# ────────────────────────────────────────────────────────────────────────────
# Dual-hop (feeder-link) helpers
# ────────────────────────────────────────────────────────────────────────────

@dataclass
class FeederLinkResult:
    """Result of a feeder-link visibility check."""
    gateway_id: str
    gateway_name: str
    gateway_lat: float
    gateway_lon: float
    sat_idx: int
    sat_name: str
    slant_range_km: float
    propagation_delay_ms: float
    elevation_deg: float


@dataclass
class DualHopResult:
    """End-to-end dual-hop latency result."""
    forward_path: list[PathHop]
    reverse_path: list[PathHop]
    total_one_way_ms: float
    total_rtt_ms: float
    feeder_gateway: str = ""
    feeder_delay_ms: float = 0.0
    user_uplink_ms: float = 0.0
    user_downlink_ms: float = 0.0
    isl_ms: float = 0.0
    switching_ms: float = 0.0
    path_found: bool = False


def find_feeder_link(
    sat_positions_km: np.ndarray,
    sat_idx: int,
    gateways: list[tuple[str, str, float, float]],  # (id, name, lat, lon)
    min_elev_deg: float = 5.0,
) -> Optional[FeederLinkResult]:
    """Find the best (lowest slant range) visible gateway for a satellite."""
    sat_pos = np.asarray(sat_positions_km[sat_idx])
    best_gw = None
    best_range = float("inf")

    for gw_id, gw_name, gw_lat, gw_lon in gateways:
        # Check satellite visibility from gateway
        obs = _ground_eci(gw_lat, gw_lon)
        los = sat_pos - obs
        los_dist = float(np.linalg.norm(los))
        obs_unit = obs / np.linalg.norm(obs)
        los_unit = los / los_dist
        cos_zenith = float(np.dot(los_unit, obs_unit))
        elev_deg = 90.0 - math.degrees(math.acos(max(-1.0, min(1.0, cos_zenith))))

        if elev_deg < min_elev_deg:
            continue

        if los_dist < best_range:
            best_range = los_dist
            delay = propagation_delay(los_dist)
            best_gw = FeederLinkResult(
                gateway_id=gw_id,
                gateway_name=gw_name,
                gateway_lat=gw_lat,
                gateway_lon=gw_lon,
                sat_idx=sat_idx,
                sat_name="",
                slant_range_km=los_dist,
                propagation_delay_ms=delay,
                elevation_deg=elev_deg,
            )

    return best_gw


def compute_dual_hop_latency(
    sat_positions_km: np.ndarray,
    adj_matrix: np.ndarray,
    src_lat_deg: float,
    src_lon_deg: float,
    dst_lat_deg: float,
    dst_lon_deg: float,
    gateways: list[tuple[str, str, float, float]],
    min_elev_deg: float = 10.0,
    feeder_min_elev_deg: float = 5.0,
    switching_delay_ms: float = 1.0,
    sat_names: Optional[list[str]] = None,
    architecture: str = "regenerative-isl",
) -> DualHopResult:
    """
    Compute end-to-end dual-hop latency.

    Path:
       user_src -> sat -> [ISL hops] -> sat -> gateway (forward)
       gateway -> sat -> [ISL hops] -> sat -> user_dst (reverse)

    Returns DualHopResult with forward + reverse path details.
    """
    p = np.asarray(sat_positions_km, dtype=float)
    n = p.shape[0]
    if n == 0 or not gateways:
        return DualHopResult(forward_path=[], reverse_path=[], total_one_way_ms=0.0, total_rtt_ms=0.0)

    # 1. Find which satellite serves the user (closest visible)
    src_vis = ground_visibility(src_lat_deg, src_lon_deg, p, min_elev_deg=min_elev_deg)
    if not src_vis.any():
        return DualHopResult(forward_path=[], reverse_path=[], total_one_way_ms=0.0, total_rtt_ms=0.0)

    src_ranges = ground_to_sat_range_km(src_lat_deg, src_lon_deg, p)
    best_src_sat = int(np.argmin(np.where(src_vis, src_ranges, np.inf)))

    # 2. Find best gateway visible from that satellite
    feeder = find_feeder_link(p, best_src_sat, gateways, min_elev_deg=feeder_min_elev_deg)

    if feeder is None:
        return DualHopResult(forward_path=[], reverse_path=[], total_one_way_ms=0.0, total_rtt_ms=0.0)

    # 3. Build graph for ISL routing
    weight, dist = build_latency_graph(p, adj_matrix, switching_delay_ms=switching_delay_ms)

    # 4a. Forward path: user_src -> sat -> gateway (via ISL to best_src_sat, then feeder down)
    fwd_uplink = propagation_delay(float(src_ranges[best_src_sat]))
    fwd_feeder = feeder.propagation_delay_ms

    forward_hops = [
        PathHop("ground_to_sat", "USER-SRC", sat_names[best_src_sat] if sat_names else f"sat_{best_src_sat}",
                float(src_ranges[best_src_sat]), fwd_uplink),
        PathHop("sat_to_gateway", sat_names[best_src_sat] if sat_names else f"sat_{best_src_sat}",
                feeder.gateway_name, feeder.slant_range_km, fwd_feeder),
    ]

    # 4b. Reverse path: gateway -> sat -> user_dst
    dst_vis = ground_visibility(dst_lat_deg, dst_lon_deg, p, min_elev_deg=min_elev_deg)
    if not dst_vis.any():
        return DualHopResult(
            forward_path=forward_hops, reverse_path=[],
            total_one_way_ms=fwd_uplink + fwd_feeder,
            total_rtt_ms=(fwd_uplink + fwd_feeder) * 2,
            feeder_gateway=feeder.gateway_name, feeder_delay_ms=fwd_feeder,
            user_uplink_ms=fwd_uplink, path_found=True,
        )

    # For reverse path: gateway is at feeder.gateway_lat, feeder.gateway_lon
    # Find satellite visible from gateway (best_src_sat or nearby)
    gw_vis = ground_visibility(feeder.gateway_lat, feeder.gateway_lon, p, min_elev_deg=feeder_min_elev_deg)
    if not gw_vis.any():
        return DualHopResult(forward_path=forward_hops, reverse_path=[], total_one_way_ms=fwd_uplink + fwd_feeder,
                             total_rtt_ms=(fwd_uplink + fwd_feeder) * 2,
                             feeder_gateway=feeder.gateway_name, feeder_delay_ms=fwd_feeder,
                             user_uplink_ms=fwd_uplink, path_found=True)

    # Use Dijkstra to find best path from gateway's feeder sat to user destination
    n_total = n + 2
    gw_node = n
    dst_node = n + 1
    edges: list[list[tuple[int, float]]] = [[] for _ in range(n_total)]

    rows, cols = np.where(np.isfinite(weight))
    for r, c in zip(rows, cols):
        edges[int(r)].append((int(c), float(weight[r, c])))

    # Gateway uplink to visible sats (feeder uplink)
    dst_ranges = ground_to_sat_range_km(dst_lat_deg, dst_lon_deg, p)
    for i in np.where(gw_vis)[0]:
        gw_to_sat_range = float(np.linalg.norm(p[i] - _ground_eci(feeder.gateway_lat, feeder.gateway_lon)))
        edges[gw_node].append((int(i), propagation_delay(gw_to_sat_range)))

    # Downlink to user destination
    for i in np.where(dst_vis)[0]:
        edges[int(i)].append((dst_node, propagation_delay(float(dst_ranges[i]))))

    rev_total_ms, rev_path_nodes = _dijkstra(n_total, edges, gw_node, dst_node)

    if math.isfinite(rev_total_ms) and rev_path_nodes:
        reverse_hops: list[PathHop] = []
        rv_uplink = rv_downlink = rv_isl = rv_switching = 0.0

        for a, b in zip(rev_path_nodes[:-1], rev_path_nodes[1:]):
            if a == gw_node:
                d = float(np.linalg.norm(p[b] - _ground_eci(feeder.gateway_lat, feeder.gateway_lon)))
                dly = propagation_delay(d)
                reverse_hops.append(PathHop("gateway_to_sat", feeder.gateway_name,
                                            sat_names[b] if sat_names else f"sat_{b}", d, dly))
                rv_uplink += dly
            elif b == dst_node:
                d = float(dst_ranges[a])
                dly = propagation_delay(d)
                reverse_hops.append(PathHop("sat_to_ground", sat_names[a] if sat_names else f"sat_{a}",
                                            "USER-DST", d, dly))
                rv_downlink += dly
            else:
                d = float(dist[a, b])
                dly = float(weight[a, b])
                reverse_hops.append(PathHop("sat_to_sat", sat_names[a] if sat_names else f"sat_{a}",
                                            sat_names[b] if sat_names else f"sat_{b}", d, dly))
                rv_isl += dly - switching_delay_ms
                rv_switching += switching_delay_ms

        total_fwd = fwd_uplink + fwd_feeder
        total_rev = rv_uplink + rv_downlink + rv_isl + rv_switching

        return DualHopResult(
            forward_path=forward_hops,
            reverse_path=reverse_hops,
            total_one_way_ms=total_fwd + total_rev,
            total_rtt_ms=(total_fwd + total_rev) * 2,
            feeder_gateway=feeder.gateway_name,
            feeder_delay_ms=fwd_feeder,
            user_uplink_ms=fwd_uplink,
            user_downlink_ms=rv_downlink,
            isl_ms=rv_isl,
            switching_ms=rv_switching,
            path_found=True,
        )

    return DualHopResult(forward_path=forward_hops, reverse_path=[], total_one_way_ms=fwd_uplink + fwd_feeder,
                         total_rtt_ms=(fwd_uplink + fwd_feeder) * 2,
                         feeder_gateway=feeder.gateway_name, feeder_delay_ms=fwd_feeder,
                         user_uplink_ms=fwd_uplink, path_found=True)
