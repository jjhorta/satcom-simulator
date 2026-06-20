"""
Heatmap-RF mode: global RF link budget availability heatmap.

Like the geometric heatmap but evaluates the full RF link budget
(FSPL + rain attenuation + noise) at each grid point and counts
the fraction of time the link budget actually closes (margin > 0 dB).

Output metric: % of simulation time where:
  1. A satellite is geometrically visible (elevation >= min_elev), AND
  2. The downlink RF link budget closes (SNR margin >= 0 dB)

This produces a more realistic coverage map for high-frequency payloads
(GSM/LTE/5G/Ku-band) where path loss and rain attenuation are significant.
For VHF payloads (AIS/VDES) the result will closely match the geometric heatmap.
"""

import csv
import json as _json
import numpy as np
from skyfield.api import EarthSatellite, load
from skyfield.framelib import itrs

from ..physics import PhysicsEngine, calculate_sso_inclination
from ..constellation import generate_walker_delta_tles, generate_multi_shell_tles
from ..constants import COMMS_PAYLOADS, KNOWN_CONSTELLATIONS
from ..plots.heatmap import save_heatmap_plot


def run_heatmap_rf(args):
    """Generate global RF link budget availability heatmap (vectorized)"""
    print(f"📡 Generating RF link budget heatmap (resolution: {args.res}° grid)...")
    print(f"   Payload: {args.comms} ({COMMS_PAYLOADS[args.comms]['desc']}) | Weather: {args.weather}")

    engine = PhysicsEngine(args.comms, args.weather)

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
        constellation_name = (
            getattr(args, 'constellation_name', None)
            or getattr(args, 'constellation', None)
            or 'custom'
        )
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
        total_sats = sum(sh['sats'] for sh in normalised)
        sats_list = [EarthSatellite(l1, l2, n, ts) for n, l1, l2 in tles_multi]
        walker_suffix = f"multi_{constellation_name}_{total_sats}sats"
        print(f"🌐 Multi-shell: {len(sats_list)} sats across {len(normalised)} shells (rendering {len(sats_list)} of {total_sats})")
    else:
        # ── Single-shell path ───────────────────────────────────────────────
        if args.sso:
            inc = calculate_sso_inclination(args.altitude)
            print(f"🛰️  SSO Mode: Using inclination {inc:.2f}° for {args.altitude}km altitude")
        else:
            inc = args.inclination
        tles_single = generate_walker_delta_tles(args.sats, args.planes, inc, args.altitude, args.phasing)
        sats_list = [EarthSatellite(l1, l2, n, ts) for n, l1, l2 in tles_single]
        walker_suffix = f"walker_{int(inc)}_{args.sats}_{args.planes}"

    # ── Grid generation (latlon or h3) ────────────────
    grid_mode = getattr(args, 'grid', 'latlon')
    h3_res = getattr(args, 'h3_res', 4)
    if grid_mode == 'h3':
        from sim.grid import generate_grid
        h3_cells = generate_grid('h3', h3_res=h3_res)
        grid_points = np.array([[c['lat'], c['lon']] for c in h3_cells])
        print(f"📊 H3 Grid: {len(grid_points)} cells at res {h3_res}")
        lats = np.unique(grid_points[:, 0])
        lons = np.unique(grid_points[:, 1])
        lon_grid, lat_grid = np.meshgrid(lons, lats)
    else:
        lats = np.arange(-90, 91, args.res)
        lons = np.arange(-180, 181, args.res)
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        grid_points = np.column_stack([lat_grid.ravel(), lon_grid.ravel()])
        print(f"📊 Grid: {len(grid_points)} points at {args.res}° resolution")

    print(f"📊 Grid: {len(grid_points)} points")

    steps = 60
    times = [ts.utc(t0.utc.year, t0.utc.month, t0.utc.day,
                    t0.utc.hour, t0.utc.minute + i * 12) for i in range(steps)]

    lat_rad = np.radians(grid_points[:, 0])
    lon_rad = np.radians(grid_points[:, 1])
    obs_x = np.cos(lat_rad) * np.cos(lon_rad)
    obs_y = np.cos(lat_rad) * np.sin(lon_rad)
    obs_z = np.sin(lat_rad)
    obs_vecs = np.stack((obs_x, obs_y, obs_z), axis=1)

    coverage_counts = np.zeros(len(grid_points), dtype=np.int32)
    chunk_size = 5000

    R_earth = 6378.137
    if shells_cfg is not None:
        avg_altitude = sum(sh['altitude_km'] for sh in normalised) / len(normalised)
    else:
        avg_altitude = args.altitude
    r_sat = R_earth + avg_altitude

    min_elev = getattr(args, 'min_elev', 10.0)
    elev_rad = np.radians(min_elev)

    # Geometric visibility threshold (same as regular heatmap)
    cos_elev = np.cos(elev_rad)
    sin_rho = (R_earth / r_sat) * cos_elev
    sin_rho = np.clip(sin_rho, -1.0, 1.0)
    rho = np.arcsin(sin_rho)
    lambda_angle = np.pi / 2 - elev_rad - rho
    min_cos_angle = np.cos(lambda_angle)

    payload = COMMS_PAYLOADS[args.comms]
    print(f"🎯 Min elevation: {min_elev}° | DL freq: {payload['dl_freq']} MHz | BW: {payload['bw']/1e3:.0f} kHz")
    print(f"   Sat TX: {10*np.log10(payload['sat_p_tx']*1000):.1f} dBm + G_tx: {payload['sat_g_tx']} dBi → Gnd G_rx: {payload['gnd_g_rx']} dBi | Req SNR: {payload['req_snr_dl']} dB")
    print(f"⏱️  Simulating {steps} timesteps over {steps*12} minutes...")

    for t_idx, t in enumerate(times):
        positions = [s.at(t).frame_xyz(itrs).km for s in sats_list]
        sat_pos = np.column_stack(positions).T

        sat_norm = sat_pos / np.linalg.norm(sat_pos, axis=1)[:, np.newaxis]

        if args.gateways:
            gw_pairs = [tuple(float(x) for x in g.split(',')) for g in args.gateways.split(';')]
            gw_cart = np.zeros((len(gw_pairs), 3))
            for gi, (glat, glon) in enumerate(gw_pairs):
                glat_r, glon_r = np.radians(glat), np.radians(glon)
                gw_cart[gi] = [np.cos(glat_r)*np.cos(glon_r),
                               np.cos(glat_r)*np.sin(glon_r),
                               np.sin(glat_r)]
            gw_sees_sat = np.zeros(sat_norm.shape[0], dtype=bool)
            for si in range(sat_norm.shape[0]):
                for gi in range(len(gw_pairs)):
                    cos_angle = np.dot(sat_norm[si], gw_cart[gi])
                    elev = 90.0 - np.degrees(np.arccos(cos_angle))
                    if elev > 5.0:
                        gw_sees_sat[si] = True
                        break
        else:
            gw_sees_sat = np.ones(sat_norm.shape[0], dtype=bool)

        for i in range(0, len(grid_points), chunk_size):
            end = min(i + chunk_size, len(grid_points))
            chunk_obs = obs_vecs[i:end]

            cos_sim = np.dot(chunk_obs, sat_norm.T)
            max_cos = np.max(cos_sim, axis=1)

            # Geometric visibility gate
            visible_mask = max_cos > min_cos_angle

            # Slant range (km) and elevation angle to best satellite
            nadir_rad = np.arccos(np.clip(max_cos, -1.0, 1.0))
            dist_km = np.sqrt(
                r_sat**2 + R_earth**2 - 2.0 * r_sat * R_earth * np.cos(nadir_rad)
            )
            elev_deg = np.degrees(np.arcsin(np.clip(
                (r_sat * np.cos(nadir_rad) - R_earth) / dist_km, -1.0, 1.0
            )))

            # Full RF link budget — vectorized
            margin, _, _ = engine.link_budget(dist_km, elev_deg)

            # Link closes: geometrically visible AND positive SNR margin
            rf_mask = visible_mask & (margin > 0)
            coverage_counts[i:end] += rf_mask.astype(np.int32)

        if (t_idx + 1) % 10 == 0:
            print(f"  Processed {t_idx + 1}/{steps} timesteps...")

    availability_pct_flat = (coverage_counts / steps) * 100.0
    coverage_grid = availability_pct_flat.reshape(lat_grid.shape)

    # ── CSV output ─────────────────────────────────────────────────────────
    csv_filename = f"heatmap_rf_{args.comms}_{walker_suffix}.csv"
    with open(csv_filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=['latitude', 'longitude', 'availability_pct', 'rf_availability_pct', 'wkt_geom'],
        )
        writer.writeheader()
        for (lat, lon), avail in zip(grid_points, availability_pct_flat):
            writer.writerow({
                'latitude':             f"{lat:.2f}",
                'longitude':            f"{lon:.2f}",
                'availability_pct':     f"{avail:.1f}",   # HeatmapViewer key
                'rf_availability_pct':  f"{avail:.1f}",   # descriptive alias
                'wkt_geom':             f"POINT({lon} {lat})",
            })

    print(f"💾 Saved: {csv_filename} (with WKT geometry for QGIS)")

    # ── Image output ────────────────────────────────────────────────────────
    img_filename = f"heatmap_rf_{args.comms}_{walker_suffix}.png"
    title = (
        f"RF Link Budget Heatmap | {COMMS_PAYLOADS[args.comms]['desc']} | "
        f"{walker_suffix} | weather: {args.weather}"
    )
    save_heatmap_plot(lat_grid, lon_grid, coverage_grid, img_filename, title,
                      COMMS_PAYLOADS[args.comms]['desc'])
