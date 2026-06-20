"""Latency mode: end-to-end RTT via multi-hop ISL routing.

Generates a time-series of one-way and round-trip latencies for a constellation
between two ground points, plus a CSV, a JSON summary and a histogram/CDF plot.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import timedelta
from typing import Optional

import numpy as np
from skyfield.api import EarthSatellite, load
from skyfield.framelib import itrs

from ..constants import KNOWN_CONSTELLATIONS, LOCATIONS
from ..constellation import generate_walker_delta_tles, generate_multi_shell_tles
from ..isl import ISL_CONFIG, isl_topology_from_walker
from ..physics import calculate_sso_inclination
from ..routing import (
    LatencyPathResult,
    find_min_latency_path,
    fiber_latency_ms,
    compute_dual_hop_latency,
    great_circle_distance_km,
)


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def _parse_location(spec: str) -> tuple[float, float]:
    """Accept ``"lat,lon"`` or a known location name → (lat, lon)."""
    if spec is None:
        raise ValueError("location required")
    s = str(spec).strip()
    if "," in s:
        try:
            lat_s, lon_s = s.split(",", 1)
            return float(lat_s), float(lon_s)
        except Exception:
            pass
    if s in LOCATIONS:
        return float(LOCATIONS[s][0]), float(LOCATIONS[s][1])
    raise ValueError(f"Unknown location '{spec}' (use 'lat,lon' or a named LOCATIONS entry)")


def _build_constellation(args, ts):
    """Return ``(sats_list, walker_suffix, num_planes_effective)``."""
    shells_cfg = None
    if getattr(args, "constellation", None):
        if args.constellation not in KNOWN_CONSTELLATIONS:
            raise ValueError(f"Unknown constellation '{args.constellation}'")
        shells_cfg = KNOWN_CONSTELLATIONS[args.constellation]
        print(f"🌐 Multi-shell preset: '{args.constellation}' ({len(shells_cfg)} shells)")
    elif getattr(args, "shells", None):
        shells_cfg = json.loads(args.shells)

    if shells_cfg is not None:
        normalised = []
        for sh in shells_cfg:
            normalised.append({
                "sats":        sh.get("sats", sh.get("num_sats", 12)),
                "planes":      sh.get("planes", sh.get("num_planes", 3)),
                "inclination": sh.get("inclination", sh.get("inc", 87.0)),
                "altitude_km": sh.get("altitude_km", sh.get("alt", sh.get("altitude", 600.0))),
                "phasing":     sh.get("phasing", 1),
            })
        tles_multi, _shell_map, _shell_meta = generate_multi_shell_tles(normalised)
        max_sats = getattr(args, "max_sats", 250)
        tles_multi = tles_multi[:max_sats]
        total_sats = sum(sh["sats"] for sh in normalised)
        sats_list = [EarthSatellite(l1, l2, n, ts) for n, l1, l2 in tles_multi]
        name = (
            getattr(args, "constellation_name", None)
            or getattr(args, "constellation", None)
            or "custom"
        )
        # Effective plane count for the Walker topology: sum of all shell planes
        planes_eff = sum(sh["planes"] for sh in normalised) or 1
        walker_suffix = f"multi_{name}_{total_sats}sats"
        print(f"🌐 Multi-shell: {len(sats_list)} sats across {len(normalised)} shells")
        return sats_list, walker_suffix, planes_eff

    # Single-shell path
    if getattr(args, "sso", False):
        inc = calculate_sso_inclination(args.altitude)
        print(f"🛰️  SSO mode → inclination {inc:.2f}° at {args.altitude} km")
    else:
        inc = args.inclination
    tles = generate_walker_delta_tles(args.sats, args.planes, inc, args.altitude, args.phasing)
    sats_list = [EarthSatellite(l1, l2, n, ts) for n, l1, l2 in tles]
    walker_suffix = f"walker_{int(inc)}_{args.sats}_{args.planes}"
    return sats_list, walker_suffix, args.planes


# ────────────────────────────────────────────────────────────────────────────
# Plot helpers
# ────────────────────────────────────────────────────────────────────────────

def _generate_latency_plots(
    rtt_values: np.ndarray,
    p5: float, p95: float, median: float,
    fiber_rtt: Optional[float],
    suffix: str,
    backend: str = "matplotlib",
) -> Optional[str]:
    """Save a 2-panel figure (histogram + CDF). Returns the saved filename."""
    if rtt_values.size == 0:
        print("⚠️  No RTT samples — skipping plot")
        return None

    if backend == "plotly":
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
        except ImportError:
            print("⚠️  plotly not available, falling back to matplotlib")
            backend = "matplotlib"

    if backend == "plotly":
        fig = make_subplots(rows=1, cols=2, subplot_titles=("RTT Histogram", "RTT CDF"))
        fig.add_trace(go.Histogram(x=rtt_values, nbinsx=30, name="RTT"), row=1, col=1)
        for v, label, color in [(p5, "P5", "lightgreen"), (median, "P50", "yellow"), (p95, "P95", "orange")]:
            fig.add_vline(x=v, line_dash="dash", line_color=color, annotation_text=label, row=1, col=1)
        sorted_v = np.sort(rtt_values)
        cdf = np.linspace(0.0, 1.0, len(sorted_v))
        fig.add_trace(go.Scatter(x=sorted_v, y=cdf, mode="lines", name="CDF"), row=1, col=2)
        if fiber_rtt is not None:
            fig.add_vline(x=fiber_rtt, line_dash="dot", line_color="red",
                          annotation_text=f"Fiber RTT ({fiber_rtt:.1f} ms)",
                          row=1, col=1)
            fig.add_vline(x=fiber_rtt, line_dash="dot", line_color="red", row=1, col=2)
        fig.update_layout(title=f"End-to-end Latency — {suffix}", showlegend=False)
        out = f"latency_{suffix}.html"
        fig.write_html(out)
        print(f"💾 Saved interactive plot: {out}")
        return out

    # matplotlib backend (default)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].hist(rtt_values, bins=30, color="steelblue", alpha=0.85, edgecolor="white")
    for v, label, color in [(p5, "P5", "green"), (median, "P50", "gold"), (p95, "P95", "orange")]:
        axes[0].axvline(v, color=color, ls="--", label=f"{label}: {v:.1f} ms")
    if fiber_rtt is not None:
        axes[0].axvline(fiber_rtt, color="red", ls=":", label=f"Fiber RTT: {fiber_rtt:.1f} ms")
    axes[0].set_xlabel("RTT (ms)"); axes[0].set_ylabel("Snapshots")
    axes[0].set_title("RTT Histogram"); axes[0].legend(loc="upper right", fontsize=9)
    axes[0].grid(alpha=0.3)

    sorted_v = np.sort(rtt_values)
    cdf = np.linspace(0.0, 1.0, len(sorted_v))
    axes[1].plot(sorted_v, cdf, color="steelblue", lw=2)
    if fiber_rtt is not None:
        below = (sorted_v < fiber_rtt).mean() * 100.0
        axes[1].axvline(fiber_rtt, color="red", ls=":", label=f"Fiber ({fiber_rtt:.1f} ms)")
        axes[1].text(0.05, 0.9, f"{below:.1f}% < fiber", transform=axes[1].transAxes,
                     bbox=dict(boxstyle="round", facecolor="white", alpha=0.85))
    axes[1].set_xlabel("RTT (ms)"); axes[1].set_ylabel("CDF")
    axes[1].set_title("RTT Cumulative Distribution"); axes[1].grid(alpha=0.3)
    axes[1].legend(loc="lower right", fontsize=9)

    fig.suptitle(f"End-to-end Latency — {suffix}", fontsize=13)
    fig.tight_layout()
    out = f"latency_{suffix}.png"
    fig.savefig(out, dpi=110, bbox_inches="tight")
    plt.close(fig)
    print(f"💾 Saved plot: {out}")
    return out


# ────────────────────────────────────────────────────────────────────────────
# Main entry
# ────────────────────────────────────────────────────────────────────────────

def run_latency(args) -> dict:
    """Execute the latency simulation. Returns a stats dict."""
    print("📡 End-to-end latency simulation (ISL routing)")

    src_lat, src_lon = _parse_location(args.from_location)
    dst_lat, dst_lon = _parse_location(args.to_location)
    print(f"   Source:      ({src_lat:.3f}, {src_lon:.3f})")
    print(f"   Destination: ({dst_lat:.3f}, {dst_lon:.3f})")

    ts = load.timescale()
    t0 = ts.utc(2024, 1, 1, 12, 0, 0)

    sats_list, walker_suffix, planes_eff = _build_constellation(args, ts)
    n_sats = len(sats_list)
    sat_names = [s.name for s in sats_list]
    print(f"   Satellites: {n_sats} (effective planes: {planes_eff})")

    duration_min = int(getattr(args, "duration", 1440))
    step_min = max(1, int(getattr(args, "step", 5)))
    n_steps = max(1, duration_min // step_min)

    isl_range = float(getattr(args, "isl_range", ISL_CONFIG["max_range_km"]))
    switching_delay = float(getattr(args, "switching_delay", ISL_CONFIG["switching_delay_ms"]))
    min_elev = float(getattr(args, "min_elev", 10.0))
    use_fiber = bool(getattr(args, "fiber_baseline", not getattr(args, "no_fiber", False)))
    architecture = str(getattr(args, "architecture", "regenerative-isl"))
    use_dual_hop = bool(getattr(args, "dual_hop", False))
    gateways_arg = str(getattr(args, "gateways", "") or "")

    # Parse gateways
    gateway_list = []
    if use_dual_hop:
        if gateways_arg.strip():
            for part in gateways_arg.split(";"):
                part = part.strip()
                if "," in part:
                    try:
                        glat = float(part.split(",")[0].strip())
                        glon = float(part.split(",")[1].strip())
                        gateway_list.append((f"gw_{glat:.1f}_{glon:.1f}", f"{glat:.1f}, {glon:.1f}", glat, glon))
                    except ValueError:
                        pass
        if not gateway_list:
            try:
                from ..ground_stations import load_gateways
                from ..config import get_settings
                settings = get_settings()
                for gw_obj in load_gateways(settings.outputs_dir):
                    if gw_obj.enabled and "vdes" in gw_obj.freq_bands:
                        gateway_list.append((gw_obj.id, gw_obj.name, gw_obj.latitude, gw_obj.longitude))
            except Exception as e:
                print(f"   Could not load default gateways: {e}")
        print(f"   Dual-hop: {len(gateway_list)} gateways loaded")

    print(f"   Window: {duration_min} min  |  step: {step_min} min  |  snapshots: {n_steps}")
    print(f"   ISL range: {isl_range:.0f} km  |  hop delay: {switching_delay:.1f} ms  |  min-elev: {min_elev:.1f}°")

    # ── Main loop ──────────────────────────────────────────────────────────
    rtt_series: list[float] = []
    dualhop_series: list[float] = []
    rows: list[dict] = []
    representative: Optional[LatencyPathResult] = None

    for step in range(n_steps):
        t = ts.utc(
            t0.utc.year, t0.utc.month, t0.utc.day,
            t0.utc.hour, t0.utc.minute + step * step_min,
        )
        positions = np.array([s.at(t).frame_xyz(itrs).km for s in sats_list])

        if architecture == 'bentpipe':
            adj = None
        else:
            adj = isl_topology_from_walker(
            num_sats=n_sats,
            num_planes=planes_eff,
            positions_km=positions,
            max_range_km=isl_range,
        )

        res = find_min_latency_path(
            sat_positions_km=positions,
            adj_matrix=adj,
            src_lat_deg=src_lat,
            src_lon_deg=src_lon,
            dst_lat_deg=dst_lat,
            dst_lon_deg=dst_lon,
            min_elev_deg=min_elev,
            switching_delay_ms=switching_delay,
            sat_names=sat_names,
        )

        path_found = res is not None and res.num_hops > 0
        rtt = res.total_rtt_ms if path_found else None
        if not path_found and architecture == "store-forward":
            _c = []
            for ts2 in range(step, min(step+120, n_steps)):
                t2 = ts.utc(t0.utc.year, t0.utc.month, t0.utc.day, t0.utc.hour, t0.utc.minute+ts2*step_min)
                p2 = np.array([s.at(t2).frame_xyz(itrs).km for s in sats_list])
                n2 = p2 / np.linalg.norm(p2, axis=1)[:, np.newaxis]
                dc = np.array([np.cos(np.radians(dst_lat))*np.cos(np.radians(dst_lon)), np.cos(np.radians(dst_lat))*np.sin(np.radians(dst_lon)), np.sin(np.radians(dst_lat))])
                for sn in n2:
                    if 90-np.degrees(np.arccos(np.dot(sn, dc))) > min_elev:
                        _c.append((ts2-step)*step_min*60000+10)
                        break
                if _c: break
            if _c: rtt = min(_c); path_found = True

        ow = res.total_one_way_ms if path_found else None
        if path_found:
            rtt_series.append(float(rtt))
            if representative is None:
                representative = res

        # Dual-hop computation
        dualhop_rtt = None
        dualhop_gw = ""
        if use_dual_hop and gateway_list:
            dh = compute_dual_hop_latency(
                sat_positions_km=positions,
                adj_matrix=adj,
                src_lat_deg=src_lat,
                src_lon_deg=src_lon,
                dst_lat_deg=dst_lat,
                dst_lon_deg=dst_lon,
                gateways=gateway_list,
                min_elev_deg=min_elev,
                feeder_min_elev_deg=5.0,
                switching_delay_ms=switching_delay,
                sat_names=sat_names,
                architecture=architecture,
            )
            if dh.path_found:
                dualhop_rtt = dh.total_rtt_ms
                dualhop_gw = dh.feeder_gateway
                dualhop_series.append(dualhop_rtt)

        rows.append({
            "time_min": step * step_min,
            "rtt_ms": "" if rtt is None else f"{rtt:.3f}",
            "one_way_ms": "" if ow is None else f"{ow:.3f}",
            "num_hops": res.num_hops if res is not None else 0,
            "src_visible": res.ground_visible_src if res is not None else 0,
            "dst_visible": res.ground_visible_dst if res is not None else 0,
            "path_found": int(bool(path_found)),
            "uplink_ms": f"{res.uplink_ms:.3f}" if path_found else "",
            "downlink_ms": f"{res.downlink_ms:.3f}" if path_found else "",
            "isl_ms": f"{res.isl_ms:.3f}" if path_found else "",
            "switching_ms": f"{res.switching_ms:.3f}" if path_found else "",
            "dualhop_rtt_ms": "" if dualhop_rtt is None else f"{dualhop_rtt:.3f}",
            "dualhop_gateway": dualhop_gw,
        })

        if (step + 1) % 50 == 0:
            print(f"   processed {step + 1}/{n_steps} snapshots…")

    # ── Stats ──────────────────────────────────────────────────────────────
    rtt_arr = np.array(rtt_series, dtype=float)
    availability_pct = 100.0 * (len(rtt_series) / max(1, n_steps))
    if rtt_arr.size > 0:
        stats = {
            "min_ms":    float(rtt_arr.min()),
            "p5_ms":     float(np.percentile(rtt_arr, 5)),
            "median_ms": float(np.percentile(rtt_arr, 50)),
            "mean_ms":   float(rtt_arr.mean()),
            "p95_ms":    float(np.percentile(rtt_arr, 95)),
            "max_ms":    float(rtt_arr.max()),
            "std_ms":    float(rtt_arr.std()),
        }
    else:
        stats = {k: None for k in
                 ("min_ms", "p5_ms", "median_ms", "mean_ms", "p95_ms", "max_ms", "std_ms")}

    fiber_one_way = fiber_latency_ms(src_lat, src_lon, dst_lat, dst_lon) if use_fiber else None
    fiber_rtt = (fiber_one_way * 2.0) if fiber_one_way is not None else None
    pct_below_fiber = (
        float((rtt_arr < fiber_rtt).mean() * 100.0)
        if fiber_rtt is not None and rtt_arr.size > 0 else None
    )

    great_circle = great_circle_distance_km(src_lat, src_lon, dst_lat, dst_lon)

    # ── Console summary ────────────────────────────────────────────────────
    print()
    print("  📡 SATELLITE RTT (end-to-end)")
    print("  " + "─" * 55)
    if stats["min_ms"] is None:
        print("  No path found at any snapshot (constellation may not reach both endpoints).")
    else:
        print(f"  Minimum                       {stats['min_ms']:.2f} ms")
        print(f"  5th percentile                {stats['p5_ms']:.2f} ms")
        print(f"  Median (P50)                  {stats['median_ms']:.2f} ms")
        print(f"  Mean                          {stats['mean_ms']:.2f} ms")
        print(f"  95th percentile               {stats['p95_ms']:.2f} ms")
        print(f"  Maximum                       {stats['max_ms']:.2f} ms")
        print(f"  Std. deviation                {stats['std_ms']:.2f} ms")
        print(f"  Path availability             {availability_pct:.1f}%")
    if fiber_rtt is not None:
        print()
        print("  FIBER BASELINE")
        print("  " + "─" * 55)
        print(f"  Great-circle distance              {great_circle:.0f} km")
        print(f"  Fiber RTT (routing factor 1.4)     {fiber_rtt:.2f} ms")
        if pct_below_fiber is not None:
            print(f"  % of time satellite RTT < fiber    {pct_below_fiber:.1f}%")

    # ── Outputs ────────────────────────────────────────────────────────────
    suffix = f"{walker_suffix}_to_{dst_lat:.0f}_{dst_lon:.0f}"
    csv_filename = f"latency_{suffix}.csv"
    with open(csv_filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"💾 Saved: {csv_filename}")

    summary = {
        "source": {"lat": src_lat, "lon": src_lon, "raw": args.from_location},
        "destination": {"lat": dst_lat, "lon": dst_lon, "raw": args.to_location},
        "constellation_suffix": walker_suffix,
        "snapshots": n_steps,
        "step_min": step_min,
        "duration_min": duration_min,
        "isl_range_km": isl_range,
        "switching_delay_ms": switching_delay,
        "min_elev_deg": min_elev,
        "availability_pct": float(availability_pct),
        "rtt": stats,
        "fiber": {
            "great_circle_km": float(great_circle),
            "one_way_ms": fiber_one_way,
            "rtt_ms": fiber_rtt,
            "pct_below_fiber": pct_below_fiber,
        } if fiber_rtt is not None else None,
        "representative_path": (
            None if representative is None or representative.num_hops == 0 else {
                "total_one_way_ms": representative.total_one_way_ms,
                "total_rtt_ms": representative.total_rtt_ms,
                "num_hops": representative.num_hops,
                "uplink_ms": representative.uplink_ms,
                "downlink_ms": representative.downlink_ms,
                "isl_ms": representative.isl_ms,
                "switching_ms": representative.switching_ms,
                "hops": [
                    {
                        "type": h.type,
                        "from": h.from_name,
                        "to": h.to_name,
                        "dist_km": h.dist_km,
                        "delay_ms": h.delay_ms,
                    }
                    for h in representative.path
                ],
            }
        ),
    }
    summary_filename = f"latency_{suffix}.json"
    with open(summary_filename, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"💾 Saved: {summary_filename}")

    # Plot
    backend = getattr(args, "backend", "matplotlib")
    _generate_latency_plots(
        rtt_arr,
        p5=stats["p5_ms"] or 0.0,
        p95=stats["p95_ms"] or 0.0,
        median=stats["median_ms"] or 0.0,
        fiber_rtt=fiber_rtt,
        suffix=suffix,
        backend=backend if backend in ("matplotlib", "plotly") else "matplotlib",
    )

    return summary
