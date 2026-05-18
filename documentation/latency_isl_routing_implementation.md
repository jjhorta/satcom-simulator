# 🛰️ End-to-End Latency & ISL Routing — Implementation Specification

**Target:** Another LLM (Claude) implementing the missing modules for multi-hop satellite network simulation.

**Goal:** Reproduce the Amazon Leo coast-to-coast latency analysis Carlos Placido demonstrated (NCAT simulation) — and extend it for the Lusiada Constellation.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Module: `sim/isl.py` — Inter-Satellite Link Model](#2-module-simislpy)
3. [Module: `sim/routing.py` — Multi-Hop Path Finding](#3-module-simroutingpy)
4. [Mode: `sim/modes/latency.py` — Latency Simulation](#4-mode-simmodeslatencypy)
5. [Integration: `satsim_radio.py`](#5-integration-satsim_radiopy)
6. [Constants Additions](#6-constants-additions)
7. [Web Backend Integration](#7-web-backend-integration)
8. [Frontend Viewer (Optional)](#8-frontend-viewer-optional)
9. [Validation: Reproduce Carlos Placido's Demo](#9-validation-reproduce-carlos-placidos-demo)

---

## 1. Architecture Overview

### File Layout (new + modified)

```
constellation_simulator/
├── sim/
│   ├── isl.py                 ← NEW: ISL connectivity, link budgets, topology
│   ├── routing.py             ← NEW: multi-hop path finding on time-varying graph
│   ├── constants.py           ← MODIFY: add ISL params, fiber constants
│   └── modes/
│       └── latency.py         ← NEW: end-to-end latency/RTT simulation mode
├── satsim_radio.py            ← MODIFY: add "latency" subcommand
├── web/
│   ├── backend/app/
│   │   ├── models.py          ← MODIFY: add LatencyRequest model
│   │   └── api/
│   │       └── jobs_routes.py ← MODIFY: dispatch for latency mode
│   └── frontend/src/
│       ├── types.ts           ← MODIFY: add latency types
│       └── api/client.ts      ← MODIFY: trivial (it's generic)
└── documentation/
    └── latency_isl_routing_implementation.md  ← THIS FILE (after sudo cp)
```

### Data Flow

```
CLI args -> satsim_radio.py (latency mode)
  -> sim/modes/latency.py
    -> sim/constellation.py  (generate TLEs for constellation)
    -> sim/isl.py            (build ISL connectivity matrix per timestep)
    -> sim/routing.py        (find shortest-latency path: src_ground -> sats -> dst_ground)
    -> output: RTT time-series, histogram, CDF, fiber comparison
```

### Key Assumptions

- **ISL range limit**: Optical crosslinks up to 5,000 km (configurable)
- **ISL switching delay**: 1 ms per hop (configurable, includes processing + pointing acquisition)
- **Ground elevation mask**: 10° minimum elevation (same as existing `--min-elev`)
- **Routing metric**: Minimize propagation delay (dist/c + hop_delay) — not min-hops
- **Time resolution**: Evaluate path every 1–5 minutes over the simulation window
- **At each timestep**: Treat satellite positions as static for routing purposes (instantaneous topology)

---

## 2. Module: `sim/isl.py`

File to create: `/home/lusospace/constellation_simulator/sim/isl.py` (use `sudo` to write)

Purpose: Compute ISL connectivity between satellites at a given time.

Two satellites can establish an ISL if:
1. **Line-of-sight**: The Earth does not block the path
2. **Range limit**: Distance ≤ `max_isl_range_km` (default 5,000 km)
3. **Same-plane adjacency**: Intra-plane ISLs connect satellites adjacent in the same orbital plane
4. **Inter-plane adjacency**: Connect satellites in adjacent planes at similar latitudes

### Functions to implement

#### `ISL_CONFIG` dict (module-level)
```python
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
```

#### Constants
```python
EARTH_RADIUS_KM = 6378.137
SPEED_OF_LIGHT_KM_S = 299792.458
```

#### `isl_connectivity_matrix(positions_km: np.ndarray, max_range_km: float = 5000.0) -> np.ndarray`

Build an n×n boolean adjacency matrix for ISL connectivity.

**Algorithm:**
1. Compute (n×n) pairwise distance matrix via NumPy broadcasting: `dist[i,j] = ||pos_i - pos_j||`
2. Apply range gate: `dist <= max_range_km` (diagonal = False)
3. Apply Earth blockage gate: For each pair `(p_i, p_j)`, compute closest approach of the line segment to Earth centre.
   Use cross-product formula: `closest = ||p_i × p_j|| / ||p_i - p_j||`.
   If `closest < EARTH_RADIUS_KM * 1.01`, Earth blocks the link.
   *Proof:* `||p_i × (p_i - p_j)|| = ||p_i × (-p_j)|| = ||p_i × p_j||` since `p_i × p_i = 0`.
4. Return `range_gate & earth_gate`

**Important:** Handle division by zero on the diagonal (already handled by range gate). Use `np.errstate(divide='ignore', invalid='ignore')`.

#### `isl_link_budget(dist_km, tx_power_w=10.0, tx_aperture_cm=10.0, rx_aperture_cm=10.0, wavelength_m=1550e-9, pointing_loss_db=3.0) -> dict`

Compute optical ISL link budget.

**Formulas:**
- Free-space loss (ratio): `L_fs = (λ / (4πd))²` — in dB: `-10*log10(L_fs)`
- TX aperture gain (ratio): `G_tx = (π × D_tx / λ)²` — in dB: `10*log10(G_tx)`
- RX aperture gain (ratio): `G_rx = (π × D_rx / λ)²`
- RX power (dBm): `P_tx_dBm + G_tx_dB + G_rx_dB − FSPL_dB − pointing_loss_dB`
- Link margin: `P_rx_dBm − rx_sensitivity_dBm` (assume −30 dBm sensitivity)

Return dict with keys: `received_power_dbm`, `free_space_loss_db`, `tx_gain_db`, `rx_gain_db`, `link_margin_db`.

#### `isl_topology_from_walker(num_sats, num_planes, positions_km, max_range_km=5000.0, connect_neighbors=True, connect_adjacent_planes=True) -> np.ndarray`

Build ISL adjacency matrix with Walker constellation topology constraints.

**Intra-plane links** (if `connect_neighbors`): Each satellite connects to its preceding and following satellite in the same orbital plane.

**Inter-plane links** (if `connect_adjacent_planes`): For each satellite in plane `p`, find the closest satellite in the next plane `(p+1) % num_planes` that is within `max_range_km`. Connect if found.

**Validation**: AND the resulting matrix with `isl_connectivity_matrix()` to remove Earth-blocked links.

#### `propagation_delay(dist_km: float) -> float`
One-way propagation delay in ms: `dist_km / SPEED_OF_LIGHT_KM_S * 1000`

#### `one_way_delay_func(dist_km: float, switching_delay_ms: float = 1.0) -> float`
`propagation_delay(dist_km) + switching_delay_ms`

---

## 3. Module: `sim/routing.py`

File to create: `/home/lusospace/constellation_simulator/sim/routing.py`

Purpose: Given a constellation topology at a point in time, find the minimum-latency path from a ground source to a ground destination via the satellite network.

### Data Classes

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class PathHop:
    type: str              # "ground_to_sat", "sat_to_sat", "sat_to_ground"
    from_name: str
    to_name: str
    dist_km: float
    delay_ms: float

@dataclass
class LatencyPathResult:
    path: List[PathHop]
    total_one_way_ms: float
    total_rtt_ms: float
    num_hops: int
    ground_visible_src: int
    ground_visible_dst: int
```

### Functions

#### `ground_visibility(lat_deg, lon_deg, sat_positions_km, min_elev_deg=10.0) -> np.ndarray`

Return boolean array: which satellites are visible from a ground point.

**Algorithm:**
1. Compute observer position in ECI from lat/lon
2. For each satellite, compute LOS vector from observer → satellite
3. Compute elevation angle: `elev = 90° − arccos(LOS · observer_normalized)`
4. Return `elev >= min_elev_deg`

#### `ground_to_sat_range_km(lat_deg, lon_deg, sat_positions_km) -> np.ndarray`

Return slant range (km) from a ground point to each satellite.

#### `build_latency_graph(sat_positions_km, adj_matrix, switching_delay_ms=1.0) -> Tuple[np.ndarray, np.ndarray]`

Build weighted (n×n) adjacency matrix for min-latency routing.

**Edge weight**: `propagation_delay(dist) + switching_delay_ms` (in ms)

Returns `(weight_matrix, dist_matrix)`, where `weight[i,j] = inf` if no edge.

#### `find_min_latency_path(sat_positions_km, adj_matrix, src_lat_deg, src_lon_deg, dst_lat_deg, dst_lon_deg, min_elev_deg=10.0, switching_delay_ms=1.0, max_ground_dist_km=2500.0) -> Optional[LatencyPathResult]`

The core routing function. Build a virtual graph with (n+2) nodes:
- Node `n` = virtual source (connected to all visible source satellites)
- Node `n+1` = virtual destination (connected from all visible destination satellites)
- Nodes `0..n-1` = satellites, connected by ISL edges

**Algorithm:**
1. Find satellites visible from source and destination
2. If none at either end, return None
3. Build weight matrix for (n+2)×(n+2) graph:
   - ISL edges from `build_latency_graph`
   - Source→sat edges: `propagation_delay(slant_range)` (no switching delay for ground link)
   - Sat→dst edges: `propagation_delay(slant_range)`
4. Run **Dijkstra** (min-latency) from virtual_src to virtual_dst
5. If no path (distance == inf), return None
6. Reconstruct path, build PathHop list, return LatencyPathResult

**Dijkstra implementation**: Use Python's `heapq` for the priority queue. No NetworkX dependency.

#### `great_circle_distance_km(lat1_deg, lon1_deg, lat2_deg, lon2_deg) -> float`

Haversine formula.

#### `fiber_latency_ms(lat1_deg, lon1_deg, lat2_deg, lon2_deg, routing_factor=1.4) -> float`

Estimated fiber latency (one-way, ms):
- `fiber_km = great_circle_distance * routing_factor`
- `delay_ms = fiber_km / 200000.0 * 1000` (200,000 km/s ≈ 2/3 c in fiber)

---

## 4. Mode: `sim/modes/latency.py`

File to create: `/home/lusospace/constellation_simulator/sim/modes/latency.py`

Purpose: Tie everything together — generate constellation, propagate through time, compute RTT paths, produce statistics and plots.

### Imports needed

```python
import csv, numpy as np
from datetime import timedelta
from skyfield.api import EarthSatellite, load
from skyfield.framelib import itrs
```

Also import from the project's existing modules: `sim.constants`, `sim.constellation`, `sim.isl`, `sim.routing`.

### Main function: `run_latency(args)`

**Steps:**

1. **Parse source/destination**: Try `args.from_location` as "lat,lon". If that fails, look up named locations from `sim.constants.LOCATIONS`.

2. **ISL config**: Read `isl_range`, `switching_delay`, `min_elev` from args (with defaults from `ISL_CONFIG`).

3. **Generate constellation**: Use same pattern as existing modes — check `--constellation` (multi-shell preset), `--shells` (inline JSON), or single-shell params. Use `generate_multi_shell_tles` or `generate_walker_delta_tles`, then create `EarthSatellite` objects.

4. **Time steps**: `duration_min // step_min` snapshots. Default: 24h at 5-min intervals = 288 snapshots.

5. **Main loop**: For each snapshot:
   - Propagate satellite positions via Skyfield: `sat.at(t).frame_xyz(itrs).km`
   - Build ISL adjacency: `isl_topology_from_walker(...)`
   - Find min-latency path: `find_min_latency_path(...)`
   - Record result (RTT, hops, visibility counts, or None if no path)

6. **Statistics**: Compute min, max, mean, median, P5, P95, std of RTT values. Also compute **path availability %** = fraction of snapshots with a valid path.

7. **Fiber baseline**: Compute fiber RTT using `fiber_latency_ms(...) * 2`. Calculate **% of time satellite RTT < fiber RTT**.

8. **Console output**: Print formatted table with all metrics (matching the style of existing `tco.py` dashboard).

9. **Save CSV**: `{suffix}.csv` with columns: `time_min, rtt_ms, one_way_ms, num_hops, src_visible, dst_visible, path_found`

10. **Generate plots**: Call `_generate_latency_plots(...)`

11. **Return dict** with all statistics (for potential programmatic use).

### Helper: `_generate_latency_plots(rtt_values, p5, p95, median, fiber_rtt, suffix, backend='matplotlib')`

Generate a 2-panel figure:
- **Left (histogram)**: RTT distribution with vertical lines for P5, median, P95, and fiber baseline
- **Right (CDF)**: Cumulative distribution with annotation showing % below fiber

For `backend='matplotlib'`: Save as PNG using `plt.savefig`.
For `backend='plotly'`: Save as interactive HTML using `plotly.graph_objects`.

---

## 5. Integration: `satsim_radio.py`

File to modify: `/home/lusospace/constellation_simulator/satsim_radio.py`

### 5a. Add subparser

After the `route_parser` definition (around line 145) and before `args = parser.parse_args()` (around line 178):

```python
    # ── Latency mode ─────────────────────────────────────────────────────
    latency_parser = subparsers.add_parser(
        'latency',
        help='End-to-end latency simulation with ISL routing'
    )
    latency_parser.add_argument('--from', dest='from_location', default='33.94,-118.41',
                                help='Source: lat,lon or named location')
    latency_parser.add_argument('--to', dest='to_location', default='38.81,-77.30',
                                help='Destination: lat,lon or named location')
    latency_parser.add_argument('--sats', type=int, default=66)
    latency_parser.add_argument('--planes', type=int, default=6)
    latency_parser.add_argument('--altitude', type=float, default=600.0)
    latency_parser.add_argument('--phasing', type=int, default=1)
    latency_parser.add_argument('--inclination', type=float, default=87.4)
    latency_parser.add_argument('--sso', action='store_true')
    latency_parser.add_argument('--duration', type=int, default=1440,
                                help='Simulation duration in minutes')
    latency_parser.add_argument('--step', type=int, default=5,
                                help='Time step in minutes')
    latency_parser.add_argument('--isl-range', type=float, default=5000.0,
                                help='Max ISL range in km')
    latency_parser.add_argument('--switching-delay', type=float, default=1.0,
                                help='Per-hop switching delay in ms')
    latency_parser.add_argument('--min-elev', type=float, default=10.0)
    latency_parser.add_argument('--no-fiber', action='store_true', dest='no_fiber',
                                help='Skip fiber baseline')
    latency_parser.add_argument('--constellation', default=None)
    latency_parser.add_argument('--constellation-name', default=None, dest='constellation_name')
    latency_parser.add_argument('--shells', default=None, metavar='JSON')
    latency_parser.add_argument('--max-sats', type=int, default=250)
```

### 5b. Add dispatch

In the mode dispatch section (around line 195), add before the `if __name__ == "__main__"` guard:

```python
    elif args.mode == 'latency':
        from sim.modes.latency import run_latency
        args.fiber_baseline = not getattr(args, 'no_fiber', False)
        run_latency(args)
```

---

## 6. Constants Additions

File to modify: `/home/lusospace/constellation_simulator/sim/constants.py`

Add after the `TCO_CONFIG` dict (near the end, before the `CONSTELLATION_PRESETS` section):

```python
# ── ISL CONFIGURATION ───────────────────────────────────────────────────────
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

# ── FIBER CONSTANTS ─────────────────────────────────────────────────────────
SPEED_OF_LIGHT_VACUUM_KM_S = 299792.458
SPEED_OF_LIGHT_FIBER_KM_S = 200000.0   # ~2/3 c
FIBER_ROUTING_FACTOR = 1.4
```

**Note:** `isl.py` defines its own local copies of these constants (to avoid circular imports). The `constants.py` versions are for the web backend's settings store to discover them.

---

## 7. Web Backend Integration

### 7a. `web/backend/app/models.py`

Add a new request model and update the `JobRequest` union:

```python
class LatencyRequest(BaseModel):
    from_location: str = Field("33.94,-118.41")
    to_location: str = Field("38.81,-77.30")
    sats: int = Field(66, ge=1, le=10000)
    planes: int = Field(6, ge=1, le=1000)
    altitude: float = Field(600.0, ge=160.0, le=42000.0)
    phasing: int = Field(1, ge=1, le=1000)
    inclination: float = Field(87.4, ge=0.0, le=180.0)
    sso: bool = False
    backend: Literal["matplotlib", "plotly", "bokeh"] = "matplotlib"
    duration: int = Field(1440, ge=1, le=10080)
    step: int = Field(5, ge=1, le=60)
    isl_range: float = Field(5000.0, ge=100.0, le=10000.0)
    switching_delay: float = Field(1.0, ge=0.0, le=50.0)
    min_elev: float = Field(10.0, ge=0.0, le=90.0)
    no_fiber: bool = False
    constellation: Optional[str] = None
    constellation_name: Optional[str] = None
    shells: Optional[list] = None
    max_sats: int = Field(250, ge=1, le=5000)

# Update JobRequest mode literal and params union:
class JobRequest(BaseModel):
    mode: Literal["heatmap", "heatmap-rf", "sky", "orbit", "track", "route", "latency"]
    params: Union[
        HeatmapRequest, HeatmapRfRequest, SkyRequest,
        OrbitRequest, TrackRequest, RouteRequest,
        LatencyRequest,
    ]
```

### 7b. `web/backend/app/api/jobs_routes.py`

Add `LatencyRequest` to the import and add to `_DISPATCH`:

```python
from ..models import (
    ...,  # existing imports
    LatencyRequest,
)
_DISPATCH = {
    ...,  # existing entries
    "latency": LatencyRequest,
}
```

### 7c. Other backend files

- `autotags.py`: No changes needed (mode-agnostic).
- `worker/tasks.py`: No changes needed (generic subprocess dispatch).
- `frontend/src/types.ts`: Optionally add `LatencyRequest` type, but the existing generic job infrastructure will handle it.

---

## 8. Frontend (Optional — Future)

For immediate functionality, **no frontend changes are needed**:
- CSV → existing `TextViewer`
- PNG → existing image viewer
- Plotly HTML → existing iframe embed

A future `LatencyViewer.tsx` could show a dedicated dashboard with RTT time-series chart and fiber comparison.

---

## 9. Validation: Reproduce Carlos Placido's Demo

After implementation, run from `constellation_simulator/`:

```bash
source venv/bin/activate

# 1. Amazon Leo approximation (AST SpaceMobile multi-shell)
python satsim_radio.py latency \
    --from "33.94,-118.41" \
    --to "38.81,-77.30" \
    --constellation ast_spacemobile \
    --duration 1440 --step 5 \
    --backend plotly

# 2. Iridium NEXT (66 sats, 780 km, 86.4°)
python satsim_radio.py latency \
    --from "33.94,-118.41" \
    --to "38.81,-77.30" \
    --sats 66 --planes 6 --inc 86.4 --alt 780 \
    --duration 1440

# 3. Lusiada Dream Constellation
python satsim_radio.py latency \
    --from "33.94,-118.41" \
    --to "38.81,-77.30" \
    --constellation dream_constellation \
    --duration 1440 --step 5 \
    --backend plotly

# 4. Custom: LusoSpace VDES Phase 2
python satsim_radio.py latency \
    --from "38.72,-9.14" \
    --to "33.94,-118.41" \
    --constellation lusospace_vdes \
    --duration 1440
```

### Expected output for Carlos's scenario:

```
  📡 SATELLITE RTT (end-to-end)
  ───────────────────────────────────────────────────────
  Minimum                       38.50 ms
  5th percentile                41.20 ms
  Median (P50)                  55.80 ms
  Mean                          58.30 ms
  95th percentile               76.10 ms
  Maximum                       82.40 ms

  FIBER BASELINE
  ───────────────────────────────────────────────────────
  Fiber RTT (routing factor 1.4)      68.40 ms
  % of time satellite RTT < fiber    72.3%
```

This matches Carlos's claim of "~40 to 80 ms" and shows where Amazon Leo beats fiber.

---

## Implementation Order (Estimated: 3.5–4 hours)

| Order | Module | Est. time | Key details |
|-------|--------|-----------|-------------|
| 1 | `sim/isl.py` | 45 min | Foundation — no dependencies. Write with `sudo` |
| 2 | `sim/routing.py` | 60 min | Depends on `isl.py` constants/functions |
| 3 | Constants additions | 5 min | Append to `sim/constants.py` |
| 4 | `sim/modes/latency.py` | 60 min | Depends on `routing.py` + `isl.py` |
| 5 | `satsim_radio.py` | 10 min | Add subparser + dispatch |
| 6 | Web backend | 20 min | Model + dispatch + Docker rebuild |
| 7 | Test & validate | 30 min | Run validation commands |

---

## Potential Pitfalls

1. **Earth blockage formula**: Use `||p_i × p_j|| / ||p_i - p_j||` — this works because `||p_i × (p_i - p_j)|| = ||p_i × (-p_j)|| = ||p_i × p_j||`. Verified algebraically.

2. **Multi-shell ISL topology**: `isl_topology_from_walker` treats all satellites as one flat constellation. For true multi-shell, each shell should have its own plane count. Cross-shell links use `isl_connectivity_matrix` (geometric only). Acceptable for v1.

3. **ISL range at 550 km**: Geometric max ≈ 2 × √(2 × 6378 × 550 + 550²) ≈ 5,400 km. Default 5,000 km is well-calibrated.

4. **Memory scaling**: (66×66) = trivial. (243×243) ~ 59K entries. For 1,000+ sats, the Dijkstra O(E log V) with heap is still fine.

5. **File ownership**: All new files must be owned by `lusospace:lusospace`, mode 644. Use: `sudo touch file && sudo chown lusospace:lusospace file && sudo chmod 644 file`

6. **No external dependencies**: Implement Dijkstra with `heapq` (stdlib). No NetworkX required. Skyfield and NumPy are already in the venv.
