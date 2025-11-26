"""
Tests for Simulator class.
"""

import pytest
from satcom import Constellation, Simulator, GroundStation
from satcom.orbital_mechanics import EARTH_RADIUS


def test_simulator_creation():
    """Test simulator creation."""
    constellation = Constellation(name="test")
    simulator = Simulator(constellation, time_step=60.0)
    
    assert simulator.constellation == constellation
    assert simulator.time_step == 60.0
    assert simulator.current_time == 0.0


def test_simulator_step():
    """Test single simulation step."""
    constellation = Constellation(name="test")
    constellation.create_walker_delta_constellation(
        total_sats=12,
        planes=3,
        phasing=1,
        altitude=550.0,
        inclination=53.0,
    )
    
    simulator = Simulator(constellation, time_step=60.0)
    initial_time = simulator.current_time
    
    simulator.step()
    
    assert simulator.current_time == initial_time + 60.0
    assert len(simulator.history) == 1


def test_simulator_run():
    """Test running simulation."""
    constellation = Constellation(name="test")
    constellation.create_walker_delta_constellation(
        total_sats=12,
        planes=3,
        phasing=1,
        altitude=550.0,
        inclination=53.0,
    )
    
    simulator = Simulator(constellation, time_step=60.0)
    
    # Run for 10 minutes
    simulator.run(duration=600.0, verbose=False)
    
    assert simulator.current_time == 600.0
    assert len(simulator.history) == 10  # 600/60 = 10 steps


def test_simulator_callback():
    """Test simulator callback functionality."""
    constellation = Constellation(name="test")
    constellation.create_walker_delta_constellation(
        total_sats=12,
        planes=3,
        phasing=1,
        altitude=550.0,
        inclination=53.0,
    )
    
    simulator = Simulator(constellation, time_step=60.0)
    
    # Track callback calls
    callback_count = [0]
    
    def test_callback(sim):
        callback_count[0] += 1
    
    simulator.add_callback(test_callback)
    
    # Run simulation
    simulator.run(duration=300.0, verbose=False)
    
    # Callback should be called for each step
    assert callback_count[0] == 5  # 300/60 = 5 steps


def test_simulator_reset():
    """Test simulator reset."""
    constellation = Constellation(name="test")
    constellation.create_walker_delta_constellation(
        total_sats=12,
        planes=3,
        phasing=1,
        altitude=550.0,
        inclination=53.0,
    )
    
    simulator = Simulator(constellation, time_step=60.0)
    
    # Run simulation
    simulator.run(duration=600.0, verbose=False)
    
    assert simulator.current_time > 0
    assert len(simulator.history) > 0
    
    # Reset
    simulator.reset()
    
    assert simulator.current_time == 0.0
    assert len(simulator.history) == 0


def test_get_coverage_over_time():
    """Test getting coverage over time."""
    constellation = Constellation(name="test")
    constellation.create_walker_delta_constellation(
        total_sats=12,
        planes=3,
        phasing=1,
        altitude=550.0,
        inclination=53.0,
    )
    
    # Add a ground station
    gs = GroundStation("test_gs", 47.6, -122.3)
    constellation.add_ground_station(gs)
    
    simulator = Simulator(constellation, time_step=60.0)
    simulator.run(duration=300.0, verbose=False)
    
    coverage_history = simulator.get_coverage_over_time()
    
    assert len(coverage_history) == 5
    assert "time" in coverage_history[0]
    assert "coverage_stats" in coverage_history[0]


def test_get_summary():
    """Test getting simulation summary."""
    constellation = Constellation(name="test")
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
    
    simulator = Simulator(constellation, time_step=60.0)
    simulator.run(duration=600.0, verbose=False)
    
    summary = simulator.get_summary()
    
    assert "total_time" in summary
    assert "num_steps" in summary
    assert "avg_coverage_percentage" in summary
    assert summary["total_time"] == 600.0
    assert summary["num_steps"] == 10
