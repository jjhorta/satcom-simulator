"""
Tests for orbital mechanics module.
"""

import pytest
import numpy as np
from satcom.orbital_mechanics import (
    orbital_elements_to_position_velocity,
    mean_motion,
    orbital_period,
    propagate_mean_anomaly,
    mean_to_true_anomaly,
    eci_to_geodetic,
    geodetic_to_eci,
    calculate_elevation_angle,
    calculate_distance,
    EARTH_RADIUS,
    EARTH_MU,
)


def test_circular_orbit_position():
    """Test position calculation for circular orbit."""
    # Circular orbit at 550km altitude
    semi_major_axis = EARTH_RADIUS + 550.0
    eccentricity = 0.0
    inclination = 0.0  # Equatorial
    raan = 0.0
    arg_perigee = 0.0
    true_anomaly = 0.0
    
    position, velocity = orbital_elements_to_position_velocity(
        semi_major_axis, eccentricity, inclination, raan, arg_perigee, true_anomaly
    )
    
    # At true anomaly 0, satellite should be at perigee on x-axis
    assert abs(np.linalg.norm(position) - semi_major_axis) < 1e-6
    assert abs(position[1]) < 1e-6  # y should be ~0
    assert abs(position[2]) < 1e-6  # z should be ~0


def test_mean_motion():
    """Test mean motion calculation."""
    semi_major_axis = EARTH_RADIUS + 550.0
    n = mean_motion(semi_major_axis)
    
    # Mean motion should be positive
    assert n > 0
    
    # For LEO, period should be around 90-100 minutes
    period = 2 * np.pi / n
    assert 5400 < period < 6000  # 90-100 minutes in seconds


def test_orbital_period():
    """Test orbital period calculation."""
    semi_major_axis = EARTH_RADIUS + 550.0
    period = orbital_period(semi_major_axis)
    
    # Period should be around 95 minutes for 550km altitude
    assert 5400 < period < 6000


def test_propagate_mean_anomaly():
    """Test mean anomaly propagation."""
    semi_major_axis = EARTH_RADIUS + 550.0
    mean_anomaly = 0.0
    dt = 3600.0  # 1 hour
    
    new_mean_anomaly = propagate_mean_anomaly(mean_anomaly, semi_major_axis, dt)
    
    # Mean anomaly should have increased
    assert new_mean_anomaly > mean_anomaly
    assert 0 <= new_mean_anomaly < 2 * np.pi


def test_mean_to_true_anomaly_circular():
    """Test conversion from mean to true anomaly for circular orbit."""
    eccentricity = 0.0
    mean_anomaly = np.pi / 4
    
    true_anomaly = mean_to_true_anomaly(mean_anomaly, eccentricity)
    
    # For circular orbit, true anomaly should equal mean anomaly
    assert abs(true_anomaly - mean_anomaly) < 1e-6


def test_mean_to_true_anomaly_elliptical():
    """Test conversion from mean to true anomaly for elliptical orbit."""
    eccentricity = 0.1
    mean_anomaly = np.pi / 2
    
    true_anomaly = mean_to_true_anomaly(mean_anomaly, eccentricity)
    
    # True anomaly should be valid
    assert 0 <= true_anomaly < 2 * np.pi


def test_geodetic_conversions():
    """Test geodetic to ECI and back."""
    lat = np.radians(45.0)  # 45° N
    lon = np.radians(30.0)  # 30° E
    alt = 550.0  # km
    
    # Convert to ECI
    position = geodetic_to_eci(lat, lon, alt)
    
    # Convert back
    lat_back, lon_back, alt_back = eci_to_geodetic(position)
    
    # Should be close to original
    assert abs(lat_back - lat) < 1e-6
    assert abs(lon_back - lon) < 1e-6
    assert abs(alt_back - alt) < 1.0  # Within 1km


def test_elevation_angle():
    """Test elevation angle calculation."""
    # Satellite directly overhead
    gs_position = np.array([EARTH_RADIUS, 0, 0])
    sat_position = np.array([EARTH_RADIUS + 550, 0, 0])
    
    elevation = calculate_elevation_angle(sat_position, gs_position)
    
    # Should be close to 90 degrees (zenith)
    assert elevation > np.radians(80)


def test_distance_calculation():
    """Test distance calculation."""
    pos1 = np.array([1000, 0, 0])
    pos2 = np.array([1000, 1000, 0])
    
    distance = calculate_distance(pos1, pos2)
    
    # Should be 1000 km (Pythagorean theorem)
    assert abs(distance - 1000.0) < 1e-6
