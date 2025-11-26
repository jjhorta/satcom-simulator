"""
Tests for Constellation class.
"""

import pytest
from satcom import Constellation, Satellite, GroundStation
from satcom.orbital_mechanics import EARTH_RADIUS


def test_constellation_creation():
    """Test constellation creation."""
    constellation = Constellation(name="test_constellation")
    
    assert constellation.name == "test_constellation"
    assert len(constellation.satellites) == 0
    assert len(constellation.ground_stations) == 0


def test_add_satellite():
    """Test adding satellites to constellation."""
    constellation = Constellation(name="test")
    
    sat = Satellite(
        sat_id="test_sat",
        semi_major_axis=EARTH_RADIUS + 550.0,
    )
    
    constellation.add_satellite(sat)
    
    assert len(constellation.satellites) == 1
    assert constellation.satellites[0] == sat


def test_add_ground_station():
    """Test adding ground stations to constellation."""
    constellation = Constellation(name="test")
    
    gs = GroundStation(
        gs_id="test_gs",
        latitude=47.6,
        longitude=-122.3,
    )
    
    constellation.add_ground_station(gs)
    
    assert len(constellation.ground_stations) == 1
    assert constellation.ground_stations[0] == gs


def test_walker_delta_constellation():
    """Test Walker Delta constellation creation."""
    constellation = Constellation(name="walker_test")
    
    # Create 12/3/1 Walker Delta constellation
    constellation.create_walker_delta_constellation(
        total_sats=12,
        planes=3,
        phasing=1,
        altitude=550.0,
        inclination=53.0,
    )
    
    assert len(constellation.satellites) == 12


def test_walker_delta_invalid_params():
    """Test Walker Delta with invalid parameters."""
    constellation = Constellation(name="walker_test")
    
    # Total satellites not divisible by planes
    with pytest.raises(ValueError):
        constellation.create_walker_delta_constellation(
            total_sats=13,
            planes=3,
            phasing=1,
            altitude=550.0,
            inclination=53.0,
        )


def test_propagate_constellation():
    """Test constellation propagation."""
    constellation = Constellation(name="test")
    
    # Add some satellites
    for i in range(3):
        sat = Satellite(
            sat_id=f"sat_{i}",
            semi_major_axis=EARTH_RADIUS + 550.0,
        )
        constellation.add_satellite(sat)
    
    # Store initial positions
    initial_positions = [sat.position.copy() for sat in constellation.satellites]
    
    # Propagate
    constellation.propagate(60.0)
    
    # Positions should have changed
    for i, sat in enumerate(constellation.satellites):
        assert not (sat.position == initial_positions[i]).all()


def test_coverage_statistics():
    """Test coverage statistics calculation."""
    constellation = Constellation(name="test")
    
    # Add satellites
    constellation.create_walker_delta_constellation(
        total_sats=12,
        planes=3,
        phasing=1,
        altitude=550.0,
        inclination=53.0,
    )
    
    # Add ground stations
    gs = GroundStation("test_gs", 47.6, -122.3)
    constellation.add_ground_station(gs)
    
    # Get statistics
    stats = constellation.get_coverage_statistics()
    
    assert "total_satellites" in stats
    assert "total_ground_stations" in stats
    assert "coverage_percentage" in stats
    assert stats["total_satellites"] == 12
    assert stats["total_ground_stations"] == 1


def test_get_satellite():
    """Test getting satellite by ID."""
    constellation = Constellation(name="test")
    
    sat = Satellite(
        sat_id="test_sat",
        semi_major_axis=EARTH_RADIUS + 550.0,
    )
    constellation.add_satellite(sat)
    
    found_sat = constellation.get_satellite("test_sat")
    
    assert found_sat is not None
    assert found_sat == sat
    
    # Non-existent satellite
    not_found = constellation.get_satellite("nonexistent")
    assert not_found is None


def test_get_ground_station():
    """Test getting ground station by ID."""
    constellation = Constellation(name="test")
    
    gs = GroundStation("test_gs", 47.6, -122.3)
    constellation.add_ground_station(gs)
    
    found_gs = constellation.get_ground_station("test_gs")
    
    assert found_gs is not None
    assert found_gs == gs
    
    # Non-existent ground station
    not_found = constellation.get_ground_station("nonexistent")
    assert not_found is None


def test_constellation_repr():
    """Test constellation string representation."""
    constellation = Constellation(name="test")
    
    repr_str = repr(constellation)
    
    assert "test" in repr_str
    assert "satellites" in repr_str
