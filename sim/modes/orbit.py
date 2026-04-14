"""
Orbit view mode: 3D orbital visualization with matplotlib animation
or plotly interactive HTML export.
"""

import os
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from datetime import timedelta
from skyfield.api import EarthSatellite, load, wgs84

from .. import backends
from ..physics import calculate_sso_inclination
from ..constellation import generate_walker_delta_tles, calculate_coverage_footprint, calculate_constellation_metrics
from ..tco import calculate_tco, print_constellation_dashboard, print_tco_analysis
from ..constants import VISUALIZATION_SETTINGS
from ..plots.orbit import draw_continents_on_sphere, draw_coverage_circle_on_sphere, create_3d_orbit_plot


def view_orbit(args):
    """3D orbital visualization with animation"""
    ts = load.timescale()
    t0 = ts.utc(2024, 1, 1, 12, 0, 0)

    if args.sso:
        inc = calculate_sso_inclination(args.altitude)
        print(f"🛰️  SSO Mode: Using inclination {inc:.2f}°")
    else:
        inc = args.inclination

    min_elev = getattr(args, 'min_elev', 10.0)
    metrics = calculate_constellation_metrics(
        num_sats=args.sats,
        num_planes=args.planes,
        altitude_km=args.altitude,
        inclination_deg=inc,
        min_elev_deg=min_elev
    )

    platform_type = getattr(args, 'platform', 'smallsat')
    payload_type = getattr(args, 'comms', 'vdes')

    tco_data = calculate_tco(
        num_sats=args.sats,
        platform_type=platform_type,
        payload_type=payload_type,
        satellite_lifetime_years=metrics['lifetime']['satellite_lifetime_years'],
        replacement_rate_per_year=metrics['lifetime']['replacement_rate_per_year'],
        mission_duration_years=15,
        num_planes=args.planes,
        deployment_mode='basic'
    )

    walker_suffix = f"walker_{int(inc)}_{args.sats}_{args.planes}"
    print_constellation_dashboard(metrics, tco_data, filename=f"dashboard_{walker_suffix}")
    print_tco_analysis(tco_data, filename=f"tco_{walker_suffix}")

    tles = generate_walker_delta_tles(args.sats, args.planes, inc, args.altitude, args.phasing)
    sats = [EarthSatellite(line1, line2, name, ts) for name, line1, line2 in tles]

    if backends.GRAPHICS_BACKEND == 'plotly':
        create_3d_orbit_plot(sats, args, inc, walker_suffix, metrics, tco_data)
        return

    # --- Matplotlib 3D animation ---
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')

    u, v = np.mgrid[0:2*np.pi:100j, 0:np.pi:50j]
    x = 6378.137 * np.cos(u) * np.sin(v)
    y = 6378.137 * np.sin(u) * np.sin(v)
    z = 6378.137 * np.cos(v)

    ax.plot_surface(x, y, z,
                    color=VISUALIZATION_SETTINGS['earth']['ocean_color'],
                    alpha=VISUALIZATION_SETTINGS['earth']['ocean_alpha'],
                    linewidth=0, antialiased=False, edgecolor='none',
                    rcount=50, ccount=50, shade=False, zorder=-1)

    print(f"🌊 Ocean rendered: color={VISUALIZATION_SETTINGS['earth']['ocean_color']}, "
          f"alpha={VISUALIZATION_SETTINGS['earth']['ocean_alpha']}")

    max_range = args.altitude + 6378.137

    coverage_radius = None
    if args.beams:
        coverage_radius = calculate_coverage_footprint(args.altitude, min_elev)
        print(f"🎯 Coverage: radius={coverage_radius:.1f} km @ {min_elev}°")

    initial_positions = [sat.at(t0).position.km for sat in sats]

    scatters = []
    for pos in initial_positions:
        scatter = ax.scatter(
            [pos[0]], [pos[1]], [pos[2]],
            c=VISUALIZATION_SETTINGS['satellites']['color'],
            s=VISUALIZATION_SETTINGS['satellites']['size'],
            marker='o',
            edgecolors=VISUALIZATION_SETTINGS['satellites']['edge_color'],
            linewidths=VISUALIZATION_SETTINGS['satellites']['edge_width']
        )
        scatters.append(scatter)

    trail_lines = []
    beam_circles = []
    beam_polygons = []
    continent_artists = []
    trail_data = [{'x': [], 'y': [], 'z': []} for _ in sats] if args.trails else None
    rotation_angle = [0.0]

    if args.map:
        print("🌍 Drawing continents...")
        collections_before = len(ax.collections)
        lines_before = len(ax.lines)
        draw_continents_on_sphere(ax, rotation_angle[0])
        continent_artists.extend(ax.collections[collections_before:])
        continent_artists.extend(ax.lines[lines_before:])
        print(f"   Added {len(ax.collections) - collections_before} continent polygons and "
              f"{len(ax.lines) - lines_before} lines")

    print(f"🚀 Starting animation with {len(sats)} satellites...")

    def update(frame):
        nonlocal continent_artists

        try:
            t = ts.utc(t0.utc_datetime() + timedelta(minutes=frame * 2))

            if args.map:
                for artist in continent_artists:
                    try:
                        artist.remove()
                    except (ValueError, AttributeError):
                        pass
                continent_artists = []

                collections_before = len(ax.collections)
                lines_before = len(ax.lines)
                rotation_angle[0] = frame * 0.5
                draw_continents_on_sphere(ax, rotation_angle[0])
                continent_artists.extend(ax.collections[collections_before:])
                continent_artists.extend(ax.lines[lines_before:])

            for scatter in scatters:
                scatter.remove()
            scatters.clear()

            for idx, sat in enumerate(sats):
                pos = sat.at(t).position.km
                scatter = ax.scatter(
                    [pos[0]], [pos[1]], [pos[2]],
                    c=VISUALIZATION_SETTINGS['satellites']['color'],
                    s=VISUALIZATION_SETTINGS['satellites']['size'],
                    marker='o',
                    edgecolors=VISUALIZATION_SETTINGS['satellites']['edge_color'],
                    linewidths=VISUALIZATION_SETTINGS['satellites']['edge_width']
                )
                scatters.append(scatter)

                if trail_data:
                    trail_data[idx]['x'].append(pos[0])
                    trail_data[idx]['y'].append(pos[1])
                    trail_data[idx]['z'].append(pos[2])
                    if len(trail_data[idx]['x']) > 50:
                        trail_data[idx]['x'].pop(0)
                        trail_data[idx]['y'].pop(0)
                        trail_data[idx]['z'].pop(0)

            for line in trail_lines:
                line.remove()
            trail_lines.clear()

            if trail_data:
                for idx in range(len(sats)):
                    if len(trail_data[idx]['x']) > 1:
                        line, = ax.plot(
                            trail_data[idx]['x'], trail_data[idx]['y'], trail_data[idx]['z'],
                            color=VISUALIZATION_SETTINGS['trails']['orbit_color'],
                            alpha=VISUALIZATION_SETTINGS['trails']['orbit_alpha'],
                            linewidth=VISUALIZATION_SETTINGS['trails']['orbit_width']
                        )
                        trail_lines.append(line)

            for circle in beam_circles:
                circle.remove()
            beam_circles.clear()
            for poly in beam_polygons:
                poly.remove()
            beam_polygons.clear()

            if args.beams and coverage_radius:
                for sat in sats:
                    geo = wgs84.subpoint(sat.at(t))
                    circle, poly = draw_coverage_circle_on_sphere(
                        ax, geo.latitude.degrees, geo.longitude.degrees, coverage_radius
                    )
                    beam_circles.append(circle)
                    beam_polygons.append(poly)

            ax.set_title(f"Orbital View | {walker_suffix} | T+{frame*2} min")
            return scatters

        except Exception as e:
            import traceback
            print(f"❌ Error in frame {frame}: {e}")
            traceback.print_exc()
            return scatters

    ax.set_xlabel('X (km)')
    ax.set_ylabel('Y (km)')
    ax.set_zlabel('Z (km)')
    ax.set_xlim([-max_range, max_range])
    ax.set_ylim([-max_range, max_range])
    ax.set_zlim([-max_range, max_range])

    frames = args.duration // 2
    duration_hours = args.duration / 60
    print(f"ℹ️  Rendering {frames} frames ({duration_hours:.1f} hours simulation)")

    anim = FuncAnimation(fig, update, frames=frames, interval=50, blit=False)

    if args.save:
        filename = f"orbit_{walker_suffix}.gif"
        writer = PillowWriter(fps=10)
        print(f"💾 Saving animation to {filename} ({frames} frames)...")

        def progress_callback(current_frame, total_frames):
            if current_frame % 5 == 0 or current_frame == total_frames - 1:
                pct = (current_frame + 1) / total_frames * 100
                print(f"   Progress: {current_frame + 1}/{total_frames} ({pct:.0f}%)")

        anim.save(filename, writer=writer, progress_callback=progress_callback)
        print(f"✅ Saved: {filename}")
        plt.close()
    else:
        if matplotlib.get_backend().lower() == 'agg':
            print("⚠️  Running with Agg backend (no display). Use --save to export as GIF.")
            print(f"   Example: python satsim_radio.py orbit --sats {args.sats} --planes {args.planes} "
                  f"--inc {int(inc)} --alt {int(args.altitude)} --beams --save")
            plt.close()
        elif not os.environ.get('DISPLAY'):
            print("⚠️  No display available. Use --save to export as GIF.")
            plt.close()
        else:
            plt.show()
