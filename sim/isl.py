"""Inter-Satellite Link (ISL) connectivity, topology and link budget helpers.

Designed for the latency / routing mode. Kept dependency-light (NumPy only)
to avoid circular imports with ``sim.constants``.
"""

from __future__ import annotations

import numpy as np

# ── Local physical constants (avoid circular imports) ──────────────────────
EARTH_RADIUS_KM = 6378.137
SPEED_OF_LIGHT_KM_S = 299792.458

# Default ISL configuration (mirrors sim.constants.ISL_CONFIG).
ISL_CONFIG = {
    "type": "optical",
    "max_range_km": 5000.0,
    "switching_delay_ms": 1.0,
    "wavelength_nm": 1550,
    "tx_power_w": 10.0,
    "aperture_tx_cm": 10.0,
    "aperture_rx_cm": 10.0,
    "pointing_loss_db": 3.0,
}


# ────────────────────────────────────────────────────────────────────────────
# Geometry
# ────────────────────────────────────────────────────────────────────────────

def isl_connectivity_matrix(positions_km: np.ndarray, max_range_km: float = 5000.0) -> np.ndarray:
    """Return an n×n boolean adjacency matrix for ISL connectivity.

    A pair (i, j) is connected if:
      - distance ≤ ``max_range_km``
      - Earth does not block the line segment between the two satellites.

    The Earth-blockage test uses the closest approach of the line segment to
    the Earth centre::

        d_closest = ||p_i × p_j|| / ||p_i - p_j||

    which is valid because ``p_i × (p_i - p_j) = -p_i × p_j``.

    Parameters
    ----------
    positions_km : (n, 3) array of ECI/ITRS positions in km.
    max_range_km : maximum geometric range to consider.

    Returns
    -------
    (n, n) bool array (diagonal = False).
    """
    p = np.asarray(positions_km, dtype=float)
    n = p.shape[0]
    if n == 0:
        return np.zeros((0, 0), dtype=bool)

    # Pairwise distance: ||p_i - p_j||
    diff = p[:, None, :] - p[None, :, :]
    dist = np.linalg.norm(diff, axis=2)

    # Range gate
    range_gate = (dist <= max_range_km) & (dist > 0.0)

    # Earth blockage gate
    # cross[i, j] = p_i × p_j  → norm of cross product
    cross = np.cross(p[:, None, :], p[None, :, :])
    cross_norm = np.linalg.norm(cross, axis=2)
    with np.errstate(divide="ignore", invalid="ignore"):
        closest = np.where(dist > 0.0, cross_norm / dist, np.inf)
    earth_gate = closest >= (EARTH_RADIUS_KM * 1.01)

    adj = range_gate & earth_gate
    np.fill_diagonal(adj, False)
    return adj


def isl_topology_from_walker(
    num_sats: int,
    num_planes: int,
    positions_km: np.ndarray,
    max_range_km: float = 5000.0,
    connect_neighbors: bool = True,
    connect_adjacent_planes: bool = True,
) -> np.ndarray:
    """Build ISL adjacency with Walker-Delta topology constraints.

    - Intra-plane: each sat connects to the previous and next sat in its plane.
    - Inter-plane: each sat connects to the closest sat in the next plane
      (mod ``num_planes``) within ``max_range_km``.

    The result is AND-ed with :func:`isl_connectivity_matrix` to drop links
    blocked by Earth or out of range.
    """
    p = np.asarray(positions_km, dtype=float)
    n = p.shape[0]
    if n == 0:
        return np.zeros((0, 0), dtype=bool)

    adj = np.zeros((n, n), dtype=bool)

    # Walker numbering assumption: satellites are interleaved per plane
    # (sat index k → plane = k % num_planes, slot = k // num_planes).
    # This matches ``generate_walker_delta_tles`` in sim/constellation.py.
    sats_per_plane = max(1, num_sats // max(1, num_planes))

    # Build plane → list-of-indices map for the actual n we have
    planes: list[list[int]] = [[] for _ in range(num_planes)]
    for k in range(n):
        plane_idx = k % num_planes
        planes[plane_idx].append(k)

    # Intra-plane neighbours (ring within plane)
    if connect_neighbors:
        for plane in planes:
            if len(plane) < 2:
                continue
            m = len(plane)
            for i in range(m):
                a = plane[i]
                b = plane[(i + 1) % m]
                adj[a, b] = True
                adj[b, a] = True

    # Inter-plane neighbours (closest sat in next plane, within range)
    if connect_adjacent_planes and num_planes > 1:
        for pi in range(num_planes):
            pj = (pi + 1) % num_planes
            if not planes[pi] or not planes[pj]:
                continue
            idx_i = np.asarray(planes[pi])
            idx_j = np.asarray(planes[pj])
            sub = np.linalg.norm(p[idx_i][:, None, :] - p[idx_j][None, :, :], axis=2)
            sub = np.where(sub <= max_range_km, sub, np.inf)
            # closest in plane j for each i (skip if all inf)
            best = np.argmin(sub, axis=1)
            best_dist = sub[np.arange(len(idx_i)), best]
            for k, jk in enumerate(best):
                if np.isfinite(best_dist[k]):
                    a = idx_i[k]
                    b = idx_j[jk]
                    adj[a, b] = True
                    adj[b, a] = True

    # Validate against geometric/Earth blockage gate
    geom = isl_connectivity_matrix(p, max_range_km=max_range_km)
    return adj & geom


# ────────────────────────────────────────────────────────────────────────────
# Delays & link budget
# ────────────────────────────────────────────────────────────────────────────

def propagation_delay(dist_km: float) -> float:
    """One-way propagation delay in milliseconds."""
    return (float(dist_km) / SPEED_OF_LIGHT_KM_S) * 1000.0


def one_way_delay(dist_km: float, switching_delay_ms: float = 1.0) -> float:
    """Propagation + per-hop switching delay (ms)."""
    return propagation_delay(dist_km) + float(switching_delay_ms)


# Backwards-compat alias used in the spec
one_way_delay_func = one_way_delay


def isl_link_budget(
    dist_km: float,
    tx_power_w: float = 10.0,
    tx_aperture_cm: float = 10.0,
    rx_aperture_cm: float = 10.0,
    wavelength_m: float = 1550e-9,
    pointing_loss_db: float = 3.0,
    rx_sensitivity_dbm: float = -30.0,
) -> dict:
    """Optical ISL link budget for diagnostics.

    Returns a dict with FSPL, gains, received power and link margin in dB/dBm.
    """
    d_m = max(float(dist_km), 1.0) * 1000.0
    lam = float(wavelength_m)
    d_tx = float(tx_aperture_cm) / 100.0
    d_rx = float(rx_aperture_cm) / 100.0

    fspl_ratio = (lam / (4.0 * np.pi * d_m)) ** 2
    g_tx_ratio = (np.pi * d_tx / lam) ** 2
    g_rx_ratio = (np.pi * d_rx / lam) ** 2

    fspl_db = -10.0 * np.log10(fspl_ratio)
    g_tx_db = 10.0 * np.log10(g_tx_ratio)
    g_rx_db = 10.0 * np.log10(g_rx_ratio)

    p_tx_dbm = 10.0 * np.log10(max(float(tx_power_w), 1e-12) * 1000.0)
    p_rx_dbm = p_tx_dbm + g_tx_db + g_rx_db - fspl_db - float(pointing_loss_db)

    return {
        "received_power_dbm": float(p_rx_dbm),
        "free_space_loss_db": float(fspl_db),
        "tx_gain_db": float(g_tx_db),
        "rx_gain_db": float(g_rx_db),
        "link_margin_db": float(p_rx_dbm - float(rx_sensitivity_dbm)),
    }
