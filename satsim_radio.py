#!/usr/bin/env python3
"""
Satellite Constellation Radio Link Simulator
Entry point: argument parsing and mode dispatch.
jhorta
"""

import argparse

# sim.backends must be imported first to configure matplotlib before any pyplot use
from sim import backends  # noqa: F401 - side-effect: sets up matplotlib Agg + fonts
from sim.backends import set_graphics_backend, load_backend_modules
from sim.constants import AVAILABLE_BACKENDS, COMMS_PAYLOADS, WEATHER_SCENARIOS
from sim.modes.heatmap import run_heatmap
from sim.modes.sky import view_sky, run_coverage
from sim.modes.orbit import view_orbit
from sim.modes.track import view_track
from sim.modes.route import run_route_analysis

def main():
    parser = argparse.ArgumentParser(description="Satellite Constellation Radio Link Simulator - Combined")
    
    # Global backend option
    parser.add_argument('--backend', default='matplotlib', 
                       choices=AVAILABLE_BACKENDS,
                       help='Graphics backend: matplotlib (static PNG), plotly (interactive 3D HTML), bokeh (interactive 2D HTML)')
    
    subparsers = parser.add_subparsers(dest='mode', help='Simulation mode')
    
    # Sky mode
    sky_parser = subparsers.add_parser('sky', help='Sky view from observer location')
    sky_parser.add_argument('--location', default='panama_canal', help='Location name or lat,lon')
    sky_parser.add_argument('--coverage', nargs='?', const='', help='Coverage mode: empty (LOCATIONS), sea, arctic, both, all')
    sky_parser.add_argument('--comms', default='vdes', choices=COMMS_PAYLOADS.keys())
    sky_parser.add_argument('--weather', default='clear', choices=WEATHER_SCENARIOS.keys())
    sky_parser.add_argument('--sats', type=int, default=66)
    sky_parser.add_argument('--planes', type=int, default=6)
    sky_parser.add_argument('--altitude', type=float, default=600.0)
    sky_parser.add_argument('--phasing', type=int, default=1)
    sky_parser.add_argument('--inclination', type=float, default=87.4)
    sky_parser.add_argument('--sso', action='store_true', help='Use SSO inclination')
    sky_parser.add_argument('--bidi', action='store_true', help='Calculate bidirectional links')
    sky_parser.add_argument('--duration', type=int, default=3600)
    sky_parser.add_argument('--speed', type=int, default=60)
    sky_parser.add_argument('--trails', action='store_true', help='Draw satellite trails')
    sky_parser.add_argument('--save', action='store_true')
    
    # Heatmap mode
    heatmap_parser = subparsers.add_parser('heatmap', help='Global coverage heatmap (vectorized)')
    heatmap_parser.add_argument('--comms', default='vdes', choices=COMMS_PAYLOADS.keys())
    heatmap_parser.add_argument('--weather', default='clear', choices=WEATHER_SCENARIOS.keys())
    heatmap_parser.add_argument('--sats', type=int, default=66)
    heatmap_parser.add_argument('--planes', type=int, default=6)
    heatmap_parser.add_argument('--altitude', type=float, default=600.0)
    heatmap_parser.add_argument('--phasing', type=int, default=1)
    heatmap_parser.add_argument('--inclination', type=float, default=87.4)
    heatmap_parser.add_argument('--sso', action='store_true')
    heatmap_parser.add_argument('--bidi', action='store_true')
    heatmap_parser.add_argument('--res', type=float, default=5.0, help='Grid resolution in degrees')
    heatmap_parser.add_argument('--min-elev', type=float, default=10.0, help='Minimum elevation angle (degrees)')
    
    # Orbit mode
    orbit_parser = subparsers.add_parser('orbit', help='3D orbital view')
    orbit_parser.add_argument('--sats', type=int, default=66)
    orbit_parser.add_argument('--planes', type=int, default=6)
    orbit_parser.add_argument('--altitude', type=float, default=600.0)
    orbit_parser.add_argument('--phasing', type=int, default=1)
    orbit_parser.add_argument('--inclination', type=float, default=87.4)
    orbit_parser.add_argument('--sso', action='store_true')
    orbit_parser.add_argument('--platform', default='smallsat', 
                             choices=['nanosat', 'microsat', 'smallsat', 'mediumsat', 'largesat'],
                             help='Satellite platform type (affects TCO calculation)')
    orbit_parser.add_argument('--comms', default='vdes', choices=COMMS_PAYLOADS.keys(),
                             help='Communications payload type')
    orbit_parser.add_argument('--trails', action='store_true', help='Draw orbital trails')
    orbit_parser.add_argument('--map', action='store_true', help='Show Earth with NASA texture')
    orbit_parser.add_argument('--beams', action='store_true', help='Show satellite coverage beams')
    orbit_parser.add_argument('--min-elev', type=float, default=10.0, help='Minimum elevation angle (degrees)')
    orbit_parser.add_argument('--duration', type=int, default=360, help='Simulation duration in minutes (default: 360 = 6 hours)')
    orbit_parser.add_argument('--save', action='store_true', help='Save to file')
    
    # Track mode
    track_parser = subparsers.add_parser('track', help='Ground track view')
    track_parser.add_argument('--sats', type=int, default=66)
    track_parser.add_argument('--planes', type=int, default=6)
    track_parser.add_argument('--altitude', type=float, default=600.0)
    track_parser.add_argument('--phasing', type=int, default=1)
    track_parser.add_argument('--inclination', type=float, default=87.4)
    track_parser.add_argument('--sso', action='store_true')
    track_parser.add_argument('--duration', type=int, default=3600)
    track_parser.add_argument('--map', action='store_true', help='Show world map background (Mercator projection)')
    track_parser.add_argument('--save', action='store_true', help='Save to file')
    
    # Route mode - analyze specific route
    route_parser = subparsers.add_parser('route', help='Analyze coverage along a specific sea/arctic route')
    route_parser.add_argument('--route', required=True, 
                             help='Route name - SEA: titan_corridor, dragon_path, silk_vein, roaring_passage | ARCTIC: borealis_run, franklin_maze, midnight_sun_arc')
    route_parser.add_argument('--comms', default='vdes', choices=COMMS_PAYLOADS.keys())
    route_parser.add_argument('--weather', default='clear', choices=WEATHER_SCENARIOS.keys())
    route_parser.add_argument('--sats', type=int, default=66)
    route_parser.add_argument('--planes', type=int, default=6)
    route_parser.add_argument('--altitude', type=float, default=600.0)
    route_parser.add_argument('--phasing', type=int, default=1)
    route_parser.add_argument('--inclination', type=float, default=87.4)
    route_parser.add_argument('--sso', action='store_true', help='Use SSO inclination')
    route_parser.add_argument('--bidi', action='store_true', help='Calculate bidirectional links')
    route_parser.add_argument('--duration', type=int, default=3600)
    route_parser.add_argument('--speed', type=int, default=60)
    route_parser.add_argument('--min-elev', type=float, default=10.0, help='Minimum elevation angle (degrees)')
    route_parser.add_argument('--trails', action='store_true', help='Draw satellite trails in animations')
    route_parser.add_argument('--save', action='store_true', help='Save individual waypoint animations (default: False)')
    
    args = parser.parse_args()
    
    # Set graphics backend before any plotting
    if hasattr(args, 'backend'):
        set_graphics_backend(args.backend)
        load_backend_modules(args.backend)
    
    if not args.mode:
        parser.print_help()
        return
    
    if args.mode == 'sky':
        if args.coverage is not None:
            run_coverage(args)
        else:
            view_sky(args)
    elif args.mode == 'heatmap':
        run_heatmap(args)
    elif args.mode == 'orbit':
        view_orbit(args)
    elif args.mode == 'track':
        view_track(args)
    elif args.mode == 'route':
        run_route_analysis(args)


if __name__ == "__main__":
    main()
