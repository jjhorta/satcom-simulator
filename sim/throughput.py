"""
IP-layer throughput computation and supply-demand matching engine.

Provides:
    compute_beam_throughput - single beam IP throughput, SNR, link margin
    compute_all_beam_throughputs - concurrent multi-beam throughput
"""

import numpy as np


def compute_beam_throughput(
    eirp_dbw: float,
    bandwidth_hz: float,
    frequency_hz: float,
    distance_km: float,
    atmospheric_loss_db: float = 0.0,
    rain_margin_db: float = 0.0,
    noise_figure_db: float = 3.0,
    modulation_efficiency_bps_hz: float = 4.0,
    min_snr_db: float = 0.0,
) -> tuple[float, float, float]:
    """
    Compute IP-layer throughput for a single user or gateway beam.

    Args:
        eirp_dbw: Effective isotropic radiated power (dBW)
        bandwidth_hz: Allocated bandwidth (Hz)
        frequency_hz: Carrier frequency (Hz)
        distance_km: Slant range (km)
        atmospheric_loss_db: Atmospheric attenuation (dB)
        rain_margin_db: Rain fade margin (dB)
        noise_figure_db: Receiver noise figure (dB)
        modulation_efficiency_bps_hz: Spectral efficiency (bps/Hz)
        min_snr_db: Minimum SNR required for link closure (dB)

    Returns:
        Tuple of (ip_throughput_bps, snr_db, margin_db)
    """
    c = 3e8  # speed of light (m/s)
    k = 1.38e-23  # Boltzmann constant (J/K)
    T = 290  # reference noise temperature (K)

    wavelength = c / frequency_hz
    distance_m = distance_km * 1000.0

    # Free-space path loss (Friis)
    fspl_db = 20 * np.log10((4 * np.pi * distance_m) / wavelength)

    # Received power at antenna port
    prx_dbw = eirp_dbw - fspl_db - atmospheric_loss_db - rain_margin_db

    # Noise power
    noise_power_watts = k * T * bandwidth_hz
    if noise_power_watts <= 0:
        noise_power_dbm = -np.inf
    else:
        noise_power_dbm = 10 * np.log10(noise_power_watts) + 30

    prx_dbm = prx_dbw + 30

    # Signal-to-noise ratio
    snr_db = prx_dbm - noise_power_dbm

    # Shannon-Hartley capacity with numerical stability
    if snr_db > -10:
        linear_snr = 10 ** (snr_db / 10)
        capacity_bps = bandwidth_hz * np.log2(1 + linear_snr)
    else:
        capacity_bps = 0.0

    # IP throughput with 85% implementation efficiency
    ip_throughput_bps = min(
        capacity_bps * 0.85,
        bandwidth_hz * modulation_efficiency_bps_hz * 0.85,
    )

    # Link margin
    margin_db = snr_db - min_snr_db

    return float(ip_throughput_bps), float(snr_db), float(margin_db)


def compute_all_beam_throughputs(
    satellites: list[dict],
    user_terminals: list[dict],
    gateway_stations: list[dict] | None = None,
) -> dict:
    """
    Concurrent IP throughput across all user + gateway beams for all satellites.

    Args:
        satellites: List of dicts with keys:
            'lat', 'lon', 'altitude_km', 'eirp_dbw', 'bandwidth_hz', 'frequency_hz'
        user_terminals: List of dicts with keys:
            'lat', 'lon', 'noise_figure_db', 'elevation_mask_deg'
        gateway_stations: Optional list of dicts with same keys as user_terminals,
            plus 'frequency_hz' override.

    Returns:
        dict with 'results' list and 'aggregate' summary
    """
    # TODO: implement vectorised multi-beam computation
    return {
        'results': [],
        'aggregate': {
            'total_throughput_bps': 0.0,
            'mean_snr_db': 0.0,
            'min_margin_db': float('inf'),
        },
    }
