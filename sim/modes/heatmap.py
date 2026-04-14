"""
Heatmap mode: vectorized global coverage heatmap generation.
"""

import csv
import numpy as np
from skyfield.api import EarthSatellite, load
from skyfield.framelib import itrs

from ..physics import calculate_sso_inclination
from ..constellation import generate_walker_delta_tles
from ..constants import COMMS_PAYLOADS
from ..plots.heatmap import save_heatmap_plot


def run_heatmap(args):
    """Generate global coverage heatmap with vectorized physics"""
    print(f"🗺️  Generating heatmap (resolution: {args.res}° grid)...")

    ts = load.timescale()
    t0 = ts.utc(2024, 1, 1, 12, 0, 0)

    if args.sso:
        inc = calculate_sso_inclination(args.altitude)
        print(f"🛰️  SSO Mode: Using inclination {inc:.2f}° for {args.altitude}km altitude")
    else:
        inc = args.inclination

    tles = generate_walker_delta_tles(args.sats, args.planes, inc, args.altitude, args.phasing)
    sats = [EarthSatellite(line1, line2, name, ts) for name, line1, line2 in tles]

    lats = np.arange(-90, 91, args.res)
    lons = np.arange(-180, 181, args.res)
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    grid_points = np.column_stack([lat_grid.ravel(), lon_grid.ravel()])

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
    r_sat = R_earth + args.altitude
    min_elev = getattr(args, 'min_elev', 10.0)
    elev_rad = np.radians(min_elev)

    cos_elev = np.cos(elev_rad)
    sin_rho = (R_earth / r_sat) * cos_elev
    sin_rho = np.clip(sin_rho, -1.0, 1.0)
    rho = np.arcsin(sin_rho)
    lambda_angle = np.pi / 2 - elev_rad - rho
    min_cos_angle = np.cos(lambda_angle)

    print(f"🎯 Using minimum elevation: {min_elev}° (cos threshold: {min_cos_angle:.3f}, angle: {np.degrees(lambda_angle):.1f}°)")
    print("⚠️  NOTE: Heatmap shows GEOMETRIC coverage (elevation angle only)")
    print("   For accurate link budget analysis, use 'sky' mode for specific locations")
    print(f"⏱️  Simulating {steps} timesteps over {steps*12} minutes...")

    for t_idx, t in enumerate(times):
        positions = [s.at(t).frame_xyz(itrs).km for s in sats]
        sat_pos = np.column_stack(positions).T

        sat_norm = sat_pos / np.linalg.norm(sat_pos, axis=1)[:, np.newaxis]

        for i in range(0, len(grid_points), chunk_size):
            end = min(i + chunk_size, len(grid_points))
            chunk_obs = obs_vecs[i:end]
            cos_sim = np.dot(chunk_obs, sat_norm.T)
            max_cos = np.max(cos_sim, axis=1)
            visible_mask = max_cos > min_cos_angle
            coverage_counts[i:end] += visible_mask.astype(np.int32)

        if (t_idx + 1) % 10 == 0:
            print(f"  Processed {t_idx + 1}/{steps} timesteps...")

    availability_pct_flat = (coverage_counts / steps) * 100.0
    coverage_grid = availability_pct_flat.reshape(lat_grid.shape)

    walker_suffix = f"walker_{int(inc)}_{args.sats}_{args.planes}"
    csv_filename = f"heatmap_{args.comms}_{walker_suffix}.csv"

    with open(csv_filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['latitude', 'longitude', 'availability_pct', 'wkt_geom'])
        writer.writeheader()
        for (lat, lon), avail in zip(grid_points, availability_pct_flat):
            writer.writerow({
                'latitude': f"{lat:.2f}",
                'longitude': f"{lon:.2f}",
                'availability_pct': f"{avail:.1f}",
                'wkt_geom': f"POINT({lon} {lat})"
            })

    print(f"💾 Saved: {csv_filename} (with WKT geometry for QGIS)")

    img_filename = f"heatmap_{args.comms}_{walker_suffix}.png"
    title = f"Coverage Heatmap | {COMMS_PAYLOADS[args.comms]['desc']} | {walker_suffix}"
    save_heatmap_plot(lat_grid, lon_grid, coverage_grid, img_filename, title,
                      COMMS_PAYLOADS[args.comms]['desc'])
