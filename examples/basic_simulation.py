#!/usr/bin/env python3
"""
Basic example of using the satcom constellation simulator.

This example demonstrates:
1. Creating a constellation with Walker Delta pattern
2. Adding ground stations
3. Running a simulation
4. Analyzing coverage statistics
"""

import sys
sys.path.insert(0, '../src')

from satcom import Constellation, GroundStation, Simulator


def main():
    # Create a constellation
    print("Creating constellation...")
    constellation = Constellation(name="Example Constellation")
    
    # Create a Walker Delta constellation: 24 satellites, 3 planes, 550km altitude
    constellation.create_walker_delta_constellation(
        total_sats=24,
        planes=3,
        phasing=1,
        altitude=550.0,
        inclination=53.0,
        prefix="sat",
    )
    
    print(f"Created {len(constellation.satellites)} satellites")
    
    # Add ground stations
    ground_stations = [
        ("Seattle", 47.6, -122.3),
        ("London", 51.5, -0.1),
        ("Tokyo", 35.7, 139.7),
        ("Sydney", -33.9, 151.2),
        ("SaoPaulo", -23.5, -46.6),
        ("Mumbai", 19.1, 72.9),
        ("Cairo", 30.0, 31.2),
        ("NewYork", 40.7, -74.0),
    ]
    
    for name, lat, lon in ground_stations:
        gs = GroundStation(f"GS_{name}", lat, lon, altitude=0.0, min_elevation=10.0)
        constellation.add_ground_station(gs)
    
    print(f"Added {len(constellation.ground_stations)} ground stations")
    
    # Check initial coverage
    print("\nInitial Coverage:")
    stats = constellation.get_coverage_statistics()
    print(f"  Stations with coverage: {stats['stations_with_coverage']}/{stats['total_ground_stations']}")
    print(f"  Coverage percentage: {stats['coverage_percentage']:.1f}%")
    print(f"  Average visible satellites: {stats['avg_visible_satellites']:.2f}")
    
    # Run simulation for 1 hour
    print("\nRunning simulation for 1 hour...")
    simulator = Simulator(constellation, time_step=60.0)
    simulator.run(duration=3600.0, verbose=False)
    
    # Get simulation summary
    print("\nSimulation Summary:")
    summary = simulator.get_summary()
    print(f"  Total time: {summary['total_time']/3600:.2f} hours")
    print(f"  Number of steps: {summary['num_steps']}")
    print(f"  Average coverage: {summary['avg_coverage_percentage']:.1f}%")
    print(f"  Min coverage: {summary['min_coverage_percentage']:.1f}%")
    print(f"  Max coverage: {summary['max_coverage_percentage']:.1f}%")
    
    # Show satellite information
    print("\nSample Satellite Info:")
    for i in range(min(3, len(constellation.satellites))):
        sat = constellation.satellites[i]
        lat, lon, alt = sat.get_geodetic_position()
        period = sat.get_orbital_period()
        print(f"  {sat.sat_id}: lat={lat:.2f}°, lon={lon:.2f}°, alt={alt:.1f}km, period={period/60:.1f}min")


if __name__ == "__main__":
    main()
