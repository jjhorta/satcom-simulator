"""
Maritime AIS/VDES demand model.

Specialised demand model for maritime satellite communications,
using AIS vessel density data to estimate VDES bandwidth demand.
"""

import numpy as np
from sim.demand import DemandModel, DemandPoint, DEMAND_PROFILES


# Default shipping density map (simplified major shipping lanes)
# Format: (lat, lon, radius_deg) — major shipping lane regions
MAJOR_SHIPPING_LANES = [
    # Atlantic
    (40.0, -50.0, 5.0),   # North Atlantic route
    (30.0, -75.0, 3.0),   # US East Coast
    (50.0, -10.0, 4.0),   # North Sea / English Channel
    (35.0, -10.0, 3.0),   # Gibraltar - Mediterranean entrance
    # Mediterranean
    (38.0, 15.0, 4.0),    # Central Med
    (32.0, 30.0, 3.0),    # Eastern Med / Suez
    # Indian Ocean
    (20.0, 65.0, 4.0),    # Arabian Sea
    (10.0, 80.0, 3.0),    # Bay of Bengal
    (-20.0, 75.0, 3.0),   # Southern Indian Ocean
    # Pacific
    (25.0, 125.0, 4.0),   # East China Sea
    (35.0, 140.0, 3.0),   # Japan coast
    (20.0, -160.0, 3.0),  # Hawaii region
    (-10.0, -150.0, 4.0), # South Pacific
    (-35.0, 175.0, 3.0),  # New Zealand / Tasman
    # Southeast Asia
    (5.0, 105.0, 4.0),    # Singapore / Malacca Strait
    (10.0, 115.0, 3.0),   # South China Sea
    # Arctic (emerging)
    (75.0, 30.0, 5.0),    # Northern Sea Route
    # South America
    (-25.0, -45.0, 3.0),  # Brazil coast
    (-35.0, -55.0, 3.0),  # Rio de la Plata
    # Africa
    (25.0, 35.0, 3.0),    # Red Sea
    (-30.0, 30.0, 3.0),   # Cape of Good Hope
    # Panama Canal
    (9.0, -79.5, 1.5),
    # Suez Canal
    (30.0, 32.5, 1.0),
    # English Channel
    (50.0, -1.0, 1.0),
    # Gibraltar Strait
    (36.0, -5.0, 1.0),
    # Malacca Strait (narrow)
    (2.5, 102.0, 0.8),
    # Bosporus
    (41.1, 29.0, 0.5),
]


class MaritimeDemandModel:
    """
    Maritime-specific demand model for AIS/VDES capacity planning.

    Uses approximate shipping lane locations with configurable density
    to estimate VDES bandwidth demand at any geographic point.
    """

    def __init__(
        self,
        base_density_multiplier: float = 1.0,
        shipping_lanes: list[tuple[float, float, float]] | None = None,
        terminals_per_ship: int = 1,
        bandwidth_per_terminal_mbps: float = 2.0,
        vdes_channel_khz: float = 50.0,
    ):
        self.base_density_multiplier = base_density_multiplier
        self.shipping_lanes = shipping_lanes or MAJOR_SHIPPING_LANES
        self.terminals_per_ship = terminals_per_ship
        self.bandwidth_per_terminal_mbps = bandwidth_per_terminal_mbps
        self.vdes_channel_khz = vdes_channel_khz

    def _lane_density(self, lat: float, lon: float) -> float:
        """Compute shipping density at (lat, lon) based on proximity to lanes."""
        density = 0.0
        for lane_lat, lane_lon, radius_deg in self.shipping_lanes:
            dlat = lat - lane_lat
            dlon = lon - lane_lon
            dist = np.sqrt(dlat ** 2 + dlon ** 2)
            if dist < radius_deg:
                # Gaussian-like falloff within radius
                contribution = np.exp(-(dist / (radius_deg * 0.3)) ** 2)
                density += contribution
        return density

    def ship_count(self, lat: float, lon: float, cell_area_km2: float = 100.0) -> float:
        """
        Estimate number of ships in a given area.

        Args:
            lat, lon: Center of area
            cell_area_km2: Area in km²

        Returns:
            Estimated ship count (float, can be fractional for small areas)
        """
        base = self._lane_density(lat, lon)
        # Open ocean background: 1 ship per 10000 km²
        background = 0.0001
        density_per_km2 = (base * 0.1 + background) * self.base_density_multiplier
        return density_per_km2 * cell_area_km2

    def demand_at(self, lat: float, lon: float, cell_area_km2: float = 100.0) -> DemandPoint:
        """
        Compute VDES bandwidth demand at a geographic point.

        Args:
            lat, lon: Geographic coordinates
            cell_area_km2: Area represented by this point (km²)

        Returns:
            DemandPoint with terminals and bandwidth
        """
        n_ships = self.ship_count(lat, lon, cell_area_km2)
        n_terminals = n_ships * self.terminals_per_ship
        return DemandPoint(
            lat=lat,
            lon=lon,
            terminals=n_terminals,
            bandwidth_per_terminal_mbps=self.bandwidth_per_terminal_mbps,
        )

    def demand_grid(self, lats: np.ndarray, lons: np.ndarray, cell_area_km2: float = 100.0) -> list[DemandPoint]:
        """Compute maritime demand across a grid."""
        points = []
        for lat, lon in zip(lats.ravel(), lons.ravel()):
            points.append(self.demand_at(float(lat), float(lon), cell_area_km2))
        return points

    def total_ships_estimate(self) -> dict:
        """
        Estimate total global ships based on shipping lane model.

        Returns:
            dict with total_ships by region
        """
        # Very rough estimate based on lane data
        lane_counts = {}
        total = 0
        for lane_lat, lane_lon, radius_deg in self.shipping_lanes:
            area_km2 = np.pi * (radius_deg * 111) ** 2
            ships = int(area_km2 * 0.05)  # ~5 ships per 100km² in lanes
            name = f"{lane_lat:.0f}N/{lane_lon:.0f}E" if lane_lat >= 0 else f"{abs(lane_lat):.0f}S/{lane_lon:.0f}E"
            lane_counts[name] = ships
            total += ships
        return {"total_ships_estimate": total, "by_lane": lane_counts}
