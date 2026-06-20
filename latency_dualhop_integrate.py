"""Add dual-hop and gateway support to sim/modes/latency.py"""
import re

PATH = "/home/lusospace/constellation_simulator/sim/modes/latency.py"
with open(PATH) as f:
    content = f.read()

# 1. Add import for dual-hop
content = content.replace(
    "from ..routing import find_min_latency_path, LatencyPathResult, fiber_latency_ms",
    "from ..routing import find_min_latency_path, LatencyPathResult, fiber_latency_ms, compute_dual_hop_latency, DualHopResult"
)

# 2. Add gateway loading + dual-hop config after architecture line
old_params = """    architecture = str(getattr(args, \"architecture\", \"regenerative-isl\"))\n\n    print(f\"   Window: {duration_min} min\"""

new_params = """    architecture = str(getattr(args, \"architecture\", \"regenerative-isl\"))
    use_dual_hop = bool(getattr(args, \"dual_hop\", False))
    gateways_arg = getattr(args, \"gateways\", None) or \"\"

    # Parse gateways: either from --gateways flag or default list
    gateway_list: list[tuple[str, str, float, float]] = []
    if use_dual_hop:
        if gateways_arg.strip():
            for part in gateways_arg.split(\";\"):
                part = part.strip()
                if \",\" in part:
                    lat_str, lon_str = part.split(\",\", 1)
                    try:
                        glat, glon = float(lat_str.strip()), float(lon_str.strip())
                        gw_id = f\"gw_{glat:.1f}_{glon:.1f}\"
                        gw_name = f\"{glat:.1f}, {glon:.1f}\"
                        gateway_list.append((gw_id, gw_name, glat, glon))
                    except ValueError:
                        pass
        # Fall back to default gateways from ground_stations module
        if not gateway_list:
            try:
                from ..ground_stations import load_gateways, get_feeder_link_gateways
                from ..config import get_settings
                settings = get_settings()
                gws = load_gateways(settings.outputs_dir)
                for gw in get_feeder_link_gateways(gws, \"vdes\"):
                    gateway_list.append((gw.id, gw.name, gw.latitude, gw.longitude))
            except Exception as e:
                print(f\"   Could not load default gateways: {e}\")
        print(f\"   Dual-hop: {len(gateway_list)} gateways loaded\")

    print(f\"   Window: {duration_min} min\""""

content = content.replace(old_params, new_params)

# 3. Run dual-hop computation alongside existing latency
old_loop = """\n    for step in range(n_steps):"""

new_loop = """\n    # ── Dual-hop series (if enabled) ──────────────────────────────────────
    dualhop_series: list[float] = []
    feeder_gateway_series: list[str] = []

    for step in range(n_steps):"""

content = content.replace(old_loop, new_loop, 1)  # only replace first occurrence

# 4. After computing single-path latency, also compute dual-hop
old_row_append = """        rows.append({
            \"time_min\": step * step_min,
            \"rtt_ms\": \"\" if rtt is None else f\"{rtt:.3f}\",
            \"one_way_ms\": \"\" if ow is None else f\"{ow:.3f}\",
            \"num_hops\": res.num_hops if res is not None else 0,
            \"src_visible\": res.ground_visible_src if res is not None else 0,
            \"dst_visible\": res.ground_visible_dst if res is not None else 0,
            \"path_found\": int(bool(path_found)),
            \"uplink_ms\": f\"{res.uplink_ms:.3f}\" if path_found else \"\",
            \"downlink_ms\": f\"{res.downlink_ms:.3f}\" if path_found else \"\",
            \"isl_ms\": f\"{res.isl_ms:.3f}\" if path_found else \"\",
            \"switching_ms\": f\"{res.switching_ms:.3f}\" if path_found else \"\",
        })"""

new_row_append = """        # Dual-hop computation (if enabled)
        dualhop_rtt = None
        dualhop_gw = ""
        if use_dual_hop and gateway_list and architecture != "bentpipe":
            dh = compute_dual_hop_latency(
                sat_positions_km=positions,
                adj_matrix=adjacency,
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
                feeder_gateway_series.append(dualhop_gw)
        elif use_dual_hop and gateway_list and architecture == "bentpipe":
            # Bent-pipe dual-hop: user -> sat -> gateway (simplified)
            dh = compute_dual_hop_latency(
                sat_positions_km=positions,
                adj_matrix=None,
                src_lat_deg=src_lat,
                src_lon_deg=src_lon,
                dst_lat_deg=dst_lat,
                dst_lon_deg=dst_lon,
                gateways=gateway_list,
                min_elev_deg=min_elev,
                feeder_min_elev_deg=5.0,
                switching_delay_ms=0,
                sat_names=sat_names,
                architecture="bentpipe",
            )
            if dh.path_found:
                dualhop_rtt = dh.total_rtt_ms
                dualhop_gw = dh.feeder_gateway
                dualhop_series.append(dualhop_rtt)
                feeder_gateway_series.append(dualhop_gw)

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
        })"""

content = content.replace(old_row_append, new_row_append)

# 5. Update CSV header and stats section
content = content.replace(
    '"time_min","rtt_ms","one_way_ms","num_hops","src_visible","dst_visible","path_found","uplink_ms","downlink_ms","isl_ms","switching_ms"',
    '"time_min","rtt_ms","one_way_ms","num_hops","src_visible","dst_visible","path_found","uplink_ms","downlink_ms","isl_ms","switching_ms","dualhop_rtt_ms","dualhop_gateway"'
)

with open(PATH, "w") as f:
    f.write(content)

print("Dual-hop + gateways integrated into run_latency()")
