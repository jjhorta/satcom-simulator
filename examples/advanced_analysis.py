#!/usr/bin/env python3
"""
Advanced constellation analysis example.

This example demonstrates:
1. Creating custom constellations
2. Using simulation callbacks for real-time analysis
3. Tracking specific satellite-ground station links
4. Analyzing coverage patterns over multiple orbits
"""

import sys
sys.path.insert(0, '../src')

from satcom import Constellation, Satellite, GroundStation, Simulator
from satcom.orbital_mechanics import EARTH_RADIUS
import numpy as np


def main():
    print("=== Advanced Constellation Analysis ===\n")
    
    # Create a constellation
    constellation = Constellation(name="Advanced Example")
    
    # Create a Walker Delta constellation: 36/6/1
    # This provides better coverage than the basic example
    constellation.create_walker_delta_constellation(
        total_sats=36,
        planes=6,
        phasing=1,
        altitude=550.0,
        inclination=53.0,
        prefix="sat",
    )
    
    print(f"Created constellation with {len(constellation.satellites)} satellites")
    
    # Add multiple ground stations for global coverage
    locations = [
        ("Seattle", 47.6, -122.3),
        ("London", 51.5, -0.1),
        ("Tokyo", 35.7, 139.7),
        ("Sydney", -33.9, 151.2),
        ("SaoPaulo", -23.5, -46.6),
        ("Mumbai", 19.1, 72.9),
        ("Cairo", 30.0, 31.2),
        ("NewYork", 40.7, -74.0),
        ("Moscow", 55.8, 37.6),
        ("Johannesburg", -26.2, 28.0),
    ]
    
    for name, lat, lon in locations:
        gs = GroundStation(f"GS_{name}", lat, lon, altitude=0.0, min_elevation=10.0)
        constellation.add_ground_station(gs)
    
    print(f"Added {len(constellation.ground_stations)} ground stations\n")
    
    # Track coverage statistics
    coverage_tracker = {
        'min_coverage': 100.0,
        'max_coverage': 0.0,
        'samples': 0,
        'total_coverage': 0.0,
    }
    
    def coverage_callback(sim):
        """Callback to track coverage statistics."""
        stats = sim.constellation.get_coverage_statistics()
        coverage = stats['coverage_percentage']
        
        coverage_tracker['samples'] += 1
        coverage_tracker['total_coverage'] += coverage
        coverage_tracker['min_coverage'] = min(coverage_tracker['min_coverage'], coverage)
        coverage_tracker['max_coverage'] = max(coverage_tracker['max_coverage'], coverage)
    
    # Create simulator and add callback
    print("Setting up simulator...")
    simulator = Simulator(constellation, time_step=60.0)
    simulator.add_callback(coverage_callback)
    
    # Run simulation for 2 orbital periods (approximately 3.2 hours)
    duration = 2 * constellation.satellites[0].get_orbital_period()
    print(f"Running simulation for {duration/3600:.2f} hours (2 orbital periods)...\n")
    
    simulator.run(duration=duration, verbose=False)
    
    # Print statistics
    print("\n=== Coverage Analysis ===")
    print(f"Simulation Duration: {duration/3600:.2f} hours")
    print(f"Number of Samples: {coverage_tracker['samples']}")
    print(f"Average Coverage: {coverage_tracker['total_coverage']/coverage_tracker['samples']:.1f}%")
    print(f"Minimum Coverage: {coverage_tracker['min_coverage']:.1f}%")
    print(f"Maximum Coverage: {coverage_tracker['max_coverage']:.1f}%")
    
    # Analyze specific ground station
    print("\n=== Ground Station Analysis: Tokyo ===")
    gs_tokyo = constellation.get_ground_station("GS_Tokyo")
    if gs_tokyo:
        visible_sats = gs_tokyo.get_visible_satellites(constellation.satellites)
        print(f"Currently Visible Satellites: {len(visible_sats)}")
        
        if visible_sats:
            print("\nVisible Satellites:")
            for sat in visible_sats[:5]:  # Show first 5
                elevation = gs_tokyo.get_elevation_angle(sat)
                distance = gs_tokyo.get_distance(sat)
                print(f"  {sat.sat_id}: elevation={elevation:.1f}°, distance={distance:.1f}km")
    
    # Analyze satellite distribution
    print("\n=== Satellite Distribution ===")
    orbital_planes = {}
    for sat in constellation.satellites:
        plane_id = sat.sat_id.split('_')[1]
        if plane_id not in orbital_planes:
            orbital_planes[plane_id] = []
        orbital_planes[plane_id].append(sat)
    
    print(f"Number of Orbital Planes: {len(orbital_planes)}")
    for plane_id, sats in sorted(orbital_planes.items()):
        print(f"  Plane {plane_id}: {len(sats)} satellites")
    
    # Calculate average altitude
    altitudes = [sat.get_geodetic_position()[2] for sat in constellation.satellites]
    print(f"\nAverage Altitude: {np.mean(altitudes):.1f} km")
    print(f"Altitude Range: {np.min(altitudes):.1f} - {np.max(altitudes):.1f} km")
    
    # Show orbital period
    period = constellation.satellites[0].get_orbital_period()
    print(f"Orbital Period: {period/60:.1f} minutes")
    
    print("\n=== Analysis Complete ===")


if __name__ == "__main__":
    main()
