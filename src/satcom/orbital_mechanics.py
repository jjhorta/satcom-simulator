"""
Orbital mechanics calculations for satellite constellation simulation.

This module provides functions for calculating satellite positions, velocities,
and orbital parameters based on Keplerian orbital elements.
"""

import numpy as np
from typing import Tuple


# Physical constants
EARTH_RADIUS = 6371.0  # km
EARTH_MU = 398600.4418  # km^3/s^2 - Earth's gravitational parameter
EARTH_J2 = 1.08263e-3  # Earth's J2 oblateness coefficient


def orbital_elements_to_position_velocity(
    semi_major_axis: float,
    eccentricity: float,
    inclination: float,
    raan: float,
    arg_perigee: float,
    true_anomaly: float
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Convert Keplerian orbital elements to position and velocity vectors.
    
    Args:
        semi_major_axis: Semi-major axis in km
        eccentricity: Orbital eccentricity (0 for circular)
        inclination: Inclination in radians
        raan: Right Ascension of Ascending Node in radians
        arg_perigee: Argument of perigee in radians
        true_anomaly: True anomaly in radians
    
    Returns:
        Tuple of (position, velocity) in Earth-Centered Inertial (ECI) frame
        position: [x, y, z] in km
        velocity: [vx, vy, vz] in km/s
    """
    # Semi-latus rectum
    p = semi_major_axis * (1 - eccentricity**2)
    
    # Distance from focus
    r = p / (1 + eccentricity * np.cos(true_anomaly))
    
    # Position in orbital plane
    r_orb = r * np.array([np.cos(true_anomaly), np.sin(true_anomaly), 0])
    
    # Velocity in orbital plane
    v_orb = np.sqrt(EARTH_MU / p) * np.array([
        -np.sin(true_anomaly),
        eccentricity + np.cos(true_anomaly),
        0
    ])
    
    # Rotation matrices
    # Rotate by argument of perigee
    cos_w, sin_w = np.cos(arg_perigee), np.sin(arg_perigee)
    R_w = np.array([
        [cos_w, -sin_w, 0],
        [sin_w, cos_w, 0],
        [0, 0, 1]
    ])
    
    # Rotate by inclination
    cos_i, sin_i = np.cos(inclination), np.sin(inclination)
    R_i = np.array([
        [1, 0, 0],
        [0, cos_i, -sin_i],
        [0, sin_i, cos_i]
    ])
    
    # Rotate by RAAN
    cos_O, sin_O = np.cos(raan), np.sin(raan)
    R_O = np.array([
        [cos_O, -sin_O, 0],
        [sin_O, cos_O, 0],
        [0, 0, 1]
    ])
    
    # Combined rotation matrix
    R = R_O @ R_i @ R_w
    
    # Transform to ECI frame
    position = R @ r_orb
    velocity = R @ v_orb
    
    return position, velocity


def mean_motion(semi_major_axis: float) -> float:
    """
    Calculate mean motion (mean angular velocity) from semi-major axis.
    
    Args:
        semi_major_axis: Semi-major axis in km
    
    Returns:
        Mean motion in radians per second
    """
    return np.sqrt(EARTH_MU / semi_major_axis**3)


def orbital_period(semi_major_axis: float) -> float:
    """
    Calculate orbital period from semi-major axis.
    
    Args:
        semi_major_axis: Semi-major axis in km
    
    Returns:
        Orbital period in seconds
    """
    return 2 * np.pi / mean_motion(semi_major_axis)


def propagate_mean_anomaly(mean_anomaly: float, semi_major_axis: float, dt: float) -> float:
    """
    Propagate mean anomaly forward in time.
    
    Args:
        mean_anomaly: Initial mean anomaly in radians
        semi_major_axis: Semi-major axis in km
        dt: Time step in seconds
    
    Returns:
        New mean anomaly in radians
    """
    n = mean_motion(semi_major_axis)
    new_mean_anomaly = mean_anomaly + n * dt
    # Normalize to [0, 2*pi]
    return new_mean_anomaly % (2 * np.pi)


def mean_to_true_anomaly(mean_anomaly: float, eccentricity: float, tolerance: float = 1e-8) -> float:
    """
    Convert mean anomaly to true anomaly using Newton-Raphson iteration.
    
    Args:
        mean_anomaly: Mean anomaly in radians
        eccentricity: Orbital eccentricity
        tolerance: Convergence tolerance
    
    Returns:
        True anomaly in radians
    """
    # First solve for eccentric anomaly using Newton-Raphson
    E = mean_anomaly  # Initial guess
    
    for _ in range(100):  # Max iterations
        f = E - eccentricity * np.sin(E) - mean_anomaly
        f_prime = 1 - eccentricity * np.cos(E)
        E_new = E - f / f_prime
        
        if abs(E_new - E) < tolerance:
            E = E_new
            break
        E = E_new
    
    # Convert eccentric anomaly to true anomaly
    true_anomaly = 2 * np.arctan2(
        np.sqrt(1 + eccentricity) * np.sin(E / 2),
        np.sqrt(1 - eccentricity) * np.cos(E / 2)
    )
    
    return true_anomaly % (2 * np.pi)


def eci_to_geodetic(position: np.ndarray) -> Tuple[float, float, float]:
    """
    Convert ECI position to geodetic coordinates (latitude, longitude, altitude).
    
    Args:
        position: Position vector [x, y, z] in km (ECI frame)
    
    Returns:
        Tuple of (latitude, longitude, altitude)
        latitude: in radians
        longitude: in radians
        altitude: in km above Earth's surface
    """
    x, y, z = position
    
    # Longitude is straightforward
    longitude = np.arctan2(y, x)
    
    # Distance from Earth's center
    r = np.linalg.norm(position)
    
    # Latitude (simplified, assumes spherical Earth)
    latitude = np.arcsin(z / r)
    
    # Altitude above surface
    altitude = r - EARTH_RADIUS
    
    return latitude, longitude, altitude


def geodetic_to_eci(latitude: float, longitude: float, altitude: float) -> np.ndarray:
    """
    Convert geodetic coordinates to ECI position.
    
    Args:
        latitude: Latitude in radians
        longitude: Longitude in radians
        altitude: Altitude in km above Earth's surface
    
    Returns:
        Position vector [x, y, z] in km (ECI frame)
    """
    r = EARTH_RADIUS + altitude
    
    x = r * np.cos(latitude) * np.cos(longitude)
    y = r * np.cos(latitude) * np.sin(longitude)
    z = r * np.sin(latitude)
    
    return np.array([x, y, z])


def calculate_elevation_angle(sat_position: np.ndarray, gs_position: np.ndarray) -> float:
    """
    Calculate elevation angle from ground station to satellite.
    
    Args:
        sat_position: Satellite position in ECI frame [x, y, z] in km
        gs_position: Ground station position in ECI frame [x, y, z] in km
    
    Returns:
        Elevation angle in radians (0 = horizon, pi/2 = zenith)
    """
    # Vector from ground station to satellite
    los_vector = sat_position - gs_position
    
    # Local vertical at ground station (radial direction)
    local_vertical = gs_position / np.linalg.norm(gs_position)
    
    # Elevation angle
    cos_zenith = np.dot(los_vector, local_vertical) / np.linalg.norm(los_vector)
    zenith_angle = np.arccos(np.clip(cos_zenith, -1, 1))
    elevation = np.pi / 2 - zenith_angle
    
    return elevation


def calculate_distance(pos1: np.ndarray, pos2: np.ndarray) -> float:
    """
    Calculate Euclidean distance between two positions.
    
    Args:
        pos1: First position [x, y, z] in km
        pos2: Second position [x, y, z] in km
    
    Returns:
        Distance in km
    """
    return np.linalg.norm(pos1 - pos2)
