"""
Total Cost of Ownership (TCO) model, cost calculations, and report formatters.
"""

import numpy as np
from .constants import TCO_CONFIG


def select_launch_vehicle(satellite_mass_kg, batch_size):
    """Select appropriate launch vehicle based on satellite mass and batch size"""
    total_mass = satellite_mass_kg * batch_size

    for name, specs in TCO_CONFIG['launch_vehicles'].items():
        if total_mass <= specs['max_payload_kg']:
            return name, specs

    return 'heavy_dedicated', TCO_CONFIG['launch_vehicles']['heavy_dedicated']


def estimate_satellite_mass(platform_type, payload_type):
    """Estimate satellite mass based on platform and payload"""
    platform = TCO_CONFIG['satellite_platforms'][platform_type]
    base_mass = platform['typical_mass_kg']
    multiplier = TCO_CONFIG['payload_multipliers'].get(payload_type, 1.0)
    return base_mass * multiplier


def calculate_tco(num_sats, platform_type, payload_type, satellite_lifetime_years,
                  replacement_rate_per_year, mission_duration_years=15, num_planes=1,
                  deployment_mode='basic'):
    """Calculate Total Cost of Ownership for satellite constellation"""
    cfg = TCO_CONFIG
    platform = cfg['satellite_platforms'][platform_type]
    deployment = cfg['deployment'][deployment_mode]

    sat_mass_kg = estimate_satellite_mass(platform_type, payload_type)

    # === INITIAL INVESTMENT (CAPEX) ===
    dev_costs = (
        cfg['development']['initial_rd'] +
        cfg['development']['payload_development'] +
        cfg['development']['ground_segment']
    )

    base_sat_cost = num_sats * platform['unit_cost']
    propulsion_cost = num_sats * deployment['propulsion_cost_per_sat']
    initial_sat_cost = base_sat_cost + propulsion_cost

    planes_per_launch = deployment['planes_per_launch']
    num_launches_for_planes = int(np.ceil(num_planes / planes_per_launch))

    estimated_sats_per_launch = max(4, int(np.ceil(num_sats / num_launches_for_planes)))
    launch_vehicle_name, launch_specs = select_launch_vehicle(sat_mass_kg, estimated_sats_per_launch)

    max_sats_per_launch = launch_specs['typical_batch_size']
    actual_sats_per_launch = int(np.ceil(num_sats / num_launches_for_planes))

    if actual_sats_per_launch > max_sats_per_launch:
        num_launches_for_capacity = int(np.ceil(num_sats / max_sats_per_launch))
        num_initial_launches = max(num_launches_for_planes, num_launches_for_capacity)
        actual_sats_per_launch = int(np.ceil(num_sats / num_initial_launches))
    else:
        num_initial_launches = num_launches_for_planes

    if 'base_cost' in launch_specs:
        total_mass_per_launch = sat_mass_kg * actual_sats_per_launch
        cost_per_launch = launch_specs['base_cost'] + (total_mass_per_launch * launch_specs['cost_per_kg'])
        initial_launch_cost = num_initial_launches * cost_per_launch
    else:
        initial_launch_cost = num_initial_launches * launch_specs['cost_per_launch']

    num_ground_stations = int(np.ceil((num_sats / 100) * cfg['operations']['ground_stations']['stations_needed_per_100_sats']))
    ground_station_capex = num_ground_stations * cfg['operations']['ground_stations']['initial_capex']
    mission_control_capex = cfg['operations']['mission_control']['initial_capex']

    launch_insurance = (initial_sat_cost + initial_launch_cost) * cfg['insurance']['launch_insurance_pct']

    total_capex = (
        dev_costs +
        initial_sat_cost +
        initial_launch_cost +
        ground_station_capex +
        mission_control_capex +
        launch_insurance
    )

    # === RECURRING COSTS (OPEX per year) ===
    replacement_sat_cost = replacement_rate_per_year * platform['unit_cost']

    actual_replacement_sats_per_launch = min(actual_sats_per_launch, replacement_rate_per_year)
    num_replacement_launches = max(1, int(np.ceil(replacement_rate_per_year / actual_sats_per_launch)))

    if 'base_cost' in launch_specs:
        total_mass_per_launch = sat_mass_kg * actual_replacement_sats_per_launch
        cost_per_launch = launch_specs['base_cost'] + (total_mass_per_launch * launch_specs['cost_per_kg'])
        replacement_launch_cost = num_replacement_launches * cost_per_launch
    else:
        replacement_launch_cost = num_replacement_launches * launch_specs['cost_per_launch']

    ground_station_opex = num_ground_stations * cfg['operations']['ground_stations']['annual_opex']
    mission_control_opex = cfg['operations']['mission_control']['annual_opex']
    network_opex = num_sats * cfg['operations']['network_operations']['cost_per_sat_per_year']

    num_engineers = int(np.ceil((num_sats / 100) * cfg['operations']['staff']['engineers_per_100_sats']))
    staff_cost = num_engineers * cfg['operations']['staff']['annual_cost_per_engineer']

    in_orbit_insurance = num_sats * platform['unit_cost'] * cfg['insurance']['annual_in_orbit_pct']

    decommissioning = (replacement_rate_per_year * cfg['decommissioning']['cost_per_satellite'] +
                       cfg['decommissioning']['regulatory_compliance'])

    annual_opex = (
        replacement_sat_cost +
        replacement_launch_cost +
        ground_station_opex +
        mission_control_opex +
        network_opex +
        staff_cost +
        in_orbit_insurance +
        decommissioning
    )

    # === TOTAL COST OF OWNERSHIP ===
    total_opex_over_mission = annual_opex * mission_duration_years
    total_tco = total_capex + total_opex_over_mission
    cost_per_sat_per_year = total_tco / (num_sats * mission_duration_years)

    return {
        'mission_parameters': {
            'num_satellites': num_sats,
            'num_planes': num_planes,
            'deployment_mode': deployment_mode,
            'platform_type': platform_type,
            'platform_description': platform['description'],
            'satellite_mass_kg': sat_mass_kg,
            'payload_type': payload_type,
            'satellite_lifetime_years': satellite_lifetime_years,
            'replacement_rate_per_year': replacement_rate_per_year,
            'mission_duration_years': mission_duration_years,
        },
        'launch_config': {
            'launch_vehicle': launch_vehicle_name,
            'launch_vehicle_description': launch_specs['description'],
            'batch_size': actual_sats_per_launch,
            'max_vehicle_capacity': max_sats_per_launch,
            'planes_per_launch': planes_per_launch,
            'initial_launches': num_initial_launches,
            'annual_replacement_launches': num_replacement_launches,
        },
        'capex': {
            'development': dev_costs,
            'initial_satellites': initial_sat_cost,
            'initial_launches': initial_launch_cost,
            'ground_infrastructure': ground_station_capex + mission_control_capex,
            'launch_insurance': launch_insurance,
            'total': total_capex,
        },
        'annual_opex': {
            'satellite_replacement': replacement_sat_cost,
            'replacement_launches': replacement_launch_cost,
            'ground_operations': ground_station_opex + mission_control_opex + network_opex,
            'staff': staff_cost,
            'insurance': in_orbit_insurance,
            'decommissioning': decommissioning,
            'total': annual_opex,
        },
        'total_costs': {
            'total_capex': total_capex,
            'total_opex': total_opex_over_mission,
            'total_tco': total_tco,
            'cost_per_sat_per_year': cost_per_sat_per_year,
        },
        'infrastructure': {
            'ground_stations': num_ground_stations,
            'engineers': num_engineers,
        }
    }


def print_tco_analysis(tco_data, filename=None):
    """Print formatted TCO analysis and optionally save to file"""
    lines = []
    lines.append("\n" + "="*80)
    lines.append("  💰 TOTAL COST OF OWNERSHIP (TCO) ANALYSIS 💰")
    lines.append("="*80)

    lines.append("\n📋 MISSION PARAMETERS")
    lines.append("-" * 80)
    mp = tco_data['mission_parameters']
    lines.append(f"  Constellation Size:       {mp['num_satellites']} satellites in {mp['num_planes']} planes")
    lines.append(f"  Deployment Mode:          {mp['deployment_mode'].title()}")
    lines.append(f"  Platform Type:            {mp['platform_description']}")
    lines.append(f"  Satellite Mass:           {mp['satellite_mass_kg']:.0f} kg")
    lines.append(f"  Payload:                  {mp['payload_type'].upper()}")
    lines.append(f"  Satellite Lifetime:       {mp['satellite_lifetime_years']:.1f} years")
    lines.append(f"  Replacement Rate:         {mp['replacement_rate_per_year']:.1f} sats/year")
    lines.append(f"  Mission Duration:         {mp['mission_duration_years']} years")

    lines.append("\n🚀 LAUNCH CONFIGURATION")
    lines.append("-" * 80)
    lc = tco_data['launch_config']
    lines.append(f"  Launch Vehicle:           {lc['launch_vehicle_description']}")
    lines.append(f"  Satellites per Launch:    {lc['batch_size']}")
    lines.append(f"  Planes per Launch:        {lc['planes_per_launch']}")
    lines.append(f"  Initial Deployment:       {lc['initial_launches']} launches")
    lines.append(f"  Steady-State:             {lc['annual_replacement_launches']} launches/year")

    lines.append("\n💵 INITIAL INVESTMENT (CAPEX)")
    lines.append("-" * 80)
    capex = tco_data['capex']
    lines.append(f"  Development (R&D):        ${capex['development']:>8.1f}M")
    lines.append(f"  Initial Satellites:       ${capex['initial_satellites']:>8.1f}M")
    lines.append(f"  Initial Launches:         ${capex['initial_launches']:>8.1f}M")
    lines.append(f"  Ground Infrastructure:    ${capex['ground_infrastructure']:>8.1f}M")
    lines.append(f"  Launch Insurance:         ${capex['launch_insurance']:>8.1f}M")
    lines.append(f"  {'─' * 35}")
    lines.append(f"  TOTAL CAPEX:              ${capex['total']:>8.1f}M")

    lines.append("\n📅 RECURRING COSTS (OPEX per year)")
    lines.append("-" * 80)
    opex = tco_data['annual_opex']
    lines.append(f"  Satellite Replacement:    ${opex['satellite_replacement']:>8.1f}M/year")
    lines.append(f"  Replacement Launches:     ${opex['replacement_launches']:>8.1f}M/year")
    lines.append(f"  Ground Operations:        ${opex['ground_operations']:>8.1f}M/year")
    lines.append(f"  Staff:                    ${opex['staff']:>8.1f}M/year")
    lines.append(f"  Insurance (In-Orbit):     ${opex['insurance']:>8.1f}M/year")
    lines.append(f"  Decommissioning:          ${opex['decommissioning']:>8.1f}M/year")
    lines.append(f"  {'─' * 35}")
    lines.append(f"  TOTAL ANNUAL OPEX:        ${opex['total']:>8.1f}M/year")

    lines.append("\n💰 TOTAL COST OF OWNERSHIP")
    lines.append("-" * 80)
    tc = tco_data['total_costs']
    lines.append(f"  Total CAPEX:              ${tc['total_capex']:>8.1f}M")
    lines.append(f"  Total OPEX ({mp['mission_duration_years']} years):     ${tc['total_opex']:>8.1f}M")
    lines.append(f"  {'─' * 35}")
    lines.append(f"  TOTAL TCO ({mp['mission_duration_years']} years):      ${tc['total_tco']:>8.1f}M")
    lines.append(f"\n  Cost per Satellite/Year:  ${tc['cost_per_sat_per_year']:>8.3f}M")

    lines.append("\n🏗️  INFRASTRUCTURE REQUIREMENTS")
    lines.append("-" * 80)
    infra = tco_data['infrastructure']
    lines.append(f"  Ground Stations:          {infra['ground_stations']}")
    lines.append(f"  Engineering Staff:        {infra['engineers']} people")

    lines.append("\n" + "="*80 + "\n")

    tco_text = "\n".join(lines)
    print(tco_text)

    if filename:
        output_file = f"{filename}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(tco_text)
        print(f"💾 TCO Analysis saved to: {output_file}")


def save_tco_json(tco_data, metrics, filename):
    """Save TCO + engineering metrics as a single JSON file for UI consumption."""
    import json
    payload = {
        'mission_parameters': tco_data['mission_parameters'],
        'launch_config':      tco_data['launch_config'],
        'capex':              tco_data['capex'],
        'annual_opex':        tco_data['annual_opex'],
        'total_costs':        tco_data['total_costs'],
        'infrastructure':     tco_data['infrastructure'],
        'orbital':            metrics['orbital'],
        'coverage':           metrics['coverage'],
        'constellation':      metrics['constellation'],
        'lifetime':           metrics['lifetime'],
    }
    output_file = f"{filename}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"💾 TCO JSON saved to: {output_file}")


def print_constellation_dashboard(metrics, tco_data=None, filename=None):
    """Print a formatted engineering dashboard and optionally save to file"""
    lines = []
    lines.append("\n" + "="*80)
    lines.append("  🛰️  SATELLITE CONSTELLATION ENGINEERING DASHBOARD  🛰️")
    lines.append("="*80)

    lines.append("\n📡 CONSTELLATION CONFIGURATION")
    lines.append("-" * 80)
    c = metrics['constellation']
    lines.append(f"  Total Satellites:     {c['total_satellites']:>6d}")
    lines.append(f"  Orbital Planes:       {c['num_planes']:>6d}")
    lines.append(f"  Sats per Plane:       {c['sats_per_plane']:>6d}")
    lines.append(f"  Altitude:             {c['altitude_km']:>6.0f} km")
    lines.append(f"  Inclination:          {c['inclination_deg']:>6.1f}°")

    lines.append("\n🌍 ORBITAL MECHANICS")
    lines.append("-" * 80)
    o = metrics['orbital']
    lines.append(f"  Orbital Period:       {o['period_min']:>6.1f} minutes ({o['period_min']/60:.2f} hours)")
    lines.append(f"  Orbital Velocity:     {o['velocity_km_s']:>6.2f} km/s")
    lines.append(f"  Orbits per Day:       {o['orbits_per_day']:>6.1f}")

    lines.append("\n📶 COVERAGE ANALYSIS")
    lines.append("-" * 80)
    cov = metrics['coverage']
    lines.append(f"  Min Elevation Angle:  {cov['min_elevation_deg']:>6.1f}°")
    lines.append(f"  Coverage Radius:      {cov['radius_km']:>6.0f} km")
    lines.append(f"  Coverage Diameter:    {cov['diameter_km']:>6.0f} km")
    lines.append(f"  Coverage Area:        {cov['area_km2']:>6,.0f} km²")
    lines.append(f"  Earth Coverage/Sat:   {cov['coverage_per_sat_pct']:>6.2f}%")
    lines.append(f"  Avg Revisit Time:     {cov['avg_revisit_time_min']:>6.1f} minutes")
    lines.append(f"  Max Gap Time:         {cov['max_gap_time_min']:>6.1f} minutes")

    lines.append("\n📡 LINK BUDGET BASICS")
    lines.append("-" * 80)
    lb = metrics['link_budget']
    lines.append(f"  Frequency Band:       {lb['frequency_band']}")
    lines.append(f"  Slant Range (min):    {lb['slant_range_km']:>6.0f} km")
    lines.append(f"  Free Space Loss:      {lb['free_space_loss_db']:>6.1f} dB (at 14 GHz)")

    lines.append("\n🚀 LIFETIME & DEPLOYMENT")
    lines.append("-" * 80)
    lt = metrics['lifetime']
    lines.append(f"  Satellite Lifetime:   {lt['satellite_lifetime_years']:>6.1f} years")
    lines.append(f"  First Deorbit:        Year {lt['first_deorbit_year']:.1f}")
    lines.append(f"  Replacement Rate:     {lt['replacement_rate_per_year']:>6.1f} satellites/year")
    lines.append(f"  Launch Batch Size:    {lt['batch_size']:>6d} satellites")
    lines.append(f"  Initial Launches:     {lt['initial_launches']:>6d} launches")
    lines.append(f"  Steady-State:         {lt['steady_state_launches_per_year']:>6d} launches/year")

    if tco_data:
        lines.append("\n💰 ECONOMIC SUMMARY (TCO)")
        lines.append("-" * 80)
        tc = tco_data['total_costs']
        opex = tco_data['annual_opex']
        lines.append(f"  Initial Investment:       ${tco_data['capex']['total']:>8.1f}M")
        lines.append(f"  Annual Operating Cost:    ${opex['total']:>8.1f}M/year")
        lines.append(f"  Total TCO (15 years):     ${tc['total_tco']:>8.1f}M")
        lines.append(f"  Cost per Sat/Year:        ${tc['cost_per_sat_per_year']:>8.3f}M")

    lines.append("\n" + "="*80 + "\n")

    dashboard_text = "\n".join(lines)
    print(dashboard_text)

    if filename:
        output_file = f"{filename}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(dashboard_text)
        print(f"💾 Dashboard saved to: {output_file}")


# ---------------------------------------------------------------------------
# Multi-shell dashboard
# ---------------------------------------------------------------------------

def print_multi_shell_dashboard(shells_cfg, agg_metrics, filename=None):
    """Print a combined dashboard for a multi-shell constellation.

    Args:
        shells_cfg  : list of shell dicts (same as passed to generate_multi_shell_tles)
        agg_metrics : result of aggregate_constellation_metrics()
        filename    : optional text file to save (without extension)
    """
    combined = agg_metrics['combined']
    per_shell = agg_metrics['per_shell']

    lines = []
    lines.append("=" * 80)
    lines.append("🌐 MULTI-SHELL CONSTELLATION DASHBOARD")
    lines.append("=" * 80)
    lines.append(f"\n  Total Satellites   : {combined['total_satellites']}")
    lines.append(f"  Number of Shells   : {combined['num_shells']}")
    lines.append(f"  Combined Coverage  : ~{combined['approx_combined_coverage_pct']:.1f}% of Earth surface")
    lines.append(f"  Best Revisit Time  : {combined['best_shell_revisit_min']:.1f} min")
    lines.append("")
    lines.append(f"{'Shell':<30} {'Sats':>6} {'Planes':>7} {'Inc°':>6} {'Alt km':>7} "
                 f"{'Cov Rad km':>11} {'Period min':>11}")
    lines.append("-" * 80)

    for i, (sh, m) in enumerate(zip(shells_cfg, per_shell)):
        label = sh.get('name') or f"Shell-{i+1} {sh['inclination']:.1f}°"
        cov   = m['coverage']
        orb   = m['orbital']
        lines.append(
            f"  {label:<28} {sh['sats']:>6} {sh['planes']:>7} "
            f"{sh['inclination']:>6.1f} {sh['altitude_km']:>7.0f} "
            f"{cov['radius_km']:>11.0f} {orb['period_min']:>11.1f}"
        )

    lines.append("\n" + "=" * 80 + "\n")
    text = "\n".join(lines)
    print(text)

    if filename:
        out = f"{filename}.txt"
        with open(out, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"💾 Multi-shell dashboard saved: {out}")
