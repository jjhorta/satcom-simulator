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
from sim.constants import AVAILABLE_BACKENDS, COMMS_PAYLOADS, WEATHER_SCENARIOS, KNOWN_CONSTELLATIONS
from sim.modes.heatmap import run_heatmap
from sim.modes.heatmap_rf import run_heatmap_rf
from sim.modes.sky import view_sky, run_coverage
from sim.modes.orbit import view_orbit
from sim.modes.track import view_track
from sim.modes.route import run_route_analysis
from sim.modes.throughput import run_throughput

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
    sky_parser.add_argument('--constellation', default=None,
                            help='Named multi-shell constellation preset')
    sky_parser.add_argument('--constellation-name', default=None, dest='constellation_name',
                            help='Display name for a --shells multi-shell run')
    sky_parser.add_argument('--shells', default=None, metavar='JSON',
                            help='Inline JSON array of shell dicts')
    sky_parser.add_argument('--max-sats', type=int, default=250,
                            help='Max satellites to evaluate per timestep (default: 250)')
    
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
    heatmap_parser.add_argument('--constellation', default=None,
                                help='Named multi-shell constellation preset')
    heatmap_parser.add_argument('--constellation-name', default=None, dest='constellation_name',
                                help='Display name for a --shells multi-shell run')
    heatmap_parser.add_argument('--shells', default=None, metavar='JSON',
                                help='Inline JSON array of shell dicts')
    heatmap_parser.add_argument('--max-sats', type=int, default=250,
                                help='Max satellites to include (default: 250)')
    
    # Heatmap-RF mode (same params as heatmap, adds full RF link budget)
    heatmap_rf_parser = subparsers.add_parser('heatmap-rf', help='Global RF link budget heatmap')
    heatmap_rf_parser.add_argument('--comms', default='vdes', choices=COMMS_PAYLOADS.keys())
    heatmap_rf_parser.add_argument('--weather', default='clear', choices=WEATHER_SCENARIOS.keys())
    heatmap_rf_parser.add_argument('--sats', type=int, default=66)
    heatmap_rf_parser.add_argument('--planes', type=int, default=6)
    heatmap_rf_parser.add_argument('--altitude', type=float, default=600.0)
    heatmap_rf_parser.add_argument('--phasing', type=int, default=1)
    heatmap_rf_parser.add_argument('--inclination', type=float, default=87.4)
    heatmap_rf_parser.add_argument('--sso', action='store_true')
    heatmap_rf_parser.add_argument('--bidi', action='store_true')
    heatmap_rf_parser.add_argument('--res', type=float, default=5.0, help='Grid resolution in degrees')
    heatmap_rf_parser.add_argument('--min-elev', type=float, default=10.0, help='Minimum elevation angle (degrees)')
    heatmap_rf_parser.add_argument('--constellation', default=None,
                                   help='Named multi-shell constellation preset')
    heatmap_rf_parser.add_argument('--constellation-name', default=None, dest='constellation_name',
                                   help='Display name for a --shells multi-shell run')
    heatmap_rf_parser.add_argument('--shells', default=None, metavar='JSON',
                                   help='Inline JSON array of shell dicts')
    heatmap_rf_parser.add_argument('--max-sats', type=int, default=250,
                                   help='Max satellites to include (default: 250)')

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
    orbit_parser.add_argument('--fill', action='store_true', help='Fill coverage beams with semi-transparent caps (requires --beams --backend plotly)')
    orbit_parser.add_argument('--min-elev', type=float, default=10.0, help='Minimum elevation angle (degrees)')
    orbit_parser.add_argument('--duration', type=int, default=360, help='Simulation duration in minutes (default: 360 = 6 hours)')
    orbit_parser.add_argument('--save', action='store_true', help='Save to file')
    # Multi-shell options (mutually exclusive with single-shell --sats/--planes/--inclination)
    orbit_parser.add_argument('--constellation', default=None,
                             help='Load a named multi-shell constellation preset (must be in KNOWN_CONSTELLATIONS)')
    orbit_parser.add_argument('--constellation-name', default=None, dest='constellation_name',
                             help='Display/label name for a --shells multi-shell run (no lookup performed)')
    orbit_parser.add_argument('--shells', default=None, metavar='JSON',
                             help='Inline JSON array of shell dicts: '
                                  '[{"sats":50,"planes":5,"inclination":55,"altitude_km":525},...]')
    orbit_parser.add_argument('--max-sats', type=int, default=250,
                             help='Max satellites to render in animation (default: 250; reduce for performance)')
    
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
    route_parser.add_argument('--constellation', default=None,
                              help='Named multi-shell constellation preset')
    route_parser.add_argument('--constellation-name', default=None, dest='constellation_name',
                              help='Display name for a --shells multi-shell run')
    route_parser.add_argument('--shells', default=None, metavar='JSON',
                              help='Inline JSON array of shell dicts')
    route_parser.add_argument('--max-sats', type=int, default=250,
                              help='Max satellites to evaluate per timestep (default: 250)')

    # Throughput mode
    throughput_parser = subparsers.add_parser('throughput', help='IP throughput heatmap over time')
    throughput_parser.add_argument('--comms', default='vdes', choices=COMMS_PAYLOADS.keys())
    throughput_parser.add_argument('--weather', default='clear', choices=WEATHER_SCENARIOS.keys())
    throughput_parser.add_argument('--sats', type=int, default=66)
    throughput_parser.add_argument('--planes', type=int, default=6)
    throughput_parser.add_argument('--altitude', type=float, default=600.0)
    throughput_parser.add_argument('--phasing', type=int, default=1)
    throughput_parser.add_argument('--inclination', type=float, default=87.4)
    throughput_parser.add_argument('--sso', action='store_true')
    throughput_parser.add_argument('--bidi', action='store_true')
    throughput_parser.add_argument('--res', type=float, default=5.0, help='Grid resolution in degrees')
    throughput_parser.add_argument('--min-elev', type=float, default=10.0, help='Minimum elevation angle')
    throughput_parser.add_argument('--duration', type=int, default=60, help='Duration in minutes')
    throughput_parser.add_argument('--step', type=int, default=10, help='Snapshot interval in minutes')
    throughput_parser.add_argument('--constellation', default=None, help='Named multi-shell constellation preset')
    throughput_parser.add_argument('--constellation-name', default=None, dest='constellation_name',
                                   help='Display name for a --shells multi-shell run')
    throughput_parser.add_argument('--shells', default=None, metavar='JSON',
                                   help='Inline JSON array of shell dicts')
    throughput_parser.add_argument('--max-sats', type=int, default=250,
                                   help='Max satellites to include')

    # Latency mode (ISL routing, end-to-end RTT vs fiber baseline)
    latency_parser = subparsers.add_parser('latency',
                                           help='End-to-end latency simulation with ISL routing')
    latency_parser.add_argument('--from', dest='from_location', default='33.94,-118.41',
                                help='Source: lat,lon or named LOCATIONS entry')
    latency_parser.add_argument('--to', dest='to_location', default='38.81,-77.30',
                                help='Destination: lat,lon or named LOCATIONS entry')
    latency_parser.add_argument('--sats', type=int, default=66)
    latency_parser.add_argument('--planes', type=int, default=6)
    latency_parser.add_argument('--altitude', type=float, default=600.0)
    latency_parser.add_argument('--phasing', type=int, default=1)
    latency_parser.add_argument('--inclination', type=float, default=87.4)
    latency_parser.add_argument('--sso', action='store_true')
    latency_parser.add_argument('--duration', type=int, default=1440,
                                help='Simulation duration in minutes')
    latency_parser.add_argument('--step', type=int, default=5,
                                help='Snapshot interval in minutes')
    latency_parser.add_argument('--isl-range', type=float, default=5000.0, dest='isl_range',
                                help='Maximum ISL range in km')
    latency_parser.add_argument('--switching-delay', type=float, default=1.0, dest='switching_delay',
                                help='Per-hop switching delay in ms')
    latency_parser.add_argument('--min-elev', type=float, default=10.0, dest='min_elev')
    latency_parser.add_argument('--no-fiber', action='store_true', dest='no_fiber',
                                help='Skip fiber baseline comparison')
    latency_parser.add_argument('--constellation', default=None,
                                help='Named multi-shell constellation preset')
    latency_parser.add_argument('--constellation-name', default=None, dest='constellation_name',
                                help='Display name for a --shells multi-shell run')
    latency_parser.add_argument('--shells', default=None, metavar='JSON',
                                help='Inline JSON array of shell dicts')
    latency_parser.add_argument('--max-sats', type=int, default=250)

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
    elif args.mode == 'heatmap-rf':
        run_heatmap_rf(args)
    elif args.mode == 'orbit':
        view_orbit(args)
    elif args.mode == 'track':
        view_track(args)
    elif args.mode == 'route':
        run_route_analysis(args)
    elif args.mode == 'latency':
        from sim.modes.latency import run_latency
        args.fiber_baseline = not getattr(args, 'no_fiber', False)
        run_latency(args)


if __name__ == "__main__":
    main()
