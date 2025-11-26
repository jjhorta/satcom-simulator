"""
Constellation class for managing multiple satellites.
"""

from typing import List, Dict, Optional
import numpy as np
from .satellite import Satellite
from .ground_station import GroundStation


class Constellation:
    """
    Manages a constellation of satellites.
    """
    
    def __init__(self, name: str):
        """
        Initialize a satellite constellation.
        
        Args:
            name: Name of the constellation
        """
        self.name = name
        self.satellites: List[Satellite] = []
        self.ground_stations: List[GroundStation] = []
    
    def add_satellite(self, satellite: Satellite):
        """
        Add a satellite to the constellation.
        
        Args:
            satellite: Satellite object to add
        """
        self.satellites.append(satellite)
    
    def add_ground_station(self, ground_station: GroundStation):
        """
        Add a ground station to the constellation.
        
        Args:
            ground_station: GroundStation object to add
        """
        self.ground_stations.append(ground_station)
    
    def create_walker_delta_constellation(
        self,
        total_sats: int,
        planes: int,
        phasing: int,
        altitude: float,
        inclination: float,
        prefix: str = "sat",
    ):
        """
        Create a Walker Delta constellation pattern.
        
        Walker Delta is a common satellite constellation pattern that provides
        uniform global coverage. Parameters T/P/F mean:
        - T: Total number of satellites
        - P: Number of equally spaced orbital planes
        - F: Relative phasing between satellites in adjacent planes
        
        Args:
            total_sats: Total number of satellites (T)
            planes: Number of orbital planes (P)
            phasing: Phasing parameter (F)
            altitude: Orbital altitude in km
            inclination: Orbital inclination in degrees
            prefix: Prefix for satellite IDs
        """
        from .orbital_mechanics import EARTH_RADIUS
        
        if total_sats % planes != 0:
            raise ValueError("Total satellites must be divisible by number of planes")
        
        sats_per_plane = total_sats // planes
        semi_major_axis = EARTH_RADIUS + altitude
        
        for plane in range(planes):
            # RAAN for this plane
            raan = plane * 360.0 / planes
            
            for sat_in_plane in range(sats_per_plane):
                # Mean anomaly for this satellite
                mean_anomaly = sat_in_plane * 360.0 / sats_per_plane
                
                # Add phasing
                mean_anomaly += plane * phasing * 360.0 / total_sats
                mean_anomaly = mean_anomaly % 360.0
                
                sat_id = f"{prefix}_{plane}_{sat_in_plane}"
                satellite = Satellite(
                    sat_id=sat_id,
                    semi_major_axis=semi_major_axis,
                    eccentricity=0.0,
                    inclination=inclination,
                    raan=raan,
                    arg_perigee=0.0,
                    mean_anomaly=mean_anomaly,
                )
                self.add_satellite(satellite)
    
    def propagate(self, dt: float):
        """
        Propagate all satellites in the constellation forward in time.
        
        Args:
            dt: Time step in seconds
        """
        for satellite in self.satellites:
            satellite.propagate(dt)
    
    def get_coverage_statistics(self) -> Dict[str, float]:
        """
        Calculate coverage statistics for the constellation.
        
        Returns:
            Dictionary with coverage metrics
        """
        if not self.ground_stations or not self.satellites:
            return {
                "total_satellites": len(self.satellites),
                "total_ground_stations": len(self.ground_stations),
                "stations_with_coverage": 0,
                "coverage_percentage": 0.0,
                "avg_visible_satellites": 0.0,
            }
        
        stations_with_coverage = 0
        total_visible = 0
        
        for gs in self.ground_stations:
            visible_sats = gs.get_visible_satellites(self.satellites)
            if visible_sats:
                stations_with_coverage += 1
            total_visible += len(visible_sats)
        
        coverage_percentage = (
            100.0 * stations_with_coverage / len(self.ground_stations)
        )
        avg_visible = total_visible / len(self.ground_stations)
        
        return {
            "total_satellites": len(self.satellites),
            "total_ground_stations": len(self.ground_stations),
            "stations_with_coverage": stations_with_coverage,
            "coverage_percentage": coverage_percentage,
            "avg_visible_satellites": avg_visible,
        }
    
    def get_satellite(self, sat_id: str) -> Optional[Satellite]:
        """
        Get a satellite by ID.
        
        Args:
            sat_id: Satellite ID
        
        Returns:
            Satellite object or None if not found
        """
        for sat in self.satellites:
            if sat.sat_id == sat_id:
                return sat
        return None
    
    def get_ground_station(self, gs_id: str) -> Optional[GroundStation]:
        """
        Get a ground station by ID.
        
        Args:
            gs_id: Ground station ID
        
        Returns:
            GroundStation object or None if not found
        """
        for gs in self.ground_stations:
            if gs.gs_id == gs_id:
                return gs
        return None
    
    def __repr__(self) -> str:
        return (
            f"Constellation(name={self.name}, "
            f"satellites={len(self.satellites)}, "
            f"ground_stations={len(self.ground_stations)})"
        )
