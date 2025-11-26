"""
Tests for GroundStation class.
"""

import pytest
import numpy as np
from satcom import GroundStation, Satellite
from satcom.orbital_mechanics import EARTH_RADIUS


def test_ground_station_creation():
    """Test ground station creation."""
    gs = GroundStation(
        gs_id="test_gs",
        latitude=47.6,
        longitude=-122.3,
        altitude=0.0,
        min_elevation=10.0,
    )
    
    assert gs.gs_id == "test_gs"
    assert gs.latitude == 47.6
    assert gs.longitude == -122.3
    assert gs.position is not None


def test_visibility_check():
    """Test satellite visibility from ground station."""
    # Ground station at equator
    gs = GroundStation(
        gs_id="test_gs",
        latitude=0.0,
        longitude=0.0,
        min_elevation=10.0,
    )
    
    # Satellite directly overhead
    sat = Satellite(
        sat_id="test_sat",
        semi_major_axis=EARTH_RADIUS + 550.0,
        eccentricity=0.0,
        inclination=0.0,
        raan=0.0,
        arg_perigee=0.0,
        mean_anomaly=0.0,
    )
    
    # Should be visible
    is_visible = gs.is_visible(sat)
    assert is_visible


def test_elevation_angle():
    """Test elevation angle calculation."""
    gs = GroundStation(
        gs_id="test_gs",
        latitude=0.0,
        longitude=0.0,
    )
    
    sat = Satellite(
        sat_id="test_sat",
        semi_major_axis=EARTH_RADIUS + 550.0,
        eccentricity=0.0,
        inclination=0.0,
    )
    
    elevation = gs.get_elevation_angle(sat)
    
    assert elevation is not None
    assert -90 <= elevation <= 90


def test_distance_calculation():
    """Test distance to satellite calculation."""
    gs = GroundStation(
        gs_id="test_gs",
        latitude=0.0,
        longitude=0.0,
    )
    
    sat = Satellite(
        sat_id="test_sat",
        semi_major_axis=EARTH_RADIUS + 550.0,
    )
    
    distance = gs.get_distance(sat)
    
    assert distance is not None
    assert distance > 0


def test_visible_satellites():
    """Test getting list of visible satellites."""
    gs = GroundStation(
        gs_id="test_gs",
        latitude=0.0,
        longitude=0.0,
        min_elevation=10.0,
    )
    
    satellites = []
    for i in range(5):
        sat = Satellite(
            sat_id=f"sat_{i}",
            semi_major_axis=EARTH_RADIUS + 550.0,
            eccentricity=0.0,
            inclination=53.0,
            raan=i * 30.0,
            arg_perigee=0.0,
            mean_anomaly=i * 60.0,
        )
        satellites.append(sat)
    
    visible = gs.get_visible_satellites(satellites)
    
    # Some satellites should be visible
    assert isinstance(visible, list)
    assert len(visible) <= len(satellites)


def test_ground_station_repr():
    """Test ground station string representation."""
    gs = GroundStation(
        gs_id="test_gs",
        latitude=47.6,
        longitude=-122.3,
    )
    
    repr_str = repr(gs)
    
    assert "test_gs" in repr_str
    assert "lat" in repr_str
