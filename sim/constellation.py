"""
Walker constellation generator, coverage geometry, and constellation metrics.
"""

import math
import numpy as np


def generate_walker_delta_tles(num_sats, num_planes, inclination, altitude_km, phasing=1, epoch_str="24001.00000000"):
    """Generate TLE strings for Walker Delta constellation"""
    mean_motion_per_day = 86400 / (2 * math.pi * math.sqrt((6378.137 + altitude_km)**3 / 398600.4418))
    eccentricity = 0.0001
    arg_perigee = 0.0

    sats_per_plane = num_sats // num_planes
    raan_spacing = 360.0 / num_planes

    tles = []
    sat_id = 1

    for plane_idx in range(num_planes):
        raan = (plane_idx * raan_spacing) % 360.0
        for sat_in_plane in range(sats_per_plane):
            mean_anomaly = (sat_in_plane * (360.0 / sats_per_plane) + (plane_idx * phasing * 360.0 / num_sats)) % 360.0

            line1 = f"1 {sat_id:05d}U 24001A   {epoch_str}  .00000000  00000-0  00000-0 0    00"
            line2 = f"2 {sat_id:05d} {inclination:8.4f} {raan:8.4f} {int(eccentricity*10000000):07d} {arg_perigee:8.4f} {mean_anomaly:8.4f} {mean_motion_per_day:11.8f}    00"

            tles.append((f"SAT-{sat_id:03d}", line1, line2))
            sat_id += 1

    return tles


def calculate_coverage_footprint(sat_alt_km, min_elev_deg):
    """Calculate the radius of coverage footprint on Earth surface

    Args:
        sat_alt_km: Satellite altitude above Earth surface (km)
        min_elev_deg: Minimum elevation angle (degrees)

    Returns:
        Coverage radius on Earth surface (km)
    """
    earth_radius = 6378.137

    elev_rad = np.radians(min_elev_deg)
    r_sat = earth_radius + sat_alt_km

    cos_elev = np.cos(elev_rad)
    sin_rho = (earth_radius / r_sat) * cos_elev
    sin_rho = np.clip(sin_rho, -1.0, 1.0)
    rho = np.arcsin(sin_rho)

    lambda_central = (np.pi / 2 - elev_rad) - rho
    coverage_radius = earth_radius * lambda_central

    return coverage_radius


def calculate_constellation_metrics(num_sats, num_planes, altitude_km, inclination_deg, min_elev_deg=10.0):
    """Calculate comprehensive constellation metrics for engineering dashboard"""
    earth_radius = 6378.137
    earth_mu = 398600.4418

    r_orbit = earth_radius + altitude_km
    orbital_period_sec = 2 * np.pi * np.sqrt(r_orbit**3 / earth_mu)
    orbital_period_min = orbital_period_sec / 60
    orbital_velocity = 2 * np.pi * r_orbit / orbital_period_sec

    coverage_radius_km = calculate_coverage_footprint(altitude_km, min_elev_deg)
    coverage_area_km2 = np.pi * coverage_radius_km**2
    earth_surface_area = 4 * np.pi * earth_radius**2
    coverage_per_sat_pct = (coverage_area_km2 / earth_surface_area) * 100

    orbital_periods_per_day = 1440 / orbital_period_min
    sats_per_plane = max(1, num_sats // num_planes)
    # In-track gap: time between successive satellites in the same plane
    in_track_gap_min = orbital_period_min / sats_per_plane
    # Cross-track gap: time between successive plane passes at a given ground point
    cross_track_gap_min = orbital_period_min / num_planes
    max_gap_time_min = max(in_track_gap_min, cross_track_gap_min)
    avg_revisit_time_min = (in_track_gap_min + cross_track_gap_min) / 2

    frequency_band = "Ku-band (12-18 GHz)"
    free_space_loss_db = 20 * np.log10(altitude_km) + 20 * np.log10(14e9) + 20 * np.log10(4 * np.pi / 3e8)

    if altitude_km < 300:
        satellite_lifetime_years = 0.5
    elif altitude_km < 400:
        satellite_lifetime_years = 1.0 + (altitude_km - 300) * 0.04
    elif altitude_km < 600:
        satellite_lifetime_years = 5.0 + (altitude_km - 400) * 0.025
    elif altitude_km < 1000:
        satellite_lifetime_years = 10.0 + (altitude_km - 600) * 0.0125
    else:
        satellite_lifetime_years = min(15.0 + (altitude_km - 1000) * 0.005, 20.0)

    first_deorbit_year = satellite_lifetime_years
    replacement_rate_per_year = num_sats / satellite_lifetime_years

    typical_batch_size = min(50, num_sats // 5)
    if typical_batch_size < 1:
        typical_batch_size = 1
    total_launches_needed = int(np.ceil(num_sats / typical_batch_size))
    launches_per_year_steady = max(1, int(np.ceil(replacement_rate_per_year / typical_batch_size)))

    return {
        'constellation': {
            'total_satellites': num_sats,
            'num_planes': num_planes,
            'sats_per_plane': num_sats // num_planes,
            'altitude_km': altitude_km,
            'inclination_deg': inclination_deg,
        },
        'orbital': {
            'period_min': orbital_period_min,
            'velocity_km_s': orbital_velocity,
            'orbits_per_day': orbital_periods_per_day,
        },
        'coverage': {
            'radius_km': coverage_radius_km,
            'diameter_km': coverage_radius_km * 2,
            'area_km2': coverage_area_km2,
            'coverage_per_sat_pct': coverage_per_sat_pct,
            'min_elevation_deg': min_elev_deg,
            'avg_revisit_time_min': avg_revisit_time_min,
            'max_gap_time_min': max_gap_time_min,
        },
        'link_budget': {
            'frequency_band': frequency_band,
            'free_space_loss_db': free_space_loss_db,
            'slant_range_km': altitude_km / np.sin(np.radians(min_elev_deg)),
        },
        'lifetime': {
            'satellite_lifetime_years': satellite_lifetime_years,
            'first_deorbit_year': first_deorbit_year,
            'replacement_rate_per_year': replacement_rate_per_year,
            'batch_size': typical_batch_size,
            'initial_launches': total_launches_needed,
            'steady_state_launches_per_year': launches_per_year_steady,
        }
    }


# ---------------------------------------------------------------------------
# Multi-shell constellation support
# ---------------------------------------------------------------------------

def generate_multi_shell_tles(shells):
    """Generate TLEs for a multi-shell constellation.

    Args:
        shells: list of dicts, each with keys:
            sats        (int)   — total satellites in this shell
            planes      (int)   — number of orbital planes
            inclination (float) — inclination in degrees
            altitude_km (float) — orbital altitude
            phasing     (int)   — Walker phasing parameter (default 1)
            name        (str)   — human label, e.g. "Shell-1 55°" (optional)

    Returns:
        tles     : flat list of (sat_name, line1, line2) tuples
        shell_map: dict mapping sat_name → shell_index (0-based)
        shell_meta: list of dicts with shell summary info
    """
    tles = []
    shell_map = {}
    shell_meta = []

    for shell_idx, shell in enumerate(shells):
        sats       = shell['sats']
        planes     = shell['planes']
        inc        = shell['inclination']
        alt        = shell['altitude_km']
        phasing    = shell.get('phasing', 1)
        label      = shell.get('name') or f"Shell-{shell_idx + 1} {inc:.1f}°"

        shell_tles = generate_walker_delta_tles(sats, planes, inc, alt, phasing)

        for orig_name, l1, l2 in shell_tles:
            new_name = f"S{shell_idx + 1}-{orig_name}"
            # Rewrite the TLE name field (first line of TLE block is just the name)
            tles.append((new_name, l1, l2))
            shell_map[new_name] = shell_idx

        shell_meta.append({
            'index':       shell_idx,
            'label':       label,
            'sats':        sats,
            'planes':      planes,
            'inclination': inc,
            'altitude_km': alt,
        })

    return tles, shell_map, shell_meta


def aggregate_constellation_metrics(shells, min_elev_deg=10.0):
    """Compute and aggregate metrics across all shells.

    Returns a dict with per-shell metrics plus combined totals.
    """
    per_shell = []
    total_sats = 0

    for shell in shells:
        m = calculate_constellation_metrics(
            num_sats=shell['sats'],
            num_planes=shell['planes'],
            altitude_km=shell['altitude_km'],
            inclination_deg=shell['inclination'],
            min_elev_deg=min_elev_deg,
        )
        per_shell.append(m)
        total_sats += shell['sats']

    # Aggregate coverage: combined coverage = 1 - Π(1 - p_i) approximation
    combined_coverage_pct = 100.0 * (
        1.0 - math.prod(1.0 - m['coverage']['coverage_per_sat_pct'] / 100.0 * m['constellation']['total_satellites']
                        for m in per_shell)
    )
    combined_coverage_pct = min(combined_coverage_pct, 100.0)

    # Best revisit = min max-gap across shells
    best_revisit = min(m['coverage']['max_gap_time_min'] for m in per_shell)

    return {
        'per_shell': per_shell,
        'combined': {
            'total_satellites': total_sats,
            'num_shells': len(shells),
            'approx_combined_coverage_pct': round(combined_coverage_pct, 2),
            'best_shell_revisit_min': round(best_revisit, 2),
        }
    }
