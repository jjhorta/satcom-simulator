"""
Route analysis mode: evaluate coverage along named sea/arctic routes.
"""

import csv
from ..physics import calculate_sso_inclination
from ..constants import SEA_ROUTES, ARCTIC_ROUTES
from .sky import view_sky


def run_route_analysis(args):
    """Analyze coverage along a specific sea or arctic route"""
    route_name = args.route

    if route_name in SEA_ROUTES:
        route_data = SEA_ROUTES[route_name]
        route_type = "Sea Route"
    elif route_name in ARCTIC_ROUTES:
        route_data = ARCTIC_ROUTES[route_name]
        route_type = "Arctic Route"
    else:
        print(f"❌ Unknown route: {route_name}")
        print("\nAvailable routes:")
        print("  SEA ROUTES:", ", ".join(SEA_ROUTES.keys()))
        print("  ARCTIC ROUTES:", ", ".join(ARCTIC_ROUTES.keys()))
        return

    print(f"\n🛳️  ROUTE ANALYSIS: {route_name.upper()} ({route_type})")
    print(f"   {len(route_data)} waypoints")
    print("="*80)

    inc = calculate_sso_inclination(args.altitude) if args.sso else args.inclination

    # Use constellation name in suffix if multi-shell
    if getattr(args, 'constellation', None):
        walker_suffix = f"multi_{args.constellation}_{sum(sh.get('sats',0) for sh in __import__('json').loads(args.shells or '[]')) or args.constellation}sats" if getattr(args, 'shells', None) else f"multi_{args.constellation}"
    elif getattr(args, 'shells', None):
        try:
            import json as _json
            _shells = _json.loads(args.shells)
            _total = sum(sh.get('sats', 0) for sh in _shells)
            _name = getattr(args, 'constellation_name', None) or 'custom'
            walker_suffix = f"multi_{_name}_{_total}sats"
        except Exception:
            walker_suffix = f"walker_{int(inc)}_{args.sats}_{args.planes}"
    else:
        walker_suffix = f"walker_{int(inc)}_{args.sats}_{args.planes}"

    original_save = args.save
    args.save = False

    if not hasattr(args, 'no_display'):
        args.no_display = True

    results = []

    for idx, (wp_name, lat, lon) in enumerate(route_data, 1):
        print(f"\n[{idx}/{len(route_data)}] Analyzing: {wp_name} ({lat:.2f}°, {lon:.2f}°)")
        args.location = f"{lat},{lon}"
        result = view_sky(args)

        if result:
            results.append({
                'waypoint': wp_name,
                'sequence': idx,
                'latitude': lat,
                'longitude': lon,
                'connectivity_pct': result['connectivity_pct']
            })
            print(f"   ✓ Connectivity: {result['connectivity_pct']:.1f}%")

    args.save = original_save

    csv_filename = f"route_{route_name}_{args.comms}_{walker_suffix}.csv"

    with open(csv_filename, 'w', newline='') as csvfile:
        fieldnames = ['sequence', 'waypoint', 'latitude', 'longitude', 'connectivity_pct', 'wkt_geom']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({
                'sequence': r['sequence'],
                'waypoint': r['waypoint'],
                'latitude': f"{r['latitude']:.4f}",
                'longitude': f"{r['longitude']:.4f}",
                'connectivity_pct': f"{r['connectivity_pct']:.1f}",
                'wkt_geom': f"POINT({r['longitude']} {r['latitude']})"
            })

    print("\n" + "="*80)
    print(f"📊 ROUTE SUMMARY: {route_name.upper()}")
    print("="*80)

    avg_connectivity = sum(r['connectivity_pct'] for r in results) / len(results) if results else 0
    min_connectivity = min(r['connectivity_pct'] for r in results) if results else 0
    max_connectivity = max(r['connectivity_pct'] for r in results) if results else 0
    worst = min(results, key=lambda x: x['connectivity_pct']) if results else None

    print(f"  Total Waypoints:        {len(results)}")
    print(f"  Average Connectivity:   {avg_connectivity:.1f}%")
    print(f"  Minimum Connectivity:   {min_connectivity:.1f}%")
    print(f"  Maximum Connectivity:   {max_connectivity:.1f}%")
    if worst:
        print(f"  Worst Coverage Point:   {worst['waypoint']} ({worst['connectivity_pct']:.1f}%)")
    print(f"\n💾 Results saved to: {csv_filename}")
    print("="*80 + "\n")
