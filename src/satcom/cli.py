"""
Command-line interface for the satellite constellation simulator.
"""

import argparse
import sys
from .constellation import Constellation
from .ground_station import GroundStation
from .simulator import Simulator
from .visualization import (
    plot_constellation_2d,
    plot_constellation_3d,
    plot_coverage_over_time,
    plot_ground_track,
)


def create_example_constellation() -> Constellation:
    """
    Create an example LEO constellation similar to Starlink.
    
    Returns:
        Constellation object
    """
    constellation = Constellation(name="Example LEO Constellation")
    
    # Create a Walker Delta constellation
    # 24 satellites in 3 planes at 550km altitude, 53° inclination
    constellation.create_walker_delta_constellation(
        total_sats=24,
        planes=3,
        phasing=1,
        altitude=550.0,
        inclination=53.0,
        prefix="sat",
    )
    
    # Add some ground stations
    ground_stations = [
        ("GS_Seattle", 47.6, -122.3, 0.0),
        ("GS_London", 51.5, -0.1, 0.0),
        ("GS_Tokyo", 35.7, 139.7, 0.0),
        ("GS_Sydney", -33.9, 151.2, 0.0),
        ("GS_SaoPaulo", -23.5, -46.6, 0.0),
    ]
    
    for gs_id, lat, lon, alt in ground_stations:
        gs = GroundStation(gs_id, lat, lon, alt)
        constellation.add_ground_station(gs)
    
    return constellation


def run_simulation(args):
    """
    Run a constellation simulation.
    """
    print("Creating constellation...")
    constellation = create_example_constellation()
    
    print(f"Constellation: {constellation}")
    print(f"  Satellites: {len(constellation.satellites)}")
    print(f"  Ground Stations: {len(constellation.ground_stations)}")
    
    print("\nInitializing simulator...")
    simulator = Simulator(constellation, time_step=args.time_step)
    
    print(f"Running simulation for {args.duration} seconds...")
    simulator.run(duration=args.duration, verbose=True)
    
    print("\nSimulation Summary:")
    summary = simulator.get_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # Save coverage plot if requested
    if args.output:
        print(f"\nGenerating coverage plot...")
        fig = plot_coverage_over_time(simulator.get_coverage_over_time())
        fig.savefig(args.output, dpi=150, bbox_inches='tight')
        print(f"Saved plot to {args.output}")


def visualize_constellation(args):
    """
    Visualize a constellation.
    """
    print("Creating constellation...")
    constellation = create_example_constellation()
    
    print(f"Constellation: {constellation}")
    
    if args.view == "2d":
        print("Generating 2D view...")
        fig = plot_constellation_2d(
            constellation,
            show_ground_stations=True,
            show_links=args.show_links,
        )
    elif args.view == "3d":
        print("Generating 3D view...")
        fig = plot_constellation_3d(constellation)
    else:
        print(f"Unknown view type: {args.view}")
        return
    
    if args.output:
        fig.savefig(args.output, dpi=150, bbox_inches='tight')
        print(f"Saved plot to {args.output}")
    else:
        import matplotlib.pyplot as plt
        plt.show()


def track_satellite(args):
    """
    Track a specific satellite's ground track.
    """
    print("Creating constellation...")
    constellation = create_example_constellation()
    
    print(f"Tracking satellite {args.satellite_id}...")
    fig = plot_ground_track(
        constellation,
        args.satellite_id,
        duration=args.duration,
        time_step=args.time_step,
    )
    
    if fig is None:
        print(f"Satellite {args.satellite_id} not found!")
        return
    
    if args.output:
        fig.savefig(args.output, dpi=150, bbox_inches='tight')
        print(f"Saved plot to {args.output}")
    else:
        import matplotlib.pyplot as plt
        plt.show()


def main():
    """
    Main entry point for the CLI.
    """
    parser = argparse.ArgumentParser(
        description="Satellite Constellation Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Simulate command
    sim_parser = subparsers.add_parser("simulate", help="Run a constellation simulation")
    sim_parser.add_argument(
        "--duration",
        type=float,
        default=3600.0,
        help="Simulation duration in seconds (default: 3600)",
    )
    sim_parser.add_argument(
        "--time-step",
        type=float,
        default=60.0,
        help="Time step in seconds (default: 60)",
    )
    sim_parser.add_argument(
        "--output",
        type=str,
        help="Output file for coverage plot (e.g., coverage.png)",
    )
    
    # Visualize command
    viz_parser = subparsers.add_parser("visualize", help="Visualize a constellation")
    viz_parser.add_argument(
        "--view",
        choices=["2d", "3d"],
        default="2d",
        help="View type (default: 2d)",
    )
    viz_parser.add_argument(
        "--show-links",
        action="store_true",
        help="Show communication links in 2D view",
    )
    viz_parser.add_argument(
        "--output",
        type=str,
        help="Output file for plot (e.g., constellation.png)",
    )
    
    # Track command
    track_parser = subparsers.add_parser("track", help="Track a satellite's ground track")
    track_parser.add_argument(
        "satellite_id",
        type=str,
        help="Satellite ID to track (e.g., sat_0_0)",
    )
    track_parser.add_argument(
        "--duration",
        type=float,
        default=5400.0,
        help="Tracking duration in seconds (default: 5400 = 1.5 hours)",
    )
    track_parser.add_argument(
        "--time-step",
        type=float,
        default=30.0,
        help="Time step in seconds (default: 30)",
    )
    track_parser.add_argument(
        "--output",
        type=str,
        help="Output file for plot (e.g., ground_track.png)",
    )
    
    args = parser.parse_args()
    
    if args.command == "simulate":
        run_simulation(args)
    elif args.command == "visualize":
        visualize_constellation(args)
    elif args.command == "track":
        track_satellite(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
