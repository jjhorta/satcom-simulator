"""
Satellite class for constellation simulation.
"""

import numpy as np
from typing import Optional
from .orbital_mechanics import (
    orbital_elements_to_position_velocity,
    propagate_mean_anomaly,
    mean_to_true_anomaly,
    orbital_period,
    eci_to_geodetic,
)


class Satellite:
    """
    Represents a satellite in orbit with its orbital parameters and state.
    """
    
    def __init__(
        self,
        sat_id: str,
        semi_major_axis: float,
        eccentricity: float = 0.0,
        inclination: float = 0.0,
        raan: float = 0.0,
        arg_perigee: float = 0.0,
        mean_anomaly: float = 0.0,
    ):
        """
        Initialize a satellite with Keplerian orbital elements.
        
        Args:
            sat_id: Unique identifier for the satellite
            semi_major_axis: Semi-major axis in km
            eccentricity: Orbital eccentricity (0 for circular)
            inclination: Inclination in degrees
            raan: Right Ascension of Ascending Node in degrees
            arg_perigee: Argument of perigee in degrees
            mean_anomaly: Mean anomaly in degrees
        """
        self.sat_id = sat_id
        self.semi_major_axis = semi_major_axis
        self.eccentricity = eccentricity
        
        # Convert angles from degrees to radians
        self.inclination = np.radians(inclination)
        self.raan = np.radians(raan)
        self.arg_perigee = np.radians(arg_perigee)
        self.mean_anomaly = np.radians(mean_anomaly)
        
        # Current state
        self.position: Optional[np.ndarray] = None
        self.velocity: Optional[np.ndarray] = None
        self.time: float = 0.0
        
        # Calculate initial position and velocity
        self.update_state()
    
    def update_state(self):
        """
        Update the satellite's position and velocity based on current orbital elements.
        """
        # Convert mean anomaly to true anomaly
        true_anomaly = mean_to_true_anomaly(self.mean_anomaly, self.eccentricity)
        
        # Calculate position and velocity
        self.position, self.velocity = orbital_elements_to_position_velocity(
            self.semi_major_axis,
            self.eccentricity,
            self.inclination,
            self.raan,
            self.arg_perigee,
            true_anomaly,
        )
    
    def propagate(self, dt: float):
        """
        Propagate the satellite's orbit forward in time.
        
        Args:
            dt: Time step in seconds
        """
        # Propagate mean anomaly
        self.mean_anomaly = propagate_mean_anomaly(
            self.mean_anomaly, self.semi_major_axis, dt
        )
        
        # Update state
        self.update_state()
        self.time += dt
    
    def get_geodetic_position(self) -> tuple:
        """
        Get the satellite's current position in geodetic coordinates.
        
        Returns:
            Tuple of (latitude_deg, longitude_deg, altitude_km)
        """
        if self.position is None:
            return (0.0, 0.0, 0.0)
        
        lat, lon, alt = eci_to_geodetic(self.position)
        return (np.degrees(lat), np.degrees(lon), alt)
    
    def get_orbital_period(self) -> float:
        """
        Get the orbital period of this satellite.
        
        Returns:
            Orbital period in seconds
        """
        return orbital_period(self.semi_major_axis)
    
    def __repr__(self) -> str:
        lat, lon, alt = self.get_geodetic_position()
        return (
            f"Satellite(id={self.sat_id}, "
            f"altitude={alt:.2f}km, "
            f"lat={lat:.2f}°, lon={lon:.2f}°)"
        )
