"""
Ground station class for satellite communications.
"""

import numpy as np
from typing import List, Optional
from .orbital_mechanics import (
    geodetic_to_eci,
    calculate_elevation_angle,
    calculate_distance,
)
from .satellite import Satellite


class GroundStation:
    """
    Represents a ground station for satellite communications.
    """
    
    def __init__(
        self,
        gs_id: str,
        latitude: float,
        longitude: float,
        altitude: float = 0.0,
        min_elevation: float = 10.0,
    ):
        """
        Initialize a ground station.
        
        Args:
            gs_id: Unique identifier for the ground station
            latitude: Latitude in degrees (positive = North)
            longitude: Longitude in degrees (positive = East)
            altitude: Altitude in km above sea level
            min_elevation: Minimum elevation angle for visibility in degrees
        """
        self.gs_id = gs_id
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude
        self.min_elevation = np.radians(min_elevation)
        
        # Convert to ECI position (assuming non-rotating frame for simplicity)
        self.position = geodetic_to_eci(
            np.radians(latitude),
            np.radians(longitude),
            altitude,
        )
    
    def is_visible(self, satellite: Satellite) -> bool:
        """
        Check if a satellite is visible from this ground station.
        
        Args:
            satellite: Satellite object to check
        
        Returns:
            True if satellite is above minimum elevation angle
        """
        if satellite.position is None:
            return False
        
        elevation = calculate_elevation_angle(satellite.position, self.position)
        return elevation >= self.min_elevation
    
    def get_elevation_angle(self, satellite: Satellite) -> Optional[float]:
        """
        Get the elevation angle to a satellite.
        
        Args:
            satellite: Satellite object
        
        Returns:
            Elevation angle in degrees, or None if position not available
        """
        if satellite.position is None:
            return None
        
        elevation = calculate_elevation_angle(satellite.position, self.position)
        return np.degrees(elevation)
    
    def get_distance(self, satellite: Satellite) -> Optional[float]:
        """
        Get the distance to a satellite.
        
        Args:
            satellite: Satellite object
        
        Returns:
            Distance in km, or None if position not available
        """
        if satellite.position is None:
            return None
        
        return calculate_distance(satellite.position, self.position)
    
    def get_visible_satellites(self, satellites: List[Satellite]) -> List[Satellite]:
        """
        Get a list of visible satellites from this ground station.
        
        Args:
            satellites: List of Satellite objects
        
        Returns:
            List of visible satellites
        """
        return [sat for sat in satellites if self.is_visible(sat)]
    
    def __repr__(self) -> str:
        return (
            f"GroundStation(id={self.gs_id}, "
            f"lat={self.latitude:.2f}°, lon={self.longitude:.2f}°, "
            f"min_elev={np.degrees(self.min_elevation):.1f}°)"
        )
