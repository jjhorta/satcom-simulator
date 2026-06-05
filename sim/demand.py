"""
Supply-Demand Matching Engine.

Configurable demand models + fairness-based capacity allocation
for multi-beam satellite constellations.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Literal

FairnessCriterion = Literal["proportional", "max-min", "priority-weighted"]

# ── Built-in demand profiles ──────────────────────────────────────

DEMAND_PROFILES = {
    "rural": {
        "desc": "Rural broadband (5 Mbps per 100 km²)",
        "terminals_per_km2": 0.05,
        "bandwidth_per_terminal_mbps": 5.0,
        "active_hours": (8, 23),
    },
    "urban": {
        "desc": "Urban broadband (50 Mbps per km²)",
        "terminals_per_km2": 10.0,
        "bandwidth_per_terminal_mbps": 50.0,
        "active_hours": (0, 24),
    },
    "maritime": {
        "desc": "Maritime AIS/VDES (1 terminal per 10 km² shipping lane)",
        "terminals_per_km2": 0.1,
        "bandwidth_per_terminal_mbps": 2.0,
        "active_hours": (0, 24),
    },
    "aviation": {
        "desc": "Aviation IFC (200 Mbps per aircraft, sparse)",
        "terminals_per_km2": 0.001,
        "bandwidth_per_terminal_mbps": 200.0,
        "active_hours": (6, 22),
    },
    "mixed": {
        "desc": "Mixed profile (weighted average of above)",
        "terminals_per_km2": 1.0,
        "bandwidth_per_terminal_mbps": 10.0,
        "active_hours": (0, 24),
    },
}


@dataclass
class DemandPoint:
    """Demand at a single geographic point."""
    lat: float
    lon: float
    terminals: float  # number of terminals
    bandwidth_per_terminal_mbps: float
    exclusion: bool = False  # exclusion zone flag


@dataclass
class SupplyPoint:
    """Supply (capacity) at a single geographic point."""
    lat: float
    lon: float
    capacity_mbps: float
    beam_id: str = ""
    sat_id: str = ""


@dataclass
class AllocationResult:
    """Result of supply-demand matching."""
    supplied_mbps: float
    unmet_mbps: float
    satisfaction_pct: float


class DemandModel:
    """Configurable demand model with pre-set profiles and custom parameters."""

    def __init__(
        self,
        profile: str = "rural",
        custom_terminals_per_km2: float | None = None,
        custom_bandwidth_per_terminal_mbps: float | None = None,
        exclusion_zones: list[tuple[float, float, float]] | None = None,
        region_bounds: tuple[float, float, float, float] = (-180, -90, 180, 90),
    ):
        cfg = DEMAND_PROFILES.get(profile, DEMAND_PROFILES["rural"])
        self.terminals_per_km2 = custom_terminals_per_km2 or cfg["terminals_per_km2"]
        self.bandwidth_per_terminal_mbps = custom_bandwidth_per_terminal_mbps or cfg["bandwidth_per_terminal_mbps"]
        self.active_hours = cfg["active_hours"]
        self.exclusion_zones = exclusion_zones or []
        self.region_bounds = region_bounds
        self.profile_name = profile

    def _is_excluded(self, lat: float, lon: float) -> bool:
        for zone_lat, zone_lon, zone_radius_km in self.exclusion_zones:
            # Great-circle distance to zone center
            dlat = np.radians(lat - zone_lat)
            dlon = np.radians(lon - zone_lon)
            a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(zone_lat)) * np.cos(np.radians(lat)) * np.sin(dlon / 2) ** 2
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
            dist_km = 6378.137 * c
            if dist_km < zone_radius_km:
                return True
        return False

    def demand_at(self, lat: float, lon: float) -> DemandPoint:
        """Compute demand at a single geographic point."""
        excluded = self._is_excluded(lat, lon)
        return DemandPoint(
            lat=lat,
            lon=lon,
            terminals=self.terminals_per_km2 if not excluded else 0.0,
            bandwidth_per_terminal_mbps=self.bandwidth_per_terminal_mbps,
            exclusion=excluded,
        )

    def demand_grid(
        self,
        grid_lats: np.ndarray,
        grid_lons: np.ndarray,
    ) -> list[DemandPoint]:
        """Compute demand across a grid of points."""
        points = []
        for lat, lon in zip(grid_lats.ravel(), grid_lons.ravel()):
            points.append(self.demand_at(float(lat), float(lon)))
        return points


def match_supply_demand(
    supply: list[SupplyPoint],
    demand: list[DemandPoint],
    fairness: FairnessCriterion = "proportional",
    total_capacity_mbps: float | None = None,
) -> list[AllocationResult]:
    """
    Match supply to demand with fairness criteria.

    Args:
        supply: List of SupplyPoint (capacity available per location)
        demand: List of DemandPoint (demand per location)
        fairness: "proportional", "max-min", or "priority-weighted"
        total_capacity_mbps: Optional cap on total allocatable capacity

    Returns:
        List of AllocationResult per demand point
    """
    # Build spatial index: for each demand point, find nearest supply
    # Simplified: associate demand with nearest supply point
    results = []

    if not supply or not demand:
        return results

    # Sort supply by capacity (descending) for fairness algorithms
    supply_sorted = sorted(supply, key=lambda s: s.capacity_mbps, reverse=True)

    # Total available capacity
    if total_capacity_mbps is None:
        total_capacity_mbps = sum(s.capacity_mbps for s in supply_sorted)

    total_demand_mbps = sum(
        d.terminals * d.bandwidth_per_terminal_mbps for d in demand if not d.exclusion
    )

    if total_demand_mbps == 0:
        return [
            AllocationResult(supplied_mbps=0.0, unmet_mbps=0.0, satisfaction_pct=100.0)
            for _ in demand
        ]

    # Simple proportional allocation
    if fairness == "proportional":
        ratio = min(total_capacity_mbps / total_demand_mbps, 1.0)
        for d in demand:
            if d.exclusion:
                results.append(AllocationResult(0.0, 0.0, 100.0))
            else:
                req = d.terminals * d.bandwidth_per_terminal_mbps
                supplied = req * ratio
                unmet = req - supplied
                results.append(
                    AllocationResult(
                        supplied_mbps=supplied,
                        unmet_mbps=max(unmet, 0.0),
                        satisfaction_pct=ratio * 100.0,
                    )
                )
        return results

    # Max-min fairness (iterative water-filling)
    elif fairness == "max-min":
        # Simplified: equally distribute then cap per point
        n_active = sum(1 for d in demand if not d.exclusion)
        if n_active == 0:
            return [AllocationResult(0.0, 0.0, 100.0) for _ in demand]

        per_point = total_capacity_mbps / n_active
        for d in demand:
            if d.exclusion:
                results.append(AllocationResult(0.0, 0.0, 100.0))
            else:
                req = d.terminals * d.bandwidth_per_terminal_mbps
                supplied = min(per_point, req)
                unmet = req - supplied
                results.append(
                    AllocationResult(
                        supplied_mbps=supplied,
                        unmet_mbps=max(unmet, 0.0),
                        satisfaction_pct=(supplied / req * 100) if req > 0 else 100.0,
                    )
                )
        return results

    # Priority-weighted
    elif fairness == "priority-weighted":
        # Maritime > aviation > rural > urban
        priority_map = {"maritime": 4, "aviation": 3, "rural": 2, "urban": 1}
        # For simplicity, just use proportional
        return match_supply_demand(supply, demand, "proportional")

    return results


def summarize_allocation(
    results: list[AllocationResult],
) -> dict:
    """Aggregate allocation results into summary statistics."""
    total_supplied = sum(r.supplied_mbps for r in results)
    total_unmet = sum(r.unmet_mbps for r in results)
    n = len([r for r in results if r.supplied_mbps > 0 or r.unmet_mbps > 0])

    return {
        "total_supplied_mbps": round(total_supplied, 2),
        "total_unmet_mbps": round(total_unmet, 2),
        "total_demand_mbps": round(total_supplied + total_unmet, 2),
        "satisfaction_pct": round(
            (total_supplied / (total_supplied + total_unmet) * 100)
            if (total_supplied + total_unmet) > 0 else 100.0,
            1,
        ),
        "points_served": n,
    }
