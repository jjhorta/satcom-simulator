"""
Throughput mode: compute IP throughput across all beams for a time-series.

Produces a CSV with columns:
    timestamp, lat, lon, sat_id, beam_id, ip_throughput_mbps, snr_db, margin_db
"""

import csv
import json as _json
import numpy as np
from skyfield.api import EarthSatellite, load
from skyfield.framelib import itrs

from ..physics import PhysicsEngine
from ..constellation import generate_walker_delta_tles, generate_multi_shell_tles
from ..constants import COMMS_PAYLOADS, KNOWN_CONSTELLATIONS
from ..throughput import compute_beam_throughput


def run_throughput(args):
    """Generate time-series of IP throughput across all beams."""
    print(f"⚡ Generating throughput snapshot (resolution: {getattr(args, 'res', 5.0)} deg)...")
    if hasattr(args, 'comms') and args.comms:
        print(f"   Payload: {args.comms} ({COMMS_PAYLOADS.get(args.comms, {}).get('desc', 'N/A')})")
    print(f"   Constellation: {getattr(args, 'sats', 66)} sats, {getattr(args, 'planes', 6)} planes, "
          f"{getattr(args, 'altitude', 600)} km")

    engine = PhysicsEngine(getattr(args, 'comms', 'vdes'), getattr(args, 'weather', 'clear'))

    ts = load.timescale()
    t0 = ts.utc(2024, 1, 1, 12, 0, 0)

    # ── Multi-shell path ────────────────────────────────────────
    shells_cfg = None
    constellation_name = 'custom'
    if getattr(args, 'constellation', None):
        shells_cfg = KNOWN_CONSTELLATIONS[args.constellation]
        constellation_name = args.constellation
        print(f"   Multi-shell preset: '{args.constellation}' ({len(shells_cfg)} shells)")
    elif getattr(args, 'shells', None):
        try:
            shells_cfg = _json.loads(args.shells)
        except Exception as e:
            print(f"   --shells JSON parse error: {e}")
            return

    if shells_cfg is not None:
        constellation_name = getattr(args, 'constellation_name', None) or constellation_name
        normalised = []
        for sh in shells_cfg:
            normalised.append({
                'sats': sh.get('sats', sh.get('num_sats', 12)),
                'planes': sh.get('planes', sh.get('num_planes', 3)),
                'inclination': sh.get('inclination', sh.get('inc', 87.0)),
                'altitude_km': sh.get('altitude_km', sh.get('alt', sh.get('altitude', 600.0))),
                'phasing': sh.get('phasing', 1),
            })
        tles = generate_multi_shell_tles(normalised, name_prefix=constellation_name.replace(' ', '_'))
    else:
        tles = generate_walker_delta_tles(
            getattr(args, 'sats', 66),
            getattr(args, 'planes', 6),
            getattr(args, 'inclination', 87.4),
            getattr(args, 'altitude', 600.0),
            getattr(args, 'phasing', 1),
        )

    n_sats = sum(len(t) for t in tles.values()) if isinstance(tles, dict) else len(tles)
    print(f"   Satellites in simulation: {n_sats}")

    # Build EarthSatellite list
    if isinstance(tles, dict):
        satellites = []
        for shell_name, shell_tles in tles.items():
            for name, line1, line2 in shell_tles:
                try:
                    satellites.append(EarthSatellite(line1, line2, name, ts))
                except Exception as e:
                    print(f"   Skipping {name}: {e}")
    else:
        satellites = []
        for name, line1, line2 in tles:
            try:
                satellites.append(EarthSatellite(line1, line2, name, ts))
            except Exception as e:
                print(f"   Skipping {name}: {e}")

    if not satellites:
        print("   No valid satellites to simulate.")
        return

    # ── Runtime parameters ──────────────────────────────────────
    duration_min = getattr(args, 'duration', 60)
    step_min = getattr(args, 'step', 10)
    min_elev = getattr(args, 'min_elev', 10.0)
    res = getattr(args, 'res', 5.0)
    max_sats = getattr(args, 'max_sats', 250)

    # Limit satellites for performance
    satellites = satellites[:max_sats]
    n_sats = len(satellites)

    # Build ground grid
    lats = np.arange(-90 + res / 2, 90, res)
    lons = np.arange(-180 + res / 2, 180, res)
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    grid_points = np.column_stack([lat_grid.ravel(), lon_grid.ravel()])
    n_grid = len(grid_points)
    print(f"   Ground grid: {len(lats)} lat x {len(lons)} lon = {n_grid} points")
    # ── Shape filter (optional) ──────────────────────────────
    shape_path = getattr(args, 'shape', None)
    if shape_path:
        from ..grid import load_shape_geojson, filter_grid_by_shape
        shape_data = load_shape_geojson(shape_path)
        if shape_data:
            grid_points = [{"lat": float(p[0]), "lon": float(p[1])} for p in grid_points]
            grid_points = filter_grid_by_shape(grid_points, shape_data)
            if len(grid_points) == 0:
                print("  No grid points inside shape. Nothing to simulate.")
                return
            # Convert back to numpy for downstream computation
            grid_points = np.array([[p["lat"], p["lon"]] for p in grid_points])
            # Rebuild meshgrid if needed
            lats = np.unique(grid_points[:, 0])
            lons = np.unique(grid_points[:, 1])
            lon_grid, lat_grid = np.meshgrid(lons, lats)
    

    # Times
    timesteps = range(0, duration_min, step_min)
    n_t = len(timesteps)
    print(f"   Duration: {duration_min} min, step: {step_min} min, {n_t} snapshots")

    # Payload parameters
    payload_key = getattr(args, 'comms', 'vdes')
    payload = COMMS_PAYLOADS.get(payload_key, {})
    eirp_dbw = float(payload.get('eirp_dbw', 40))
    bandwidth_hz = float(payload.get('bandwidth', 25e3))
    frequency_hz = float(payload.get('frequency', 162e6))

    # ── Simulation loop ─────────────────────────────────────────
    output_path = f"throughput_{constellation_name}_{duration_min}min.csv"
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'timestamp_min', 'lat', 'lon', 'sat_id', 'sat_name',
            'ip_throughput_mbps', 'snr_db', 'margin_db', 'slant_range_km'
        ])

        total_links = 0
        closed_links = 0

        for t_idx, t_min in enumerate(timesteps):
            t = ts.utc(2024, 1, 1, 12, t_min, 0)
            if t_idx % max(1, n_t // 10) == 0:
                print(f"   Processing t={t_min} min ({t_idx + 1}/{n_t})...")

            # Get satellite positions in geocentric (ITRS)
            geocentric = [sat.at(t) for sat in satellites]
            positions = [g.position.km for g in geocentric]

            for sat_idx, pos in enumerate(positions):
                sat_x, sat_y, sat_z = pos
                sat_lat = np.degrees(np.arcsin(sat_z / np.linalg.norm(pos)))
                sat_lon = np.degrees(np.arctan2(sat_y, sat_x))

                # Altitude above Earth surface
                sat_alt_km = np.linalg.norm(pos) - 6378.137

                for gp_idx in range(0, n_grid, 1000):  # batch grid points
                    batch_end = min(gp_idx + 1000, n_grid)
                    batch_lats = grid_points[gp_idx:batch_end, 0]
                    batch_lons = grid_points[gp_idx:batch_end, 1]

                    # Great-circle distance approximation
                    d_lat = np.radians(batch_lats - sat_lat)
                    d_lon = np.radians(batch_lons - sat_lon)
                    a = np.sin(d_lat / 2) ** 2 + np.cos(np.radians(sat_lat)) * np.cos(
                        np.radians(batch_lats)
                    ) * np.sin(d_lon / 2) ** 2
                    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
                    ground_dist_km = 6378.137 * c

                    # Slant range (Pythagorean approximation)
                    slant_range_km = np.sqrt(ground_dist_km ** 2 + sat_alt_km ** 2)

                    # Elevation angle
                    elev_rad = np.arctan2(
                        sat_alt_km,
                        ground_dist_km
                    ) - np.arcsin(
                        6378.137 * np.cos(np.arctan2(sat_alt_km, ground_dist_km)) / (6378.137 + sat_alt_km)
                    )
                    elev_deg = np.degrees(elev_rad)

                    # Visibility mask
                    visible = elev_deg >= min_elev

                    if not np.any(visible):
                        continue

                    for idx_in_batch in np.where(visible)[0]:
                        abs_idx = gp_idx + idx_in_batch
                        slant = float(slant_range_km[idx_in_batch])
                        bps, snr, margin = compute_beam_throughput(
                            eirp_dbw=eirp_dbw,
                            bandwidth_hz=bandwidth_hz,
                            frequency_hz=frequency_hz,
                            distance_km=slant,
                        )
                        writer.writerow([
                            t_min,
                            round(float(batch_lats[idx_in_batch]), 4),
                            round(float(batch_lons[idx_in_batch]), 4),
                            sat_idx,
                            satellites[sat_idx].name,
                            round(bps / 1e6, 4),
                            round(snr, 2),
                            round(margin, 2),
                            round(slant, 1),
                        ])
                        total_links += 1
                        if margin > 0:
                            closed_links += 1

    print(f"\n✅ Throughput simulation complete → {output_path}")
    print(f"   Total links computed: {total_links}")
    print(f"   Links with positive margin: {closed_links}")
    if total_links > 0:
        print(f"   Link closure rate: {100 * closed_links / total_links:.1f}%")
