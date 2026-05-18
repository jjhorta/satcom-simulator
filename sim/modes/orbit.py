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
from ..constellation import (
    generate_walker_delta_tles, calculate_coverage_footprint,
    calculate_constellation_metrics,
    generate_multi_shell_tles, aggregate_constellation_metrics,
)
from ..tco import calculate_tco, print_constellation_dashboard, print_tco_analysis, save_tco_json, print_multi_shell_dashboard
from ..constants import VISUALIZATION_SETTINGS, KNOWN_CONSTELLATIONS
from ..plots.orbit import draw_continents_on_sphere, draw_coverage_circle_on_sphere, create_3d_orbit_plot


def view_orbit(args):
    """3D orbital visualization with animation"""
    import json as _json

    ts = load.timescale()
    t0 = ts.utc(2024, 1, 1, 12, 0, 0)

    # ── Multi-shell path ────────────────────────────────────────────────────
    shells_cfg = None
    if getattr(args, 'constellation', None):
        shells_cfg = KNOWN_CONSTELLATIONS[args.constellation]
        print(f"🌐 Multi-shell preset: '{args.constellation}' ({len(shells_cfg)} shells)")
    elif getattr(args, 'shells', None):
        try:
            shells_cfg = _json.loads(args.shells)
        except Exception as e:
            print(f"❌ --shells JSON parse error: {e}")
            return

    if shells_cfg is not None:
        _view_orbit_multi_shell(args, ts, t0, shells_cfg)
        return

    # ── Single-shell path (original behaviour) ──────────────────────────────
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
    save_tco_json(tco_data, metrics, filename=f"tco_{walker_suffix}")

    tles = generate_walker_delta_tles(args.sats, args.planes, inc, args.altitude, args.phasing)

    # Save TLEs as JSON so the web UI can propagate them client-side
    import json
    tle_payload = {
        "inclination": inc,
        "altitude_km": args.altitude,
        "num_sats": args.sats,
        "num_planes": args.planes,
        "epoch": "2024-01-01T12:00:00Z",
        "tles": [{"name": name, "line1": l1, "line2": l2} for name, l1, l2 in tles],
    }
    with open(f"tles_{walker_suffix}.json", "w") as f:
        json.dump(tle_payload, f, indent=2)

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


# ---------------------------------------------------------------------------
# Multi-shell orbit view
# ---------------------------------------------------------------------------

def _view_orbit_multi_shell(args, ts, t0, shells_cfg):
    """Handle multi-shell constellation visualisation (plotly only)."""
    import json as _json

    min_elev = getattr(args, 'min_elev', 10.0)

    # Normalise shell dicts: support both 'inc' and 'inclination', 'alt' and 'altitude_km'
    normalised = []
    for sh in shells_cfg:
        normalised.append({
            'sats':        sh.get('sats', sh.get('num_sats', 12)),
            'planes':      sh.get('planes', sh.get('num_planes', 3)),
            'inclination': sh.get('inclination', sh.get('inc', 87.0)),
            'altitude_km': sh.get('altitude_km', sh.get('alt', sh.get('altitude', 600.0))),
            'phasing':     sh.get('phasing', 1),
            'name':        sh.get('name'),
        })

    tles, shell_map, shell_meta = generate_multi_shell_tles(normalised)
    agg = aggregate_constellation_metrics(normalised, min_elev)

    total_sats = agg['combined']['total_satellites']
    num_shells = agg['combined']['num_shells']

    # Walker suffix for filenames (must be defined before any use)
    constellation_name = (
        getattr(args, 'constellation_name', None)
        or getattr(args, 'constellation', None)
        or 'custom'
    )
    walker_suffix = f"multi_{constellation_name}_{total_sats}sats"

    print(f"🌐 Multi-shell constellation: {total_sats} satellites across {num_shells} shells")
    for m in shell_meta:
        print(f"   Shell {m['index']+1}: {m['label']} — {m['sats']} sats in {m['planes']} planes @ {m['altitude_km']} km")

    print_multi_shell_dashboard(normalised, agg, filename=f"dashboard_{walker_suffix}")

    # ── TCO for Business Plan ───────────────────────────────────────────────
    # Use the largest shell as the representative for orbital/coverage metrics,
    # then override constellation totals with the aggregate.
    platform_type = getattr(args, 'platform', 'smallsat')
    payload_type  = getattr(args, 'comms', 'ais')
    rep_idx = max(range(len(normalised)), key=lambda i: normalised[i]['sats'])
    rep_metrics = agg['per_shell'][rep_idx]
    combined = agg['combined']
    try:
        tco_data = calculate_tco(
            num_sats=total_sats,
            platform_type=platform_type,
            payload_type=payload_type,
            satellite_lifetime_years=rep_metrics['lifetime']['satellite_lifetime_years'],
            replacement_rate_per_year=rep_metrics['lifetime']['replacement_rate_per_year'],
            mission_duration_years=15,
            num_planes=sum(sh['planes'] for sh in normalised),
            deployment_mode='basic',
        )
        # Build a metrics dict compatible with save_tco_json
        combined_metrics = {
            'orbital': rep_metrics['orbital'],
            'coverage': {
                'min_elevation_deg':    rep_metrics['coverage']['min_elevation_deg'],
                'radius_km':            rep_metrics['coverage']['radius_km'],
                'area_km2':             rep_metrics['coverage']['area_km2'],
                'coverage_per_sat_pct': combined['approx_combined_coverage_pct'] / total_sats,
                'avg_revisit_time_min': combined['best_shell_revisit_min'],
                'max_gap_time_min':     combined['best_shell_revisit_min'],
            },
            'constellation': {
                'total_satellites': total_sats,
                'num_planes':  sum(sh['planes'] for sh in normalised),
                'sats_per_plane': total_sats // max(sum(sh['planes'] for sh in normalised), 1),
                'altitude_km': rep_metrics['constellation']['altitude_km'],
                'inclination_deg': rep_metrics['constellation']['inclination_deg'],
            },
            'lifetime': rep_metrics['lifetime'],
        }
        save_tco_json(tco_data, combined_metrics, filename=f"tco_{walker_suffix}")
        print_tco_analysis(tco_data, filename=f"tco_{walker_suffix}")
    except Exception as _tco_err:
        print(f"⚠️  TCO calculation skipped: {_tco_err}")

    # Build coverage radius per shell
    shell_coverage_radii = {
        m['index']: calculate_coverage_footprint(m['altitude_km'], min_elev)
        for m in shell_meta
    }

    # Save TLEs
    tle_payload = {
        "type": "multi_shell",
        "constellation": constellation_name,
        "total_satellites": total_sats,
        "shells": shell_meta,
        "epoch": "2024-01-01T12:00:00Z",
        "tles": [{"name": name, "line1": l1, "line2": l2} for name, l1, l2 in tles],
    }
    tle_file = f"tles_{walker_suffix}.json"
    with open(tle_file, "w") as f:
        _json.dump(tle_payload, f, indent=2)
    print(f"💾 TLEs saved: {tle_file}")

    sats_obj = [EarthSatellite(line1, line2, name, ts) for name, line1, line2 in tles]

    if backends.GRAPHICS_BACKEND == 'plotly':
        create_3d_orbit_plot(
            sats_obj, args,
            inc=None,           # not used in multi-shell mode
            walker_suffix=walker_suffix,
            metrics=None,
            tco_data=None,
            shell_map=shell_map,
            shell_meta=shell_meta,
            shell_coverage_radii=shell_coverage_radii,
        )
    else:
        print("⚠️  Multi-shell visualisation only supported with --backend plotly.")
        print(f"   Re-run with: --backend plotly")
        print(f"\n📊 Combined metrics:")
        print(f"   Total satellites : {total_sats}")
        print(f"   Shells           : {num_shells}")
        print(f"   Approx coverage  : {agg['combined']['approx_combined_coverage_pct']:.1f}%")
        print(f"   Best revisit     : {agg['combined']['best_shell_revisit_min']:.1f} min")
