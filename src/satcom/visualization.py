"""
Visualization tools for satellite constellations.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from typing import Optional, List
from .constellation import Constellation
from .orbital_mechanics import EARTH_RADIUS


def plot_constellation_2d(
    constellation: Constellation,
    figsize: tuple = (12, 8),
    show_ground_stations: bool = True,
    show_links: bool = False,
) -> plt.Figure:
    """
    Plot a 2D view of the constellation (lat/lon projection).
    
    Args:
        constellation: Constellation object to plot
        figsize: Figure size (width, height)
        show_ground_stations: Whether to show ground stations
        show_links: Whether to show communication links
    
    Returns:
        matplotlib Figure object
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    # Plot Earth outline
    theta = np.linspace(0, 2 * np.pi, 100)
    ax.plot(180 * np.cos(theta) / np.pi, 90 * np.sin(theta) / np.pi, 'k-', linewidth=2)
    
    # Plot satellites
    if constellation.satellites:
        lats = []
        lons = []
        for sat in constellation.satellites:
            lat, lon, _ = sat.get_geodetic_position()
            lats.append(lat)
            lons.append(lon)
        
        ax.scatter(lons, lats, c='blue', s=50, alpha=0.6, label='Satellites')
    
    # Plot ground stations
    if show_ground_stations and constellation.ground_stations:
        gs_lats = [gs.latitude for gs in constellation.ground_stations]
        gs_lons = [gs.longitude for gs in constellation.ground_stations]
        ax.scatter(gs_lons, gs_lats, c='red', marker='^', s=100, 
                  label='Ground Stations')
        
        # Show visibility links
        if show_links:
            for gs in constellation.ground_stations:
                visible_sats = gs.get_visible_satellites(constellation.satellites)
                for sat in visible_sats:
                    sat_lat, sat_lon, _ = sat.get_geodetic_position()
                    ax.plot([gs.longitude, sat_lon], [gs.latitude, sat_lat],
                           'g-', alpha=0.2, linewidth=0.5)
    
    ax.set_xlabel('Longitude (degrees)')
    ax.set_ylabel('Latitude (degrees)')
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_title(f'Constellation: {constellation.name}')
    
    return fig


def plot_constellation_3d(
    constellation: Constellation,
    figsize: tuple = (12, 10),
) -> plt.Figure:
    """
    Plot a 3D view of the constellation.
    
    Args:
        constellation: Constellation object to plot
        figsize: Figure size (width, height)
    
    Returns:
        matplotlib Figure object
    """
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection='3d')
    
    # Plot Earth
    u = np.linspace(0, 2 * np.pi, 50)
    v = np.linspace(0, np.pi, 50)
    x_earth = EARTH_RADIUS * np.outer(np.cos(u), np.sin(v))
    y_earth = EARTH_RADIUS * np.outer(np.sin(u), np.sin(v))
    z_earth = EARTH_RADIUS * np.outer(np.ones(np.size(u)), np.cos(v))
    ax.plot_surface(x_earth, y_earth, z_earth, color='lightblue', alpha=0.3)
    
    # Plot satellites
    if constellation.satellites:
        sat_positions = np.array([sat.position for sat in constellation.satellites])
        ax.scatter(sat_positions[:, 0], sat_positions[:, 1], sat_positions[:, 2],
                  c='blue', s=50, alpha=0.8, label='Satellites')
    
    # Plot ground stations
    if constellation.ground_stations:
        gs_positions = np.array([gs.position for gs in constellation.ground_stations])
        ax.scatter(gs_positions[:, 0], gs_positions[:, 1], gs_positions[:, 2],
                  c='red', marker='^', s=100, label='Ground Stations')
    
    ax.set_xlabel('X (km)')
    ax.set_ylabel('Y (km)')
    ax.set_zlabel('Z (km)')
    ax.legend()
    ax.set_title(f'Constellation: {constellation.name} (3D View)')
    
    # Equal aspect ratio
    max_range = np.max([sat.semi_major_axis for sat in constellation.satellites]) if constellation.satellites else EARTH_RADIUS * 2
    ax.set_xlim([-max_range, max_range])
    ax.set_ylim([-max_range, max_range])
    ax.set_zlim([-max_range, max_range])
    
    return fig


def plot_coverage_over_time(
    simulation_history: List[dict],
    figsize: tuple = (12, 6),
) -> plt.Figure:
    """
    Plot coverage statistics over time.
    
    Args:
        simulation_history: List of simulation state dictionaries
        figsize: Figure size (width, height)
    
    Returns:
        matplotlib Figure object
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    times = [state["time"] / 3600 for state in simulation_history]  # Convert to hours
    coverage = [state["coverage_stats"]["coverage_percentage"] 
                for state in simulation_history]
    avg_visible = [state["coverage_stats"]["avg_visible_satellites"]
                   for state in simulation_history]
    
    ax.plot(times, coverage, 'b-', linewidth=2, label='Coverage %')
    ax.set_xlabel('Time (hours)')
    ax.set_ylabel('Coverage (%)', color='b')
    ax.tick_params(axis='y', labelcolor='b')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 105)
    
    # Second y-axis for average visible satellites
    ax2 = ax.twinx()
    ax2.plot(times, avg_visible, 'r-', linewidth=2, label='Avg Visible Sats')
    ax2.set_ylabel('Avg Visible Satellites', color='r')
    ax2.tick_params(axis='y', labelcolor='r')
    
    ax.set_title('Coverage Statistics Over Time')
    
    # Combine legends
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc='best')
    
    return fig


def plot_ground_track(
    constellation: Constellation,
    satellite_id: str,
    duration: float,
    time_step: float = 60.0,
    figsize: tuple = (12, 6),
) -> Optional[plt.Figure]:
    """
    Plot the ground track of a specific satellite.
    
    Args:
        constellation: Constellation object
        satellite_id: ID of satellite to track
        duration: Duration to track in seconds
        time_step: Time step for tracking in seconds
        figsize: Figure size (width, height)
    
    Returns:
        matplotlib Figure object or None if satellite not found
    """
    satellite = constellation.get_satellite(satellite_id)
    if satellite is None:
        return None
    
    # Store initial state
    initial_mean_anomaly = satellite.mean_anomaly
    initial_time = satellite.time
    
    # Track satellite
    lats = []
    lons = []
    num_steps = int(duration / time_step)
    
    for _ in range(num_steps):
        lat, lon, _ = satellite.get_geodetic_position()
        lats.append(lat)
        lons.append(lon)
        satellite.propagate(time_step)
    
    # Restore initial state
    satellite.mean_anomaly = initial_mean_anomaly
    satellite.time = initial_time
    satellite.update_state()
    
    # Plot
    fig, ax = plt.subplots(figsize=figsize)
    
    # Plot world map outline
    ax.plot([-180, 180, 180, -180, -180], [-90, -90, 90, 90, -90], 'k-', linewidth=2)
    
    # Plot ground track
    # Handle longitude wrapping
    lons_wrapped = []
    lats_wrapped = []
    for i, (lon, lat) in enumerate(zip(lons, lats)):
        if i > 0 and abs(lon - lons[i-1]) > 180:
            # Break in track due to wrapping
            ax.plot(lons_wrapped, lats_wrapped, 'b-', linewidth=2, alpha=0.7)
            lons_wrapped = []
            lats_wrapped = []
        lons_wrapped.append(lon)
        lats_wrapped.append(lat)
    
    ax.plot(lons_wrapped, lats_wrapped, 'b-', linewidth=2, alpha=0.7, label='Ground Track')
    
    # Mark start and end
    ax.plot(lons[0], lats[0], 'go', markersize=10, label='Start')
    ax.plot(lons[-1], lats[-1], 'ro', markersize=10, label='End')
    
    ax.set_xlabel('Longitude (degrees)')
    ax.set_ylabel('Latitude (degrees)')
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_title(f'Ground Track: {satellite_id} ({duration/3600:.1f} hours)')
    
    return fig
