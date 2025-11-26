"""
Tests for Satellite class.
"""

import pytest
import numpy as np
from satcom import Satellite
from satcom.orbital_mechanics import EARTH_RADIUS


def test_satellite_creation():
    """Test satellite creation with basic parameters."""
    sat = Satellite(
        sat_id="test_sat",
        semi_major_axis=EARTH_RADIUS + 550.0,
        eccentricity=0.0,
        inclination=53.0,
        raan=0.0,
        arg_perigee=0.0,
        mean_anomaly=0.0,
    )
    
    assert sat.sat_id == "test_sat"
    assert sat.semi_major_axis == EARTH_RADIUS + 550.0
    assert sat.position is not None
    assert sat.velocity is not None


def test_satellite_propagation():
    """Test satellite orbital propagation."""
    sat = Satellite(
        sat_id="test_sat",
        semi_major_axis=EARTH_RADIUS + 550.0,
        eccentricity=0.0,
        inclination=53.0,
    )
    
    initial_position = sat.position.copy()
    initial_time = sat.time
    
    # Propagate for 1 minute
    sat.propagate(60.0)
    
    # Position should have changed
    assert not np.allclose(sat.position, initial_position)
    
    # Time should have advanced
    assert sat.time == initial_time + 60.0


def test_geodetic_position():
    """Test geodetic position calculation."""
    sat = Satellite(
        sat_id="test_sat",
        semi_major_axis=EARTH_RADIUS + 550.0,
        eccentricity=0.0,
        inclination=0.0,
    )
    
    lat, lon, alt = sat.get_geodetic_position()
    
    # Latitude should be valid
    assert -90 <= lat <= 90
    
    # Longitude should be valid
    assert -180 <= lon <= 180
    
    # Altitude should be around 550 km
    assert 500 < alt < 600


def test_orbital_period():
    """Test orbital period calculation."""
    sat = Satellite(
        sat_id="test_sat",
        semi_major_axis=EARTH_RADIUS + 550.0,
    )
    
    period = sat.get_orbital_period()
    
    # Period should be around 95 minutes
    assert 5400 < period < 6000


def test_satellite_repr():
    """Test satellite string representation."""
    sat = Satellite(
        sat_id="test_sat",
        semi_major_axis=EARTH_RADIUS + 550.0,
    )
    
    repr_str = repr(sat)
    
    assert "test_sat" in repr_str
    assert "altitude" in repr_str
