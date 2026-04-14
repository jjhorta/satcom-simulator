"""
Physics engine: link budget, rain attenuation, and orbital mechanics helpers.
"""

import numpy as np
from .constants import COMMS_PAYLOADS, WEATHER_SCENARIOS


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
    """Scalar rain loss calculation for scalar link budget functions"""
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
    """Scalar link budget for observer-centric sky view functions"""
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
