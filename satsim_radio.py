#!/usr/bin/env python3
"""
Satellite Constellation Radio Link Simulator - Combined Version
Merges observer-centric accuracy with vectorized performance
Supports QGIS CSV export with WKT geometry
"""

import argparse
import sys
import csv
import numpy as np
import matplotlib
from datetime import timedelta
import warnings
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.animation import FuncAnimation, PillowWriter
from skyfield.api import EarthSatellite, load, wgs84
from skyfield.framelib import itrs
import matplotlib.font_manager as fm

warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')


# --- FONT CONFIGURATION ---
plt_font_family = 'sans-serif'
plt_fonts = ['Noto Color Emoji','Symbola', 'DejaVu Sans', 'Bitstream Vera Sans', 'Noto Sans']

try:
    plt.rcParams['font.family'] = plt_font_family
    plt.rcParams['font.sans-serif'] = plt_fonts
    plt.rcParams['font.monospace'] = ['DejaVu Sans Mono', 'Symbola','Noto Color Emoji']
except:
    pass

try:
    fm.fontManager.__init__()
except:
    pass


# --- CONSTANTS & LOCATIONS ---

LOCATIONS = {
    # PRIMARY CHOKEPOINTS
    "panama_canal":      (8.9824, -79.5199),
    "suez_canal":        (30.5852, 32.3999),
    "gibraltar":         (36.1408, -5.3536),
    "bab_el_mandeb":     (12.5905, 43.3444),
    "strait_of_hormuz":  (26.5667, 56.2500),
    "strait_of_malacca": (1.3521, 103.8198),
    "bosphorus":         (41.0082, 28.9784),
    "oresund":           (55.6049, 12.8286),
    "cape_good_hope":    (-34.3548, 18.4698),

    # SECONDARY CHOKEPOINTS
    "strait_of_dover":   (51.0167, 1.4667),
    "strait_of_magellan":(-53.4833, -70.7833),
    "bering_strait":     (65.8167, -168.9333),
    "sunda_strait":      (-5.9167, 105.7500),
    "lombok_strait":     (-8.7500, 115.7167),
    "luzon_strait":      (20.5000, 121.0000),
    "korea_strait":      (34.5000, 129.5000),
    "strait_of_florida": (24.0000, -80.8333),
    "torres_strait":     (-9.8333, 142.5000),

    # TIER 1: GLOBAL MEGA-PORTS
    "shanghai":          (31.2304, 121.4737),
    "singapore":         (1.2903, 103.8519),
    "ningbo":            (29.8683, 121.5440),
    "shenzhen":          (22.5431, 114.0579),
    "busan":             (35.1796, 129.0756),
    "los_angeles":       (33.7288, -118.2620),

    # TIER 2: MAJOR REGIONAL HUBS
    "rotterdam":         (51.9225, 4.4792),
    "antwerp":           (51.2194, 4.4025),
    "hamburg":           (53.5488, 9.9872),
    "dubai_jebel_ali":   (25.0159, 55.0680),
    "tanger_med":        (35.8866, -5.4866),
    "new_york":          (40.7128, -74.0060),
    "santos":            (-23.9618, -46.3322),
    "colombo":           (6.9271, 79.8612),
    "yokohama":          (35.4437, 139.6380),
    "salalah":           (16.9980, 54.0010),

    # TIER 3: ARCTIC FRONTIERS
    "murmansk":          (68.9585, 33.0827),
    "sabetta":           (71.2740, 72.0725),
    "pevek":             (69.7029, 170.3106),
    "tiksi":             (71.6366, 128.8685),
    "petropavlovsk":     (53.0128, 158.6509),
    "nome":              (64.5011, -165.4064),
    "utqiagvik":         (71.2906, -156.7886),
    "dutch_harbor":      (53.8898, -166.5422),
    "kirkenes":          (69.7269, 30.0450),
    "finnafjord":        (66.1062, -15.1502),
    "reykjavik":         (64.1265, -21.8174),
    "tromso":            (69.6492, 18.9553),
    "nuuk":              (64.1814, -51.7215),
    "iqaluit":           (63.7467, -68.5170),
    "nanisivik":         (73.0407, -84.5492),
    "churchill":         (58.7684, -94.1650),
    "tuktoyaktuk":       (69.4454, -133.0342),
    "pangnirtung":       (66.1446, -65.7126),

    # OTHER PORTS / STRATEGIC ISLANDS
    "lisbon":            (38.7223, -9.1393),
    "london":            (51.5074, -0.1278),
    "sydney":            (-33.8688, 151.2093),
    "helsinki":          (60.1699, 24.9384),
    "rio":               (-22.9068, -43.1729),
    "luanda":            (-8.8399, 13.2894),
    "maputo":            (-25.9692, 32.5732),
    "azores":            (37.7412, -25.6756),
    "madeira":           (32.6500, -16.9080),
    "canarias":          (28.2916, -16.6291),
    "hawaii":            (21.3069, -157.8583),
    "selvagens":         (30.1378, -15.8656),
}

SEA_ROUTES = {
    "titan_corridor": [
        ("titan_01", 49.9000, -6.5000),
        ("titan_02", 49.5000, -12.0000),
        ("titan_03", 48.2000, -20.0000),
        ("titan_04", 46.5000, -30.0000),
        ("titan_05", 44.8000, -40.0000),
        ("titan_06", 43.0000, -48.0000),
        ("titan_07", 41.5000, -55.0000),
        ("titan_08", 40.8000, -62.0000),
        ("titan_09", 40.2000, -68.0000),
        ("titan_10", 40.0000, -71.5000),
    ],
    "dragon_path": [
        ("dragon_01", 34.8000, 143.0000),
        ("dragon_02", 38.0000, 155.0000),
        ("dragon_03", 42.0000, 165.0000),
        ("dragon_04", 45.0000, 175.0000),
        ("dragon_05", 47.0000, -175.0000),
        ("dragon_06", 48.0000, -165.0000),
        ("dragon_07", 46.5000, -155.0000),
        ("dragon_08", 44.0000, -145.0000),
        ("dragon_09", 40.0000, -135.0000),
        ("dragon_10", 35.5000, -125.0000),
    ],
    "silk_vein": [
        ("silk_01", 12.0000, 45.0000),
        ("silk_02", 10.5000, 52.0000),
        ("silk_03", 9.0000, 60.0000),
        ("silk_04", 7.5000, 68.0000),
        ("silk_05", 6.0000, 75.0000),
        ("silk_06", 5.8000, 82.0000),
        ("silk_07", 5.9000, 88.0000),
        ("silk_08", 6.0000, 93.0000),
        ("silk_09", 5.5000, 97.0000),
        ("silk_10", 3.0000, 100.0000),
    ],
    "roaring_passage": [
        ("roar_01", -25.0000, -40.0000),
        ("roar_02", -30.0000, -25.0000),
        ("roar_03", -33.0000, -10.0000),
        ("roar_04", -34.0000, 10.0000),
        ("roar_05", -36.0000, 25.0000),
        ("roar_06", -35.0000, 40.0000),
        ("roar_07", -32.0000, 60.0000),
        ("roar_08", -28.0000, 80.0000),
        ("roar_09", -20.0000, 95.0000),
        ("roar_10", -15.0000, 110.0000),
    ]
}

ARCTIC_ROUTES = {
    "borealis_run": [
        ("boreal_01", 71.0000, 40.0000),
        ("boreal_02", 70.8000, 55.0000),
        ("boreal_03", 73.0000, 65.0000),
        ("boreal_04", 75.0000, 80.0000),
        ("boreal_05", 76.5000, 95.0000),
        ("boreal_06", 78.0000, 103.0000),
        ("boreal_07", 77.0000, 115.0000),
        ("boreal_08", 75.5000, 135.0000),
        ("boreal_09", 74.0000, 150.0000),
        ("boreal_10", 72.5000, 165.0000),
        ("boreal_11", 71.0000, 178.0000),
        ("boreal_12", 67.0000, -169.0000),
    ],
    "franklin_maze": [
        ("franklin_01", 70.0000, -60.0000),
        ("franklin_02", 73.0000, -70.0000),
        ("franklin_03", 74.2000, -80.0000),
        ("franklin_04", 74.5000, -90.0000),
        ("franklin_05", 75.0000, -100.0000),
        ("franklin_06", 74.8000, -110.0000),
        ("franklin_07", 73.0000, -120.0000),
        ("franklin_08", 71.5000, -125.0000),
        ("franklin_09", 70.5000, -135.0000),
        ("franklin_10", 71.0000, -145.0000),
        ("franklin_11", 71.5000, -155.0000),
        ("franklin_12", 69.0000, -165.0000),
    ],
    "midnight_sun_arc": [
        ("midnight_01", 66.0000, -168.5000),
        ("midnight_02", 72.0000, -175.0000),
        ("midnight_03", 78.0000, -180.0000),
        ("midnight_04", 84.0000, -160.0000),
        ("midnight_05", 88.0000, -120.0000),
        ("midnight_06", 90.0000, 0.0000),
        ("midnight_07", 88.0000, 30.0000),
        ("midnight_08", 84.0000, 10.0000),
        ("midnight_09", 80.0000, 5.0000),
        ("midnight_10", 76.0000, 8.0000),
        ("midnight_11", 72.0000, 15.0000),
        ("midnight_12", 68.0000, 12.0000),
    ]
}

WEATHER_SCENARIOS = {
    "clear":    0.0,
    "smoke":    0.0,
    "drizzle":  0.25,
    "rain":     5.0,
    "storm":    25.0,
    "tropical": 100.0
}

COMMS_PAYLOADS = {
    "ais": { 
        "desc": "AIS (Maritime)", "mod": "GMSK", "bw": 25000,
        "dl_freq": 162.0, "sat_p_tx": 12.5, "sat_g_tx": 2.0, "gnd_g_rx": 2.0, "gnd_nf": 4.0, "req_snr_dl": 10.0,
        "ul_freq": 162.0, "gnd_p_tx": 12.5, "gnd_g_tx": 2.0, "sat_g_rx": 2.0, "sat_nf": 3.0, "req_snr_ul": 10.0
    },
    "vdes": { 
        "desc": "VDES (Data)", "mod": "QPSK", "bw": 50000,
        "dl_freq": 157.0, "sat_p_tx": 20.0, "sat_g_tx": 3.0, "gnd_g_rx": 2.0, "gnd_nf": 4.0, "req_snr_dl": 12.0,
        "ul_freq": 161.0, "gnd_p_tx": 10.0, "gnd_g_tx": 2.0, "sat_g_rx": 3.0, "sat_nf": 3.0, "req_snr_ul": 12.0
    },
    "gsm": { 
        "desc": "2G D2C", "mod": "GMSK", "bw": 200000,
        "dl_freq": 935.0, "sat_p_tx": 50.0, "sat_g_tx": 30.0, "gnd_g_rx": 0.0, "gnd_nf": 5.0, "req_snr_dl": 9.0,
        "ul_freq": 890.0, "gnd_p_tx": 2.0,  "gnd_g_tx": 0.0,  "sat_g_rx": 30.0,"sat_nf": 2.0, "req_snr_ul": 9.0
    },
    "lte": { 
        "desc": "4G D2C", "mod": "16QAM", "bw": 5000000,
        "dl_freq": 2110.0, "sat_p_tx": 80.0, "sat_g_tx": 35.0, "gnd_g_rx": -3.0,"gnd_nf": 7.0, "req_snr_dl": 15.0,
        "ul_freq": 1920.0, "gnd_p_tx": 0.2,  "gnd_g_tx": -3.0, "sat_g_rx": 35.0,"sat_nf": 2.5, "req_snr_ul": 15.0
    },
    "5g": { 
        "desc": "5G Sub-6", "mod": "64QAM", "bw": 20000000,
        "dl_freq": 2170.0, "sat_p_tx": 100.0,"sat_g_tx": 38.0, "gnd_g_rx": -5.0,"gnd_nf": 8.0, "req_snr_dl": 22.0,
        "ul_freq": 1980.0, "gnd_p_tx": 0.2,  "gnd_g_tx": -5.0, "sat_g_rx": 38.0,"sat_nf": 2.5, "req_snr_ul": 18.0
    },
    "mss": { 
        "desc": "SatPhone", "mod": "QPSK", "bw": 100000,
        "dl_freq": 1620.0, "sat_p_tx": 50.0, "sat_g_tx": 25.0, "gnd_g_rx": 2.0, "gnd_nf": 2.0, "req_snr_dl": 7.0,
        "ul_freq": 1626.5, "gnd_p_tx": 2.0,  "gnd_g_tx": 2.0,  "sat_g_rx": 25.0,"sat_nf": 2.0, "req_snr_ul": 7.0
    },
    "starlink_ku": { 
        "desc": "Starlink (Ku-Band)", "mod": "64QAM", "bw": 250000000,
        "dl_freq": 12000.0, "sat_p_tx": 20.0, "sat_g_tx": 38.0, "gnd_g_rx": 34.0, "gnd_nf": 3.0, "req_snr_dl": 12.0,
        "ul_freq": 14000.0, "gnd_p_tx": 2.0,  "gnd_g_tx": 34.0, "sat_g_rx": 38.0, "sat_nf": 4.0, "req_snr_ul": 12.0
    }
}


# --- PHYSICS ENGINE ---

class PhysicsEngine:
    """Vectorized physics calculations for fast heatmap generation"""
    
    def __init__(self, payload, weather):
        self.payload = COMMS_PAYLOADS[payload]
        self.rain_rate = WEATHER_SCENARIOS[weather]
        
    def get_rain_attenuation(self, freq_mhz, elev_deg):
        """Vectorized rain attenuation (ITU-R P.838)"""
        if self.rain_rate <= 0:
            return np.zeros_like(elev_deg) if isinstance(elev_deg, np.ndarray) else 0.0
            
        freq_ghz = freq_mhz / 1000.0
        if freq_ghz < 0.5:
            k, alpha = 0.00001, 0.8
        elif freq_ghz < 2.5:
            k, alpha = 0.0004, 1.0
        else:
            k, alpha = 0.01, 1.2
            
        specific_att = k * (self.rain_rate ** alpha)
        h_rain, h_obs = 4.0, 0.0
        
        elev_safe = np.maximum(elev_deg, 5.0)
        el_rad = np.radians(elev_safe)
        slant_path = (h_rain - h_obs) / np.sin(el_rad)
        
        return specific_att * slant_path
    
    def link_budget(self, dist_km, elev_deg, is_uplink=False):
        """Vectorized link budget calculation"""
        p = self.payload
        
        if is_uplink:
            freq = p['ul_freq']
            p_tx_w = p['gnd_p_tx']
            g_tx = p['gnd_g_tx']
            g_rx = p['sat_g_rx']
            nf = p['sat_nf']
            req_snr = p['req_snr_ul']
            bw = p['bw']
        else:
            freq = p['dl_freq']
            p_tx_w = p['sat_p_tx']
            g_tx = p['sat_g_tx']
            g_rx = p['gnd_g_rx']
            nf = p['gnd_nf']
            req_snr = p['req_snr_dl']
            bw = p['bw']
        
        fspl = 32.44 + 20 * np.log10(dist_km) + 20 * np.log10(freq)
        rain_loss = self.get_rain_attenuation(freq, elev_deg)
        
        k_tb = -174 + 10 * np.log10(bw)
        noise_floor = k_tb + nf
        
        p_tx_dbm = 10 * np.log10(p_tx_w * 1000)
        rx_power = p_tx_dbm + g_tx + g_rx - (fspl + rain_loss)
        
        raw_snr = rx_power - noise_floor
        margin = raw_snr - req_snr
        
        return margin, raw_snr, rain_loss


def calculate_rain_loss(freq_mhz, elev_deg, rain_rate):
    """Scalar rain loss calculation for legacy functions"""
    if rain_rate <= 0 or elev_deg <= 0:
        return 0.0
    freq_ghz = freq_mhz / 1000.0
    if freq_ghz < 0.5:
        k, alpha = 0.00001, 0.8
    elif freq_ghz < 2.5:
        k, alpha = 0.0004, 1.0
    else:
        k, alpha = 0.01, 1.2
    
    specific_attenuation = k * (rain_rate ** alpha)
    h_rain, h_obs = 4.0, 0.0
    el_rad = np.radians(max(elev_deg, 5.0))
    slant_path = (h_rain - h_obs) / np.sin(el_rad)
    return specific_attenuation * slant_path

def calculate_generic_link(dist_km, elev_deg, freq, bw, p_tx_w, g_tx, g_rx, nf, req_snr, weather_key):
    """Scalar link budget for legacy functions"""
    fspl = 32.44 + 20 * np.log10(dist_km) + 20 * np.log10(freq)
    rain_rate = WEATHER_SCENARIOS.get(weather_key, 0.0)
    rain_loss = calculate_rain_loss(freq, elev_deg, rain_rate)
    
    k_tb = -174 + 10 * np.log10(bw)
    noise_floor = k_tb + nf
    
    p_tx_dbm = 10 * np.log10(p_tx_w * 1000)
    rx_power = p_tx_dbm + g_tx + g_rx - (fspl + rain_loss)
    
    raw_snr = rx_power - noise_floor
    margin = raw_snr - req_snr
    return margin, raw_snr, rain_loss

def calculate_sso_inclination(altitude_km):
    """Calculate Sun-Synchronous Orbit inclination"""
    mu = 398600.4418
    re = 6378.137
    J2 = 0.00108263
    target_precession = 1.99106e-7
    
    a = re + altitude_km
    n = np.sqrt(mu / (a**3))
    cos_i = -2 * target_precession / (3 * n * J2 * (re / a)**2)
    cos_i = np.clip(cos_i, -1.0, 1.0)
    
    inclination_rad = np.arccos(cos_i)
    return np.degrees(inclination_rad)


# --- WALKER CONSTELLATION GENERATOR ---

def generate_walker_delta_tles(num_sats, num_planes, inclination, altitude_km, phasing=1, epoch_str="24001.00000000"):
    """Generate TLE strings for Walker Delta constellation"""
    import math
    
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
            mean_anomaly = (sat_in_plane * (360.0/sats_per_plane) + (plane_idx * phasing * 360.0 / num_sats)) % 360.0
            
            line1 = f"1 {sat_id:05d}U 24001A   {epoch_str}  .00000000  00000-0  00000-0 0    00"
            line2 = f"2 {sat_id:05d} {inclination:8.4f} {raan:8.4f} {int(eccentricity*10000000):07d} {arg_perigee:8.4f} {mean_anomaly:8.4f} {mean_motion_per_day:11.8f}    00"
            
            tles.append((f"SAT-{sat_id:03d}", line1, line2))
            sat_id += 1
    
    return tles


# --- HEATMAP MODE (VECTORIZED) ---

def run_heatmap(args):
    """Generate global coverage heatmap with vectorized physics"""
    print(f"🗺️  Generating heatmap (resolution: {args.res}° grid)...")
    
    ts = load.timescale()
    t0 = ts.utc(2024, 1, 1, 12, 0, 0)
    
    # Generate constellation
    if args.sso:
        sso_inc = calculate_sso_inclination(args.altitude)
        print(f"🛰️  SSO Mode: Using inclination {sso_inc:.2f}° for {args.altitude}km altitude")
        inc = sso_inc
    else:
        inc = args.inclination
    
    tles = generate_walker_delta_tles(args.sats, args.planes, inc, args.altitude, args.phasing)
    sats = [EarthSatellite(line1, line2, name, ts) for name, line1, line2 in tles]
    
    # Create grid (inclusive endpoints)
    lats = np.arange(-90, 91, args.res)
    lons = np.arange(-180, 181, args.res)
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    grid_points = np.column_stack([lat_grid.ravel(), lon_grid.ravel()])
    
    print(f"📊 Grid: {len(grid_points)} points")
    
    # Time window: 60 steps × 12 minutes = 720 minutes
    steps = 60
    times = [ts.utc(t0.utc.year, t0.utc.month, t0.utc.day, t0.utc.hour, t0.utc.minute + i*12) for i in range(steps)]
    
    # Observer unit vectors (Earth-fixed, computed once)
    lat_rad = np.radians(grid_points[:, 0])
    lon_rad = np.radians(grid_points[:, 1])
    obs_x = np.cos(lat_rad) * np.cos(lon_rad)
    obs_y = np.cos(lat_rad) * np.sin(lon_rad)
    obs_z = np.sin(lat_rad)
    obs_vecs = np.stack((obs_x, obs_y, obs_z), axis=1)
    
    coverage_counts = np.zeros(len(grid_points), dtype=np.int32)
    chunk_size = 5000
    
    R_earth = 6378.137
    horizon_limit = R_earth / (R_earth + args.altitude)
    
    print(f"⏱️  Simulating {steps} timesteps over {steps*12} minutes...")
    
    for t_idx, t in enumerate(times):
        # Propagate satellites at this timestep
        positions = [s.at(t).frame_xyz(itrs).km for s in sats]
        sat_pos = np.column_stack(positions).T  # (N_sats, 3)
        
        # Normalize satellite vectors
        sat_norm = sat_pos / np.linalg.norm(sat_pos, axis=1)[:, np.newaxis]
        
        # Chunked processing
        for i in range(0, len(grid_points), chunk_size):
            end = min(i + chunk_size, len(grid_points))
            chunk_obs = obs_vecs[i:end]
            
            # Cosine similarity (dot product of unit vectors)
            cos_sim = np.dot(chunk_obs, sat_norm.T)  # (chunk_size, N_sats)
            
            # Check if any satellite is visible (above horizon)
            max_cos = np.max(cos_sim, axis=1)
            visible_mask = max_cos > horizon_limit
            
            # Accumulate coverage
            coverage_counts[i:end] += visible_mask.astype(np.int32)
        
        if (t_idx + 1) % 10 == 0:
            print(f"  Processed {t_idx + 1}/{steps} timesteps...")
    
    # Calculate availability percentage
    availability_pct_flat = (coverage_counts / steps) * 100.0
    coverage_grid = availability_pct_flat.reshape(lat_grid.shape)
    
    # Save CSV with WKT geometry
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
    
    # Plot heatmap
    fig, ax = plt.subplots(figsize=(16, 8))
    im = ax.imshow(coverage_grid, extent=[-180, 180, -90, 90], origin='lower', 
                   cmap='RdYlGn', vmin=0, vmax=100, aspect='auto')
    
    ax.set_xlabel('Longitude (°)')
    ax.set_ylabel('Latitude (°)')
    ax.set_title(f"Coverage Heatmap | {COMMS_PAYLOADS[args.comms]['desc']} | {walker_suffix}")
    
    cbar = plt.colorbar(im, ax=ax, label='Availability (%)')
    
    img_filename = f"heatmap_{args.comms}_{walker_suffix}.png"
    plt.savefig(img_filename, dpi=150, bbox_inches='tight')
    print(f"💾 Saved: {img_filename}")
    
    plt.show()


# --- SKY VIEW MODE (OBSERVER-CENTRIC WITH PRETTY DASHBOARD) ---

def view_sky(args):
    """Observer-centric sky view with animated dashboard"""
    ts = load.timescale()
    t0 = ts.utc(2024, 1, 1, 12, 0, 0)
    
    # Determine location
    loc_name = args.location
    if loc_name in LOCATIONS:
        lat, lon = LOCATIONS[loc_name]
    else:
        try:
            lat, lon = map(float, loc_name.split(','))
        except:
            print(f"❌ Unknown location: {loc_name}")
            return
    
    observer = wgs84.latlon(lat, lon)
    
    # Generate constellation
    if args.sso:
        sso_inc = calculate_sso_inclination(args.altitude)
        print(f"🛰️  SSO Mode: Using inclination {sso_inc:.2f}°")
        inc = sso_inc
    else:
        inc = args.inclination
    
    tles = generate_walker_delta_tles(args.sats, args.planes, inc, args.altitude, args.phasing)
    sats = [EarthSatellite(line1, line2, name, ts) for name, line1, line2 in tles]
    
    p = COMMS_PAYLOADS[args.comms]
    mode = "Bidirectional" if args.bidi else "Downlink Only"
    
    # Setup figure with dashboard
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
    
    # Trail storage
    trail_lines = []
    if args.trails:
        trail_data = {}
    
    # Connectivity tracking
    connectivity_frames = []  # Track True/False for each frame
    
    def update(frame):
        nonlocal connectivity_frames
        
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
                
                # Downlink
                dl_margin, dl_snr, rain_loss = calculate_generic_link(
                    dist_km, alt.degrees, p['dl_freq'], p['bw'],
                    p['sat_p_tx'], p['sat_g_tx'], p['gnd_g_rx'], p['gnd_nf'],
                    p['req_snr_dl'], args.weather
                )
                
                # Uplink
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
                    'name': sat.name,
                    'dl_mar': dl_margin,
                    'dl_snr': dl_snr,
                    'ul_mar': ul_margin,
                    'ul_snr': ul_snr,
                    'connected': connected
                })
                
                visible_azs.append(az_rad)
                visible_alts.append(alt.degrees)
                visible_margins.append(margin)
                
                # Store trails
                if args.trails:
                    if sat.name not in trail_data:
                        trail_data[sat.name] = {'az': [], 'alt': []}
                    trail_data[sat.name]['az'].append(az_rad)
                    trail_data[sat.name]['alt'].append(alt.degrees)
                    # Keep trail length reasonable
                    if len(trail_data[sat.name]['az']) > 30:
                        trail_data[sat.name]['az'].pop(0)
                        trail_data[sat.name]['alt'].pop(0)
                
                if connected:
                    has_connection = True
        
        # Record connectivity state for this frame
        connectivity_frames.append(has_connection)
        
        # Update scatter
        if visible_azs:
            scat.set_offsets(np.c_[visible_azs, visible_alts])
            scat.set_array(np.array(visible_margins))
        else:
            scat.set_offsets(np.empty((0, 2)))
        
        # Redraw trails
        for line in trail_lines:
            line.remove()
        trail_lines.clear()
        
        if args.trails:
            for sat_name, data in trail_data.items():
                if len(data['az']) > 1:
                    line, = ax.plot(data['az'], data['alt'], 'b-', alpha=0.2, linewidth=1)
                    trail_lines.append(line)
        
        # Calculate connectivity percentage
        if len(connectivity_frames) > 0:
            connectivity_pct = (sum(connectivity_frames) / len(connectivity_frames)) * 100.0
        else:
            connectivity_pct = 0.0
        
        # Sort satellites by best margin
        if args.bidi:
            visible_data.sort(key=lambda x: min(x['dl_mar'], x['ul_mar']) if x['ul_mar'] is not None else x['dl_mar'], reverse=True)
        else:
            visible_data.sort(key=lambda x: x['dl_mar'], reverse=True)
        top_sats = visible_data[:3]
        
        # Dashboard rendering
        ax_info.clear()
        ax_info.axis('off')
        
        walker_suffix = f"walker_{int(inc)}_{args.sats}_{args.planes}"
        
        # Header line
        ax_info.text(0.02, 0.95, f"SERVICE: {p['desc']} ({p['mod']}) | WEATHER: {args.weather.upper()} | Connectivity: {connectivity_pct:.1f}%", 
                     fontsize=11, weight='bold', family='monospace')
        
        # Column headers
        y_pos = 0.75
        ax_info.text(0.02, y_pos, "SAT ID", fontsize=10, weight='bold', family='monospace')
        ax_info.text(0.20, y_pos, "DOWNLINK (Rx Ground)", fontsize=10, weight='bold', color='blue', family='monospace')
        if args.bidi:
            ax_info.text(0.55, y_pos, "UPLINK (Rx Space)", fontsize=10, weight='bold', color='red', family='monospace')
        ax_info.text(0.85, y_pos, "STATUS", fontsize=10, weight='bold', family='monospace')
        
        y_pos -= 0.15
        
        # Display top 3 satellites
        if not top_sats:
            ax_info.text(0.02, y_pos, "NO SATELLITES IN VIEW", family='monospace')
        else:
            for s in top_sats:
                # Colors for margins
                c_dl = 'green' if s['dl_mar'] >= 0 else 'red'
                
                # Icons
                icon = "[LINK OK]" if s['connected'] else "[BROKEN]"
                
                # Row Data
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
    
    # Animation
    frames = args.duration // args.speed
    anim = FuncAnimation(fig, update, frames=frames, interval=50, blit=False)
    
    if args.save:
        walker_suffix = f"walker_{int(inc)}_{args.sats}_{args.planes}"
        gif_filename = f"sky_{loc_name}_{args.comms}_{walker_suffix}.gif"
        writer = PillowWriter(fps=10)
        anim.save(gif_filename, writer=writer)
        print(f"💾 Saved: {gif_filename}")
    
    plt.show()
    
    # Return connectivity stats
    final_connectivity = (sum(connectivity_frames) / len(connectivity_frames)) * 100.0 if connectivity_frames else 0.0
    return {
        'location': loc_name,
        'latitude': lat,
        'longitude': lon,
        'connectivity_pct': final_connectivity
    }


# --- COVERAGE MODE (BATCH PROCESSING WITH CSV EXPORT) ---

def run_coverage(args):
    """Batch coverage analysis across multiple locations with CSV export"""
    
    # Determine location set
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
    
    # CSV filename with WKT
    inc = calculate_sso_inclination(args.altitude) if args.sso else args.inclination
    walker_suffix = f"walker_{int(inc)}_{args.sats}_{args.planes}"
    csv_filename = f"coverage_{csv_suffix}_{args.comms}_{walker_suffix}.csv"
    
    # Write CSV header
    with open(csv_filename, 'w', newline='') as csvfile:
        fieldnames = ['location', 'latitude', 'longitude', 'connectivity_pct', 'wkt_geom']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
    
    print(f"💾 Writing results to: {csv_filename}")
    
    # Process each location
    for idx, (loc_name, (lat, lon)) in enumerate(locations_to_test.items(), 1):
        print(f"\n[{idx}/{len(locations_to_test)}] Testing: {loc_name}")
        
        # Override location for sky view
        args.location = loc_name
        result = view_sky(args)
        
        # Append to CSV
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
    
    print(f"\n🎉 Coverage analysis complete! Results saved to: {csv_filename}")


# --- ORBIT VIEW (3D VISUALIZATION) ---

def view_orbit(args):
    """3D orbital visualization with animation"""
    ts = load.timescale()
    t0 = ts.utc(2024, 1, 1, 12, 0, 0)
    
    if args.sso:
        inc = calculate_sso_inclination(args.altitude)
        print(f"🛰️  SSO Mode: Using inclination {inc:.2f}°")
    else:
        inc = args.inclination
    
    tles = generate_walker_delta_tles(args.sats, args.planes, inc, args.altitude, args.phasing)
    sats = [EarthSatellite(line1, line2, name, ts) for name, line1, line2 in tles]

    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Earth sphere
    u, v = np.mgrid[0:2*np.pi:50j, 0:np.pi:25j]
    x = 6378.137 * np.cos(u) * np.sin(v)
    y = 6378.137 * np.sin(u) * np.sin(v)
    z = 6378.137 * np.cos(v)
    ax.plot_surface(x, y, z, color='lightblue', alpha=0.3)
    
    walker_suffix = f"walker_{int(inc)}_{args.sats}_{args.planes}"
    max_range = args.altitude + 6378.137
    
    # Initialize scatter and trail storage
    scatters = [ax.scatter([], [], [], c='red', s=30, marker='o') for _ in sats]
    trail_lines = []
    if args.trails:
        trail_data = [{'x': [], 'y': [], 'z': []} for _ in sats]
    
    def update(frame):
        t = ts.utc(t0.utc_datetime() + timedelta(minutes=frame * 2))
        
        for idx, sat in enumerate(sats):
            pos = sat.at(t).position.km
            scatters[idx]._offsets3d = ([pos[0]], [pos[1]], [pos[2]])
            
            if args.trails:
                trail_data[idx]['x'].append(pos[0])
                trail_data[idx]['y'].append(pos[1])
                trail_data[idx]['z'].append(pos[2])
                
                # Keep trail length reasonable
                if len(trail_data[idx]['x']) > 50:
                    trail_data[idx]['x'].pop(0)
                    trail_data[idx]['y'].pop(0)
                    trail_data[idx]['z'].pop(0)
        
        # Redraw trails
        for line in trail_lines:
            line.remove()
        trail_lines.clear()
        
        if args.trails:
            for idx in range(len(sats)):
                if len(trail_data[idx]['x']) > 1:
                    line, = ax.plot(trail_data[idx]['x'], trail_data[idx]['y'], 
                                    trail_data[idx]['z'], 'r-', alpha=0.3, linewidth=0.5)
                    trail_lines.append(line)
        
        ax.set_title(f"Orbital View | {walker_suffix} | T+{frame*2} min")
        
        return scatters
    
    ax.set_xlabel('X (km)')
    ax.set_ylabel('Y (km)')
    ax.set_zlabel('Z (km)')
    ax.set_xlim([-max_range, max_range])
    ax.set_ylim([-max_range, max_range])
    ax.set_zlim([-max_range, max_range])
    
    frames = 180  # 6 hours at 2 min/frame
    anim = FuncAnimation(fig, update, frames=frames, interval=50, blit=False)
    
    if args.save:
        filename = f"orbit_{walker_suffix}.gif"
        writer = PillowWriter(fps=10)
        anim.save(filename, writer=writer)
        print(f"💾 Saved: {filename}")
    
    plt.show()


# --- TRACK VIEW (GROUND TRACK) ---

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

    fig, ax = plt.subplots(figsize=(16, 8))    # Plot tracks
    colors = plt.cm.tab20(np.linspace(0, 1, args.planes))
    
    for idx, sat in enumerate(sats):
        lats, lons = [], []
        for minutes in range(0, args.duration // 60, 2):
            t = ts.utc(t0.utc_datetime() + timedelta(minutes=minutes))
            geo = wgs84.subpoint(sat.at(t))
            lats.append(geo.latitude.degrees)
            lons.append(geo.longitude.degrees)
        
        plane_idx = idx // (args.sats // args.planes)
        ax.plot(lons, lats, color=colors[plane_idx], alpha=0.6, linewidth=0.8)
    
    ax.set_xlim([-180, 180])
    ax.set_ylim([-90, 90])
    ax.set_xlabel('Longitude (°)')
    ax.set_ylabel('Latitude (°)')
    ax.grid(True, alpha=0.3)
    
    walker_suffix = f"walker_{int(inc)}_{args.sats}_{args.planes}"
    ax.set_title(f"Ground Tracks | {walker_suffix}")
    
    if args.save:
        filename = f"track_{walker_suffix}.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"💾 Saved: {filename}")
    
    plt.tight_layout()
    plt.show()


# --- MAIN CLI ---

def main():
    parser = argparse.ArgumentParser(description="Satellite Constellation Radio Link Simulator - Combined")
    
    subparsers = parser.add_subparsers(dest='mode', help='Simulation mode')
    
    # Sky mode
    sky_parser = subparsers.add_parser('sky', help='Sky view from observer location')
    sky_parser.add_argument('--location', default='panama_canal', help='Location name or lat,lon')
    sky_parser.add_argument('--coverage', nargs='?', const='', help='Coverage mode: empty (LOCATIONS), sea, arctic, both, all')
    sky_parser.add_argument('--comms', default='vdes', choices=COMMS_PAYLOADS.keys())
    sky_parser.add_argument('--weather', default='clear', choices=WEATHER_SCENARIOS.keys())
    sky_parser.add_argument('--sats', type=int, default=66)
    sky_parser.add_argument('--planes', type=int, default=6)
    sky_parser.add_argument('--altitude', type=float, default=600.0)
    sky_parser.add_argument('--phasing', type=int, default=1)
    sky_parser.add_argument('--inclination', type=float, default=87.4)
    sky_parser.add_argument('--sso', action='store_true', help='Use SSO inclination')
    sky_parser.add_argument('--bidi', action='store_true', help='Calculate bidirectional links')
    sky_parser.add_argument('--duration', type=int, default=3600)
    sky_parser.add_argument('--speed', type=int, default=60)
    sky_parser.add_argument('--trails', action='store_true', help='Draw satellite trails')
    sky_parser.add_argument('--save', action='store_true')
    
    # Heatmap mode
    heatmap_parser = subparsers.add_parser('heatmap', help='Global coverage heatmap (vectorized)')
    heatmap_parser.add_argument('--comms', default='vdes', choices=COMMS_PAYLOADS.keys())
    heatmap_parser.add_argument('--weather', default='clear', choices=WEATHER_SCENARIOS.keys())
    heatmap_parser.add_argument('--sats', type=int, default=66)
    heatmap_parser.add_argument('--planes', type=int, default=6)
    heatmap_parser.add_argument('--altitude', type=float, default=600.0)
    heatmap_parser.add_argument('--phasing', type=int, default=1)
    heatmap_parser.add_argument('--inclination', type=float, default=87.4)
    heatmap_parser.add_argument('--sso', action='store_true')
    heatmap_parser.add_argument('--bidi', action='store_true')
    heatmap_parser.add_argument('--res', type=float, default=5.0, help='Grid resolution in degrees')
    
    # Orbit mode
    orbit_parser = subparsers.add_parser('orbit', help='3D orbital view')
    orbit_parser.add_argument('--sats', type=int, default=66)
    orbit_parser.add_argument('--planes', type=int, default=6)
    orbit_parser.add_argument('--altitude', type=float, default=600.0)
    orbit_parser.add_argument('--phasing', type=int, default=1)
    orbit_parser.add_argument('--inclination', type=float, default=87.4)
    orbit_parser.add_argument('--sso', action='store_true')
    orbit_parser.add_argument('--trails', action='store_true', help='Draw orbital trails')
    orbit_parser.add_argument('--save', action='store_true', help='Save to file')
    
    # Track mode
    track_parser = subparsers.add_parser('track', help='Ground track view')
    track_parser.add_argument('--sats', type=int, default=66)
    track_parser.add_argument('--planes', type=int, default=6)
    track_parser.add_argument('--altitude', type=float, default=600.0)
    track_parser.add_argument('--phasing', type=int, default=1)
    track_parser.add_argument('--inclination', type=float, default=87.4)
    track_parser.add_argument('--sso', action='store_true')
    track_parser.add_argument('--duration', type=int, default=3600)
    track_parser.add_argument('--save', action='store_true', help='Save to file')
    
    args = parser.parse_args()
    
    if not args.mode:
        parser.print_help()
        return
    
    if args.mode == 'sky':
        if args.coverage is not None:
            run_coverage(args)
        else:
            view_sky(args)
    elif args.mode == 'heatmap':
        run_heatmap(args)
    elif args.mode == 'orbit':
        view_orbit(args)
    elif args.mode == 'track':
        view_track(args)


if __name__ == "__main__":
    main()
