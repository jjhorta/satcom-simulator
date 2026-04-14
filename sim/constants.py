"""
Satellite Constellation Simulator - Constants & Configuration
All project-wide constants, lookup tables, and configuration dictionaries.
"""

import os

# --- GRAPHICS BACKENDS ---
AVAILABLE_BACKENDS = ['matplotlib', 'plotly', 'bokeh']

# --- ASSET PATHS ---
_SIM_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_SIM_DIR)
ASSETS_DIR = os.path.join(PROJECT_ROOT, 'assets')
COASTLINE_FILE = os.path.join(ASSETS_DIR, 'coastline.json')

# --- LOCATIONS ---
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

# --- WEATHER SCENARIOS ---
WEATHER_SCENARIOS = {
    "clear":    0.0,
    "smoke":    0.0,
    "drizzle":  0.25,
    "rain":     5.0,
    "storm":    25.0,
    "tropical": 100.0
}

# --- COMMUNICATIONS PAYLOADS ---
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
        "ul_freq": 890.0, "gnd_p_tx": 2.0,  "gnd_g_tx": 0.0,  "sat_g_rx": 30.0, "sat_nf": 2.0, "req_snr_ul": 9.0
    },
    "lte": {
        "desc": "4G D2C", "mod": "16QAM", "bw": 5000000,
        "dl_freq": 2110.0, "sat_p_tx": 80.0, "sat_g_tx": 35.0, "gnd_g_rx": -3.0, "gnd_nf": 7.0, "req_snr_dl": 15.0,
        "ul_freq": 1920.0, "gnd_p_tx": 0.2,  "gnd_g_tx": -3.0, "sat_g_rx": 35.0, "sat_nf": 2.5, "req_snr_ul": 15.0
    },
    "5g": {
        "desc": "5G Sub-6", "mod": "64QAM", "bw": 20000000,
        "dl_freq": 2170.0, "sat_p_tx": 100.0, "sat_g_tx": 38.0, "gnd_g_rx": -5.0, "gnd_nf": 8.0, "req_snr_dl": 22.0,
        "ul_freq": 1980.0, "gnd_p_tx": 0.2,   "gnd_g_tx": -5.0, "sat_g_rx": 38.0, "sat_nf": 2.5, "req_snr_ul": 18.0
    },
    "mss": {
        "desc": "SatPhone", "mod": "QPSK", "bw": 100000,
        "dl_freq": 1620.0, "sat_p_tx": 50.0, "sat_g_tx": 25.0, "gnd_g_rx": 2.0, "gnd_nf": 2.0, "req_snr_dl": 7.0,
        "ul_freq": 1626.5, "gnd_p_tx": 2.0,  "gnd_g_tx": 2.0,  "sat_g_rx": 25.0, "sat_nf": 2.0, "req_snr_ul": 7.0
    },
    "starlink_ku": {
        "desc": "Starlink (Ku-Band)", "mod": "64QAM", "bw": 250000000,
        "dl_freq": 12000.0, "sat_p_tx": 20.0, "sat_g_tx": 38.0, "gnd_g_rx": 34.0, "gnd_nf": 3.0, "req_snr_dl": 12.0,
        "ul_freq": 14000.0, "gnd_p_tx": 2.0,  "gnd_g_tx": 34.0, "sat_g_rx": 38.0, "sat_nf": 4.0, "req_snr_ul": 12.0
    }
}

# --- VISUALIZATION SETTINGS ---
VISUALIZATION_SETTINGS = {
    'earth': {
        'ocean_color': '#1E90FF',
        'ocean_alpha': 0.3,
    },
    'continents': {
        'fill_color': '#00FF00',
        'edge_color': '#2F4F2F',
        'alpha': 1.0,
        'edge_width': 0.5,
    },
    'satellites': {
        'color': 'red',
        'size': 50,
        'edge_color': 'white',
        'edge_width': 0.5,
    },
    'beams': {
        'color': 'yellow',
        'alpha': 0.6,
        'line_width': 2,
    },
    'trails': {
        'orbit_color': 'red',
        'orbit_alpha': 0.3,
        'orbit_width': 0.5,
        'sky_color': 'blue',
        'sky_alpha': 0.2,
        'sky_width': 1,
    }
}

# --- TCO CONFIGURATION ---
TCO_CONFIG = {
    'satellite_platforms': {
        'nanosat': {
            'typical_mass_kg': 12,
            'unit_cost': 0.7,
            'description': 'Nanosat 8U CubeSat (10-20 kg, VDES/AIS)'
        },
        'microsat': {
            'typical_mass_kg': 50,
            'unit_cost': 2.5,
            'description': 'Microsat (25-100 kg)'
        },
        'smallsat': {
            'typical_mass_kg': 150,
            'unit_cost': 5.0,
            'description': 'Smallsat (100-250 kg, SAR/optical)'
        },
        'mediumsat': {
            'typical_mass_kg': 500,
            'unit_cost': 25.0,
            'description': 'Mediumsat (250-800 kg)'
        },
        'largesat': {
            'typical_mass_kg': 2000,
            'unit_cost': 100.0,
            'description': 'Largesat (800+ kg, GEO/complex)'
        }
    },
    'payload_multipliers': {
        'ais': 0.9,
        'vdes': 1.0,
        'gsm': 1.3,
        '5g': 1.6,
        'mss': 1.4,
        'starlink_ku': 1.5,
    },
    'launch_vehicles': {
        'rideshare': {
            'base_cost': 0.325,
            'cost_per_kg': 0.0065,
            'max_payload_kg': 1500,
            'typical_batch_size': 20,
            'description': 'Rideshare (SpaceX Transporter, ~$325k+mass)'
        },
        'small_dedicated': {
            'cost_per_launch': 7.5,
            'max_payload_kg': 300,
            'typical_batch_size': 5,
            'description': 'Small dedicated (Rocket Lab Electron)'
        },
        'medium_dedicated': {
            'cost_per_launch': 67.0,
            'max_payload_kg': 15000,
            'typical_batch_size': 50,
            'description': 'Medium dedicated (Falcon 9)'
        },
        'heavy_dedicated': {
            'cost_per_launch': 150.0,
            'max_payload_kg': 50000,
            'typical_batch_size': 100,
            'description': 'Heavy dedicated (Falcon Heavy)'
        }
    },
    'development': {
        'initial_rd': 1.0,
        'payload_development': 0.5,
        'ground_segment': 1.0,
    },
    'operations': {
        'ground_stations': {
            'stations_needed_per_100_sats': 2,
            'initial_capex': 0.4,
            'annual_opex': 0.15,
        },
        'mission_control': {
            'initial_capex': 0.5,
            'annual_opex': 0.3,
        },
        'network_operations': {
            'cost_per_sat_per_year': 0.02,
        },
        'staff': {
            'engineers_per_100_sats': 8,
            'annual_cost_per_engineer': 0.15,
        },
    },
    'insurance': {
        'launch_insurance_pct': 0.05,
        'annual_in_orbit_pct': 0.02,
    },
    'decommissioning': {
        'cost_per_satellite': 0.05,
        'regulatory_compliance': 0.2,
    },
    'deployment': {
        'basic': {
            'planes_per_launch': 1,
            'propulsion_cost_per_sat': 0.0,
            'deployment_opex_factor': 1.0,
        },
        'advanced': {
            'planes_per_launch': 3,
            'propulsion_cost_per_sat': 0.15,
            'deployment_opex_factor': 1.5,
        }
    }
}
