"""
Sky view mode: observer-centric animated sky plot and batch coverage analysis.
"""

import csv
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from datetime import timedelta
from skyfield.api import EarthSatellite, load, wgs84

from ..physics import calculate_sso_inclination, calculate_generic_link
from ..constellation import generate_walker_delta_tles, generate_multi_shell_tles
from ..constants import (COMMS_PAYLOADS, LOCATIONS, SEA_ROUTES, ARCTIC_ROUTES,
                          VISUALIZATION_SETTINGS, KNOWN_CONSTELLATIONS)


def view_sky(args):
    """Observer-centric sky view with animated dashboard"""
    import json as _json
    ts = load.timescale()
    t0 = ts.utc(2024, 1, 1, 12, 0, 0)

    loc_name = args.location
    if loc_name in LOCATIONS:
        lat, lon = LOCATIONS[loc_name]
    else:
        try:
            lat, lon = map(float, loc_name.split(','))
        except Exception:
            print(f"❌ Unknown location: {loc_name}")
            return

    observer = wgs84.latlon(lat, lon)

    # ── Multi-shell path ────────────────────────────────────────────────────
    shells_cfg = None
    if getattr(args, 'constellation', None):
        shells_cfg = KNOWN_CONSTELLATIONS[args.constellation]
    elif getattr(args, 'shells', None):
        try:
            shells_cfg = _json.loads(args.shells)
        except Exception as e:
            print(f"❌ --shells JSON parse error: {e}")
            return

    if shells_cfg is not None:
        normalised = []
        for sh in shells_cfg:
            normalised.append({
                'sats':        sh.get('sats', sh.get('num_sats', 12)),
                'planes':      sh.get('planes', sh.get('num_planes', 3)),
                'inclination': sh.get('inclination', sh.get('inc', 87.0)),
                'altitude_km': sh.get('altitude_km', sh.get('alt', sh.get('altitude', 600.0))),
                'phasing':     sh.get('phasing', 1),
            })
        tles_multi, _shell_map, _shell_meta = generate_multi_shell_tles(normalised)
        max_sats = getattr(args, 'max_sats', 250)
        tles_multi = tles_multi[:max_sats]
        tles = tles_multi
        total_sats = sum(sh['sats'] for sh in normalised)
        constellation_name = (
            getattr(args, 'constellation_name', None)
            or getattr(args, 'constellation', None)
            or 'custom'
        )
        print(f"🌐 Multi-shell sky view: {len(tles)} of {total_sats} sats ({constellation_name})")
    else:
        if args.sso:
            inc = calculate_sso_inclination(args.altitude)
            print(f"🛰️  SSO Mode: Using inclination {inc:.2f}°")
        else:
            inc = args.inclination
        tles = generate_walker_delta_tles(args.sats, args.planes, inc, args.altitude, args.phasing)

    sats = [EarthSatellite(line1, line2, name, ts) for name, line1, line2 in tles]

    p = COMMS_PAYLOADS[args.comms]
    min_elev = getattr(args, 'min_elev', 10.0)
    no_display = getattr(args, 'no_display', False)

    if no_display:
        # Headless: compute connectivity without animation
        connectivity_frames = []
        frames = args.duration // args.speed

        for frame in range(frames):
            t = ts.utc(t0.utc_datetime() + timedelta(seconds=frame * args.speed))
            has_connection = False

            for sat in sats:
                topo = (sat - observer).at(t)
                alt, az, dist = topo.altaz()

                if alt.degrees > min_elev:
                    dl_margin, _, _ = calculate_generic_link(
                        dist.km, alt.degrees, p['dl_freq'], p['bw'],
                        p['sat_p_tx'], p['sat_g_tx'], p['gnd_g_rx'], p['gnd_nf'],
                        p['req_snr_dl'], args.weather
                    )
                    if args.bidi:
                        ul_margin, _, _ = calculate_generic_link(
                            dist.km, alt.degrees, p['ul_freq'], p['bw'],
                            p['gnd_p_tx'], p['gnd_g_tx'], p['sat_g_rx'], p['sat_nf'],
                            p['req_snr_ul'], args.weather
                        )
                        connected = (dl_margin >= 0) and (ul_margin >= 0)
                    else:
                        connected = dl_margin >= 0

                    if connected:
                        has_connection = True
                        break

            connectivity_frames.append(has_connection)

        final_connectivity = (sum(connectivity_frames) / len(connectivity_frames)) * 100.0 if connectivity_frames else 0.0
        return {'location': loc_name, 'latitude': lat, 'longitude': lon,
                'connectivity_pct': final_connectivity}

    # Interactive animated sky view
    fig = plt.figure(figsize=(12, 8))
    gs = fig.add_gridspec(2, 1, height_ratios=[4, 1], hspace=0.3)

    ax = fig.add_subplot(gs[0], projection='polar')
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_rlim(90, 0)
    ax.set_yticks([0, 30, 60, 90])
    ax.set_yticklabels(['Horizon', '30°', '60°', 'Zenith'])

    ax_info = fig.add_subplot(gs[1])
    ax_info.axis('off')

    scat = ax.scatter([], [], c=[], cmap='RdYlGn', vmin=0, vmax=20, s=80, edgecolors='black')

    trail_lines = []
    trail_data = {} if args.trails else None
    connectivity_frames = []

    def update(frame):
        t = ts.utc(t0.utc_datetime() + timedelta(seconds=frame * args.speed))

        visible_azs, visible_alts, visible_margins = [], [], []
        visible_data = []
        has_connection = False

        for sat in sats:
            topo = (sat - observer).at(t)
            alt, az, dist = topo.altaz()

            if alt.degrees > 0:
                az_rad = np.radians(az.degrees)
                dist_km = dist.km

                dl_margin, dl_snr, _ = calculate_generic_link(
                    dist_km, alt.degrees, p['dl_freq'], p['bw'],
                    p['sat_p_tx'], p['sat_g_tx'], p['gnd_g_rx'], p['gnd_nf'],
                    p['req_snr_dl'], args.weather
                )

                if args.bidi:
                    ul_margin, ul_snr, _ = calculate_generic_link(
                        dist_km, alt.degrees, p['ul_freq'], p['bw'],
                        p['gnd_p_tx'], p['gnd_g_tx'], p['sat_g_rx'], p['sat_nf'],
                        p['req_snr_ul'], args.weather
                    )
                    connected = (dl_margin >= 0) and (ul_margin >= 0)
                    margin = min(dl_margin, ul_margin)
                else:
                    ul_margin, ul_snr = None, None
                    connected = dl_margin >= 0
                    margin = dl_margin

                visible_data.append({
                    'name': sat.name, 'dl_mar': dl_margin, 'dl_snr': dl_snr,
                    'ul_mar': ul_margin, 'ul_snr': ul_snr, 'connected': connected
                })
                visible_azs.append(az_rad)
                visible_alts.append(alt.degrees)
                visible_margins.append(margin)

                if trail_data is not None:
                    if sat.name not in trail_data:
                        trail_data[sat.name] = {'az': [], 'alt': []}
                    trail_data[sat.name]['az'].append(az_rad)
                    trail_data[sat.name]['alt'].append(alt.degrees)
                    if len(trail_data[sat.name]['az']) > 30:
                        trail_data[sat.name]['az'].pop(0)
                        trail_data[sat.name]['alt'].pop(0)

                if connected:
                    has_connection = True

        connectivity_frames.append(has_connection)

        if visible_azs:
            scat.set_offsets(np.c_[visible_azs, visible_alts])
            scat.set_array(np.array(visible_margins))
        else:
            scat.set_offsets(np.empty((0, 2)))

        for line in trail_lines:
            line.remove()
        trail_lines.clear()

        if trail_data:
            for data in trail_data.values():
                if len(data['az']) > 1:
                    line, = ax.plot(data['az'], data['alt'],
                                    color=VISUALIZATION_SETTINGS['trails']['sky_color'],
                                    alpha=VISUALIZATION_SETTINGS['trails']['sky_alpha'],
                                    linewidth=VISUALIZATION_SETTINGS['trails']['sky_width'])
                    trail_lines.append(line)

        connectivity_pct = (sum(connectivity_frames) / len(connectivity_frames)) * 100.0

        if args.bidi:
            visible_data.sort(key=lambda x: min(x['dl_mar'], x['ul_mar']) if x['ul_mar'] is not None else x['dl_mar'], reverse=True)
        else:
            visible_data.sort(key=lambda x: x['dl_mar'], reverse=True)
        top_sats = visible_data[:3]

        ax_info.clear()
        ax_info.axis('off')
        walker_suffix = f"walker_{int(inc)}_{args.sats}_{args.planes}"

        ax_info.text(0.02, 0.95,
                     f"SERVICE: {p['desc']} ({p['mod']}) | WEATHER: {args.weather.upper()} | Connectivity: {connectivity_pct:.1f}%",
                     fontsize=11, weight='bold', family='monospace')

        y_pos = 0.75
        ax_info.text(0.02, y_pos, "SAT ID", fontsize=10, weight='bold', family='monospace')
        ax_info.text(0.20, y_pos, "DOWNLINK (Rx Ground)", fontsize=10, weight='bold', color='blue', family='monospace')
        if args.bidi:
            ax_info.text(0.55, y_pos, "UPLINK (Rx Space)", fontsize=10, weight='bold', color='red', family='monospace')
        ax_info.text(0.85, y_pos, "STATUS", fontsize=10, weight='bold', family='monospace')
        y_pos -= 0.15

        if not top_sats:
            ax_info.text(0.02, y_pos, "NO SATELLITES IN VIEW", family='monospace')
        else:
            for s in top_sats:
                c_dl = 'green' if s['dl_mar'] >= 0 else 'red'
                icon = "[LINK OK]" if s['connected'] else "[BROKEN]"
                ax_info.text(0.02, y_pos, f"{s['name']}", family='monospace', fontsize=10)
                ax_info.text(0.20, y_pos, f"SNR:{s['dl_snr']:4.1f}dB | Mar:{s['dl_mar']:+5.1f}dB",
                             family='monospace', fontsize=10, color=c_dl)
                if args.bidi:
                    c_ul = 'green' if s['ul_mar'] >= 0 else 'red'
                    ax_info.text(0.55, y_pos, f"SNR:{s['ul_snr']:4.1f}dB | Mar:{s['ul_mar']:+5.1f}dB",
                                 family='monospace', fontsize=10, color=c_ul)
                ax_info.text(0.85, y_pos, f"{icon}", family='monospace', fontsize=10, weight='bold')
                y_pos -= 0.15

        ax.set_title(f"Sky View: {loc_name.upper()} | {walker_suffix} | T+{frame * args.speed // 60:.0f} min", pad=20)
        return scat,

    frames = args.duration // args.speed
    anim = FuncAnimation(fig, update, frames=frames, interval=50, blit=False)

    if args.save:
        walker_suffix = f"walker_{int(inc)}_{args.sats}_{args.planes}"
        gif_filename = f"sky_{loc_name}_{args.comms}_{walker_suffix}.gif"
        writer = PillowWriter(fps=10)
        anim.save(gif_filename, writer=writer)
        print(f"💾 Saved: {gif_filename}")

    if matplotlib.get_backend().lower() != 'agg':
        plt.show()
    else:
        plt.close()

    final_connectivity = (sum(connectivity_frames) / len(connectivity_frames)) * 100.0 if connectivity_frames else 0.0
    return {'location': loc_name, 'latitude': lat, 'longitude': lon,
            'connectivity_pct': final_connectivity}


def run_coverage(args):
    """Batch coverage analysis across multiple locations with CSV export"""
    locations_to_test = {}

    if args.coverage == '':
        locations_to_test = LOCATIONS
        csv_suffix = "locations"
    elif args.coverage == 'sea':
        for route_name, waypoints in SEA_ROUTES.items():
            for wp_name, lat, lon in waypoints:
                locations_to_test[wp_name] = (lat, lon)
        csv_suffix = "sea_routes"
    elif args.coverage == 'arctic':
        for route_name, waypoints in ARCTIC_ROUTES.items():
            for wp_name, lat, lon in waypoints:
                locations_to_test[wp_name] = (lat, lon)
        csv_suffix = "arctic_routes"
    elif args.coverage == 'both':
        locations_to_test = LOCATIONS.copy()
        for route_name, waypoints in SEA_ROUTES.items():
            for wp_name, lat, lon in waypoints:
                locations_to_test[wp_name] = (lat, lon)
        csv_suffix = "locations_sea"
    elif args.coverage == 'all':
        locations_to_test = LOCATIONS.copy()
        for route_name, waypoints in SEA_ROUTES.items():
            for wp_name, lat, lon in waypoints:
                locations_to_test[wp_name] = (lat, lon)
        for route_name, waypoints in ARCTIC_ROUTES.items():
            for wp_name, lat, lon in waypoints:
                locations_to_test[wp_name] = (lat, lon)
        csv_suffix = "all_locations"

    print(f"📊 Coverage Analysis: {len(locations_to_test)} locations")

    inc = calculate_sso_inclination(args.altitude) if args.sso else args.inclination
    walker_suffix = f"walker_{int(inc)}_{args.sats}_{args.planes}"
    csv_filename = f"coverage_{csv_suffix}_{args.comms}_{walker_suffix}.csv"

    with open(csv_filename, 'w', newline='') as csvfile:
        fieldnames = ['location', 'latitude', 'longitude', 'connectivity_pct', 'wkt_geom']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

    print(f"💾 Writing results to: {csv_filename}")

    if not hasattr(args, 'no_display'):
        args.no_display = True

    for idx, (loc_name, (lat, lon)) in enumerate(locations_to_test.items(), 1):
        print(f"\n[{idx}/{len(locations_to_test)}] Testing: {loc_name}")
        args.location = loc_name
        result = view_sky(args)

        with open(csv_filename, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['location', 'latitude', 'longitude', 'connectivity_pct', 'wkt_geom'])
            writer.writerow({
                'location': result['location'],
                'latitude': f"{result['latitude']:.4f}",
                'longitude': f"{result['longitude']:.4f}",
                'connectivity_pct': f"{result['connectivity_pct']:.1f}",
                'wkt_geom': f"POINT({result['longitude']} {result['latitude']})"
            })

        print(f"✅ {loc_name}: {result['connectivity_pct']:.1f}% connectivity")


    # ── GeoJSON + QGIS style export ───────────────────────────────────────
    geojson_filename = f"coverage_{csv_suffix}_{args.comms}_{walker_suffix}.geojson"
    from ..exports.geojson import write_coverage_geojson
    from ..exports.qml import write_qml
    # Reconstruct results list (view_sky returns one at a time)
    if 'locations_to_test' in dir():
        coverage_results = []
        # Results were printed line by line; we need to rebuild from the appended CSV
        # Parse the CSV we just wrote
        import csv as _csv
        with open(csv_filename, 'r') as _f:
            _reader = _csv.DictReader(_f)
            for _row in _reader:
                coverage_results.append({
                    'location': _row['location'],
                    'latitude': float(_row['latitude']),
                    'longitude': float(_row['longitude']),
                    'connectivity_pct': float(_row['connectivity_pct']),
                })
        write_coverage_geojson(coverage_results, geojson_filename, csv_suffix)
        write_qml(geojson_filename, "coverage")

    print(f"\n🎉 Coverage analysis complete! Results saved to: {csv_filename}")
