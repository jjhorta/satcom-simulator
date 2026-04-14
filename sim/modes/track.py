"""
Track view mode: ground track visualization on a 2D Mercator map.
"""

import os
import json
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from datetime import timedelta
from skyfield.api import EarthSatellite, load, wgs84

from ..physics import calculate_sso_inclination
from ..constellation import generate_walker_delta_tles
from ..constants import COASTLINE_FILE


def load_earth_texture():
    """Load coastline GeoJSON for 2D Mercator background.
    Returns parsed GeoJSON dict or None if unavailable."""
    if not os.path.exists(COASTLINE_FILE):
        print(f"⚠️  Coastline data not found: {COASTLINE_FILE}")
        print("   Run orbit mode first to download coastline data automatically")
        return None

    try:
        with open(COASTLINE_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Error reading coastline data: {e}")
        return None


def view_track(args):
    """Ground track visualization"""
    ts = load.timescale()
    t0 = ts.utc(2024, 1, 1, 12, 0, 0)

    if args.sso:
        inc = calculate_sso_inclination(args.altitude)
        print(f"🛰️  SSO Mode: Using inclination {inc:.2f}°")
    else:
        inc = args.inclination

    tles = generate_walker_delta_tles(args.sats, args.planes, inc, args.altitude, args.phasing)
    sats = [EarthSatellite(line1, line2, name, ts) for name, line1, line2 in tles]

    fig, ax = plt.subplots(figsize=(16, 8))

    if args.map:
        coastline_data = load_earth_texture()
        if coastline_data is not None:
            for feature in coastline_data['features']:
                geom = feature['geometry']
                if geom['type'] == 'LineString':
                    coords = geom['coordinates']
                    lons = [c[0] for c in coords]
                    lats = [c[1] for c in coords]
                    ax.plot(lons, lats, 'k-', linewidth=0.5, alpha=0.3, zorder=0)
                elif geom['type'] == 'MultiLineString':
                    for segment in geom['coordinates']:
                        lons = [c[0] for c in segment]
                        lats = [c[1] for c in segment]
                        ax.plot(lons, lats, 'k-', linewidth=0.5, alpha=0.3, zorder=0)

    ax.set_facecolor('#E0F0FF')

    colors = plt.cm.tab20(np.linspace(0, 1, args.planes))

    for idx, sat in enumerate(sats):
        lats, lons = [], []
        for minutes in range(0, args.duration // 60, 2):
            t = ts.utc(t0.utc_datetime() + timedelta(minutes=minutes))
            geo = wgs84.subpoint(sat.at(t))
            lats.append(geo.latitude.degrees)
            lons.append(geo.longitude.degrees)

        plane_idx = idx // (args.sats // args.planes)

        lons_array = np.array(lons)
        lats_array = np.array(lats)

        # Split track at dateline crossings (>180° jump)
        lon_diff = np.diff(lons_array)
        crossing_indices = np.where(np.abs(lon_diff) > 180)[0]

        start_idx = 0
        for cross_idx in crossing_indices:
            ax.plot(lons_array[start_idx:cross_idx+1], lats_array[start_idx:cross_idx+1],
                    color=colors[plane_idx], alpha=0.8, linewidth=1.2, zorder=1)
            start_idx = cross_idx + 1
        ax.plot(lons_array[start_idx:], lats_array[start_idx:],
                color=colors[plane_idx], alpha=0.8, linewidth=1.2, zorder=1)

    ax.set_xlim([-180, 180])
    ax.set_ylim([-90, 90])
    ax.set_xlabel('Longitude (°)')
    ax.set_ylabel('Latitude (°)')
    ax.grid(True, alpha=0.3, zorder=2)

    walker_suffix = f"walker_{int(inc)}_{args.sats}_{args.planes}"
    ax.set_title(f"Ground Tracks | {walker_suffix}")

    if args.save:
        filename = f"track_{walker_suffix}.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"💾 Saved: {filename}")

    plt.tight_layout()

    if matplotlib.get_backend().lower() == 'agg':
        if not args.save:
            print("⚠️  Running with Agg backend (no display). Use --save to export as PNG.")
            print(f"   Example: python satsim_radio.py track --sats {args.sats} --planes {args.planes} "
                  f"--inc {int(inc)} --alt {int(args.altitude)} --save")
        plt.close()
    elif not args.save and not os.environ.get('DISPLAY'):
        print("⚠️  No display available. Use --save to export as PNG.")
        plt.close()
    elif not args.save:
        plt.show()
