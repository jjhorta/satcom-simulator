"""
Throughput and demand API routes for the web backend.

Provides REST endpoints for:
  - POST /api/sim/throughput — compute IP throughput across beams
  - POST /api/sim/demand — evaluate demand at a location
  - POST /api/sim/supply-demand — match supply to demand
  - GET  /api/sim/demand-profiles — list available demand profiles
"""

import json
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..config import Settings, get_settings
from ..auth import get_current_user

router = APIRouter(prefix="/api/sim", tags=["sim"])


@router.get("/demand-profiles")
async def get_demand_profiles():
    """List available demand profiles with descriptions."""
    try:
        from sim.demand import DEMAND_PROFILES
        return {
            "profiles": [
                {
                    "id": k,
                    "description": v["desc"],
                    "terminals_per_km2": v["terminals_per_km2"],
                    "bandwidth_per_terminal_mbps": v["bandwidth_per_terminal_mbps"],
                    "active_hours_start": v["active_hours"][0],
                    "active_hours_end": v["active_hours"][1],
                }
                for k, v in DEMAND_PROFILES.items()
            ]
        }
    except ImportError as e:
        raise HTTPException(status_code=501, detail=f"Demand engine not available: {e}")


class SimThroughputRequest(BaseModel):
    comms: str = "vdes"
    sats: int = 66
    planes: int = 6
    altitude: float = 600.0
    inclination: float = 87.4
    grid_res: float = 5.0
    min_elev: float = 10.0
    duration_min: int = 60
    step_min: int = 10


class SimThroughputResponse(BaseModel):
    total_links: int
    total_throughput_mbps: float
    mean_snr_db: float
    results_csv: str




@router.post("/throughput", response_model=SimThroughputResponse)
async def run_throughput_sim(
    body: SimThroughputRequest,
    current_user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """
    Run an IP throughput simulation and return results.
    Processes in background via RQ job queue.
    """
    try:
        from sim.throughput import compute_beam_throughput
        from sim.constants import COMMS_PAYLOADS
        from sim.constellation import generate_walker_delta_tles
        from skyfield.api import EarthSatellite, load

        payload = COMMS_PAYLOADS.get(body.comms, COMMS_PAYLOADS["vdes"])
        eirp_dbw = float(payload.get("sat_p_tx", 20) + payload.get("sat_g_tx", 3))
        bandwidth_hz = float(payload.get("bw", 50e3))
        frequency_hz = float(payload.get("dl_freq", 157e6))

        # Generate constellation
        tles = generate_walker_delta_tles(
            body.sats, body.planes, body.inclination, body.altitude
        )

        ts = load.timescale()
        satellites = []
        for name, l1, l2 in tles:
            try:
                satellites.append(EarthSatellite(l1, l2, name, ts))
            except Exception:
                pass

        if not satellites:
            raise HTTPException(status_code=400, detail="No valid satellites generated")

        # Build grid
        res = body.grid_res
        lats = np.arange(-90 + res / 2, 90, res)
        lons = np.arange(-180 + res / 2, 180, res)

        timesteps = range(0, body.duration_min, body.step_min)

        total_links = 0
        total_throughput = 0.0
        snr_values = []

        for t_min in timesteps:
            t = ts.utc(2024, 1, 1, 12, t_min, 0)
            for sat in satellites[:100]:  # limit for API performance
                geocentric = sat.at(t)
                pos = geocentric.position.km
                sat_alt = np.linalg.norm(pos) - 6378.137
                sat_lat = np.degrees(np.arcsin(pos[2] / np.linalg.norm(pos)))
                sat_lon = np.degrees(np.arctan2(pos[1], pos[0]))

                for lat in lats:
                    for lon in lons:
                        dlat = np.radians(lat - sat_lat)
                        dlon = np.radians(lon - sat_lon)
                        a = np.sin(dlat / 2)**2 + np.cos(np.radians(sat_lat)) * \
                            np.cos(np.radians(lat)) * np.sin(dlon / 2)**2
                        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
                        ground_dist = 6378.137 * c
                        slant = np.sqrt(ground_dist**2 + sat_alt**2)

                        elev = np.degrees(np.arctan2(sat_alt, ground_dist) -
                                         np.arcsin(6378.137 * np.cos(
                                             np.arctan2(sat_alt, ground_dist)) / (6378.137 + sat_alt)))
                        if elev < body.min_elev:
                            continue

                        bps, snr, _ = compute_beam_throughput(
                            eirp_dbw=eirp_dbw, bandwidth_hz=bandwidth_hz,
                            frequency_hz=frequency_hz, distance_km=slant,
                        )
                        total_links += 1
                        total_throughput += bps
                        snr_values.append(snr)

        mean_snr = float(np.mean(snr_values)) if snr_values else 0.0

        return SimThroughputResponse(
            total_links=total_links,
            total_throughput_mbps=round(total_throughput / 1e6, 2),
            mean_snr_db=round(mean_snr, 2),
            results_csv="",
        )

    except ImportError as e:
        raise HTTPException(status_code=501, detail=f"Simulation engine unavailable: {e}")


class DemandRequest(BaseModel):
    lat: float
    lon: float
    profile: str = "maritime"
    exclusion_zones: list[dict] | None = None


class DemandResponse(BaseModel):
    lat: float
    lon: float
    terminals: float
    bandwidth_per_terminal_mbps: float
    total_demand_mbps: float
    profile: str


@router.post("/demand", response_model=DemandResponse)
async def evaluate_demand(
    body: DemandRequest,
    current_user: dict = Depends(get_current_user),
):
    """Evaluate demand at a specific geographic location."""
    try:
        if body.profile == "maritime":
            from sim.demand_maritime import MaritimeDemandModel
            model = MaritimeDemandModel()
            point = model.demand_at(body.lat, body.lon)
        else:
            from sim.demand import DemandModel
            model = DemandModel(profile=body.profile)
            point = model.demand_at(body.lat, body.lon)

        demand_mbps = point.terminals * point.bandwidth_per_terminal_mbps
        return DemandResponse(
            lat=body.lat,
            lon=body.lon,
            terminals=round(point.terminals, 4),
            bandwidth_per_terminal_mbps=point.bandwidth_per_terminal_mbps,
            total_demand_mbps=round(demand_mbps, 4),
            profile=body.profile,
        )
    except ImportError as e:
        raise HTTPException(status_code=501, detail=f"Demand engine unavailable: {e}")


class SupplyDemandRequest(BaseModel):
    profile: str = "maritime"
    grid_res: float = 5.0
    fairness: str = "proportional"
    total_capacity_mbps: float = 1000.0
    region_bounds: list[float] | None = None


class SupplyDemandResponse(BaseModel):
    total_supplied_mbps: float
    total_unmet_mbps: float
    satisfaction_pct: float
    points_served: int


@router.post("/supply-demand", response_model=SupplyDemandResponse)
async def match_supply_demand(
    body: SupplyDemandRequest,
    current_user: dict = Depends(get_current_user),
):
    """Match supply to demand across a geographic grid."""
    try:
        from sim.demand import DemandModel, SupplyPoint, match_supply_demand, summarize_allocation
        from sim.demand_maritime import MaritimeDemandModel

        bounds = tuple(body.region_bounds) if body.region_bounds else (-180, -90, 180, 90)

        if body.profile == "maritime":
            demand_model = MaritimeDemandModel()
            lats = np.arange(bounds[1] + body.grid_res / 2, bounds[3], body.grid_res)
            lons = np.arange(bounds[0] + body.grid_res / 2, bounds[2], body.grid_res)
            demand = demand_model.demand_grid(lats, lons)
        else:
            demand_model = DemandModel(profile=body.profile, region_bounds=bounds)
            lats = np.arange(bounds[1] + body.grid_res / 2, bounds[3], body.grid_res)
            lons = np.arange(bounds[0] + body.grid_res / 2, bounds[2], body.grid_res)
            demand = demand_model.demand_grid(lats, lons)

        # Create uniform supply distribution
        n_points = len(demand)
        supply = []
        if n_points > 0:
            per_point = body.total_capacity_mbps / n_points
            for d in demand:
                supply.append(SupplyPoint(
                    lat=d.lat, lon=d.lon, capacity_mbps=per_point,
                ))

        results = match_supply_demand(supply, demand, body.fairness, body.total_capacity_mbps)
        summary = summarize_allocation(results)

        return SupplyDemandResponse(
            total_supplied_mbps=summary["total_supplied_mbps"],
            total_unmet_mbps=summary["total_unmet_mbps"],
            satisfaction_pct=summary["satisfaction_pct"],
            points_served=summary["points_served"],
        )

    except ImportError as e:
        raise HTTPException(status_code=501, detail=f"Engine unavailable: {e}")
