"""
3D orbit visualization helpers: continent drawing, coverage circles,
and the plotly-based interactive orbit plot.
"""

import os
import json
import numpy as np
from datetime import timedelta

from .. import backends
from ..constants import VISUALIZATION_SETTINGS, COASTLINE_FILE
from ..constellation import calculate_coverage_footprint

COASTLINE_DOWNLOAD_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector"
    "/master/geojson/ne_110m_coastline.geojson"
)


# ---------------------------------------------------------------------------
# Matplotlib helpers
# ---------------------------------------------------------------------------

def draw_coastline_segment(ax, coords, rotation_deg, earth_radius):
    """Draw a single coastline segment on the 3D sphere as a filled polygon"""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    if len(coords) < 3:
        return

    step = max(1, len(coords) // 100)
    coords = coords[::step]

    lons, lats = zip(*coords)
    lons = np.array(lons) + rotation_deg
    lats = np.array(lats)

    lat_rad = np.radians(lats)
    lon_rad = np.radians(lons)

    continent_radius = earth_radius * 1.01

    x = continent_radius * np.cos(lat_rad) * np.cos(lon_rad)
    y = continent_radius * np.cos(lat_rad) * np.sin(lon_rad)
    z = continent_radius * np.sin(lat_rad)

    verts = [list(zip(x, y, z))]
    poly = Poly3DCollection(
        verts,
        alpha=VISUALIZATION_SETTINGS['continents']['alpha'],
        facecolor=VISUALIZATION_SETTINGS['continents']['fill_color'],
        edgecolor=VISUALIZATION_SETTINGS['continents']['edge_color'],
        linewidth=VISUALIZATION_SETTINGS['continents']['edge_width'],
        zsort='average'
    )
    ax.add_collection3d(poly)
    ax.plot(x, y, z, color='yellow', linewidth=2, alpha=1.0)


def draw_continents_on_sphere(ax, rotation_deg=0):
    """Draw continent outlines on a 3D matplotlib sphere"""
    earth_radius = 6378.137

    if os.path.exists(COASTLINE_FILE):
        try:
            with open(COASTLINE_FILE, 'r') as f:
                data = json.load(f)

            for feature in data['features']:
                geom = feature['geometry']
                if geom['type'] == 'LineString':
                    draw_coastline_segment(ax, geom['coordinates'], rotation_deg, earth_radius)
                elif geom['type'] == 'MultiLineString':
                    for segment in geom['coordinates']:
                        draw_coastline_segment(ax, segment, rotation_deg, earth_radius)

            return True

        except Exception as e:
            print(f"⚠️  Error reading coastline data: {e}")
            print("   Delete coastline.json in assets/ and re-run to download fresh data")
            return False
    else:
        import urllib.request
        print("🌍 Downloading Natural Earth coastline data...")
        try:
            os.makedirs(os.path.dirname(COASTLINE_FILE), exist_ok=True)
            urllib.request.urlretrieve(COASTLINE_DOWNLOAD_URL, COASTLINE_FILE)
            print("✅ Coastline data downloaded")
            return draw_continents_on_sphere(ax, rotation_deg)
        except Exception as e:
            print(f"❌ Download failed: {e}")
            return False


def draw_coverage_circle_on_sphere(ax, lat_deg, lon_deg, radius_km, color=None, alpha=None):
    """Draw a coverage circle on the 3D Earth sphere. Returns (line, polygon)."""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    if color is None:
        color = VISUALIZATION_SETTINGS['beams']['color']
    if alpha is None:
        alpha = VISUALIZATION_SETTINGS['beams']['alpha']

    earth_radius = 6378.137
    lat_rad = np.radians(lat_deg)
    lon_rad = np.radians(lon_deg)
    ang_radius = radius_km / earth_radius

    num_points = 24
    angles = np.linspace(0, 2 * np.pi, num_points)

    circle_lats, circle_lons = [], []
    for angle in angles:
        lat_new = np.arcsin(np.sin(lat_rad) * np.cos(ang_radius) +
                            np.cos(lat_rad) * np.sin(ang_radius) * np.cos(angle))
        lon_new = lon_rad + np.arctan2(np.sin(angle) * np.sin(ang_radius) * np.cos(lat_rad),
                                        np.cos(ang_radius) - np.sin(lat_rad) * np.sin(lat_new))
        circle_lats.append(lat_new)
        circle_lons.append(lon_new)

    circle_lats = np.array(circle_lats)
    circle_lons = np.array(circle_lons)

    x = earth_radius * np.cos(circle_lats) * np.cos(circle_lons)
    y = earth_radius * np.cos(circle_lats) * np.sin(circle_lons)
    z = earth_radius * np.sin(circle_lats)

    line, = ax.plot(x, y, z, color=color, alpha=alpha, linewidth=2.5, zorder=10)

    verts = [list(zip(x, y, z))]
    poly = Poly3DCollection(verts, alpha=alpha * 0.5, facecolor=color,
                            edgecolor='none', zorder=5)
    ax.add_collection3d(poly)

    return line, poly


# ---------------------------------------------------------------------------
# Plotly interactive orbit plot
# ---------------------------------------------------------------------------

def _create_coverage_circle_plotly(lat_deg, lon_deg, radius_km):
    """Create coverage circle on Earth sphere for plotly 3D visualization"""
    earth_radius = 6378.137
    lat_rad = np.radians(lat_deg)
    lon_rad = np.radians(lon_deg)
    ang_radius = radius_km / earth_radius

    num_points = 24
    angles = np.linspace(0, 2 * np.pi, num_points)
    circle_lats, circle_lons = [], []

    for angle in angles:
        lat_new = np.arcsin(np.sin(lat_rad) * np.cos(ang_radius) +
                            np.cos(lat_rad) * np.sin(ang_radius) * np.cos(angle))
        lon_new = lon_rad + np.arctan2(np.sin(angle) * np.sin(ang_radius) * np.cos(lat_rad),
                                        np.cos(ang_radius) - np.sin(lat_rad) * np.sin(lat_new))
        circle_lats.append(lat_new)
        circle_lons.append(lon_new)

    circle_lats = np.array(circle_lats)
    circle_lons = np.array(circle_lons)
    x = earth_radius * np.cos(circle_lats) * np.cos(circle_lons)
    y = earth_radius * np.cos(circle_lats) * np.sin(circle_lons)
    z = earth_radius * np.sin(circle_lats)
    return x, y, z


def _create_coverage_fill_plotly(lat_deg, lon_deg, radius_km, color, opacity=0.25):
    """Create a filled spherical cap as go.Mesh3d for Plotly 3D.
    Uses a triangulated fan from the nadir (sub-satellite) point on the
    Earth surface to the coverage-circle edge points.
    """
    import plotly.graph_objects as go

    earth_radius = 6378.137
    lat_rad = np.radians(lat_deg)
    lon_rad = np.radians(lon_deg)
    ang_radius = radius_km / earth_radius

    # Nadir point — centre of the cap on the Earth surface
    cx0 = earth_radius * np.cos(lat_rad) * np.cos(lon_rad)
    cy0 = earth_radius * np.cos(lat_rad) * np.sin(lon_rad)
    cz0 = earth_radius * np.sin(lat_rad)

    num_points = 36
    angles = np.linspace(0, 2 * np.pi, num_points, endpoint=False)
    circle_lats, circle_lons = [], []
    for angle in angles:
        lat_new = np.arcsin(np.sin(lat_rad) * np.cos(ang_radius) +
                            np.cos(lat_rad) * np.sin(ang_radius) * np.cos(angle))
        lon_new = lon_rad + np.arctan2(np.sin(angle) * np.sin(ang_radius) * np.cos(lat_rad),
                                        np.cos(ang_radius) - np.sin(lat_rad) * np.sin(lat_new))
        circle_lats.append(lat_new)
        circle_lons.append(lon_new)

    circle_lats = np.array(circle_lats)
    circle_lons = np.array(circle_lons)
    ex = earth_radius * np.cos(circle_lats) * np.cos(circle_lons)
    ey = earth_radius * np.cos(circle_lats) * np.sin(circle_lons)
    ez = earth_radius * np.sin(circle_lats)

    # Vertices: index 0 = nadir centre, indices 1..N = edge ring
    xs = np.concatenate([[cx0], ex])
    ys = np.concatenate([[cy0], ey])
    zs = np.concatenate([[cz0], ez])

    # Fan triangulation: (0, i, i+1) with wraparound on the last triangle
    ii = [0] * num_points
    jj = list(range(1, num_points + 1))
    kk = list(range(2, num_points + 1)) + [1]

    return go.Mesh3d(
        x=xs, y=ys, z=zs,
        i=ii, j=jj, k=kk,
        color=color,
        opacity=opacity,
        showscale=False,
        hoverinfo='skip',
        flatshading=True,
        lighting=dict(ambient=1.0, diffuse=0.0, specular=0.0),
        showlegend=False,
    )


def create_3d_orbit_plot(sats, args, inc, walker_suffix, metrics=None, tco_data=None,
                         shell_map=None, shell_meta=None, shell_coverage_radii=None):
    """Create interactive plotly 3D orbit visualization.

    Args:
        sats                : list of EarthSatellite objects
        args                : parsed CLI args
        inc                 : inclination (float or None for multi-shell)
        walker_suffix       : filename suffix string
        metrics             : single-shell metrics dict (or None)
        tco_data            : TCO dict (or None)
        shell_map           : dict sat_name → shell_index (multi-shell only)
        shell_meta          : list of shell metadata dicts (multi-shell only)
        shell_coverage_radii: dict shell_index → coverage_radius_km (multi-shell only)
    """
    backends.load_backend_modules('plotly')
    if not backends.plotly_available:
        print("ℹ️  Plotly unavailable, falling back to matplotlib.")
        return

    import plotly.graph_objects as go
    from skyfield.api import load

    ts = load.timescale()
    t0 = ts.utc(2024, 1, 1, 12, 0, 0)

    # ── Colour palette ──────────────────────────────────────────────────────
    # 12 visually distinct colours for single-shell cycle or shell colouring
    SHELL_COLORS = [
        '#00d4ff',   # cyan
        '#ff6b35',   # orange
        '#7eff6b',   # lime
        '#ff4da6',   # pink
        '#a78bfa',   # violet
        '#fbbf24',   # amber
        '#34d399',   # emerald
        '#f87171',   # red
        '#60a5fa',   # blue
        '#e879f9',   # fuchsia
        '#4ade80',   # green
        '#fb923c',   # orange-red
    ]

    is_multi_shell = shell_map is not None and shell_meta is not None

    # Max sats cap (CLI --max-sats or default 250)
    max_sats = getattr(args, 'max_sats', 250)
    num_sats = min(len(sats), max_sats)

    show_trails = getattr(args, 'trails', False)
    show_map    = getattr(args, 'map', False)
    show_beams  = getattr(args, 'beams', False)
    show_fill   = getattr(args, 'fill', False)

    # Build per-satellite colour list
    sat_colors = []
    if is_multi_shell:
        for sat in sats[:num_sats]:
            sidx = shell_map.get(sat.name, 0)
            sat_colors.append(SHELL_COLORS[sidx % len(SHELL_COLORS)])
    else:
        for i in range(num_sats):
            sat_colors.append(SHELL_COLORS[i % len(SHELL_COLORS)])

    # Auto-reduce frames for large constellations (performance)
    num_frames = 20 if num_sats > 100 else (30 if show_beams else 60)

    print(f"🎨 Generating interactive 3D orbit plot ({num_sats} satellites, {num_frames} frames)...")

    # Pre-calculate satellite positions
    all_sat_positions = []
    for sat in sats[:num_sats]:
        traj = []
        for minutes in range(0, args.duration + 1, 2):
            t = ts.utc(t0.utc_datetime() + timedelta(minutes=minutes))
            pos = sat.at(t).position.km
            traj.append(pos)
        all_sat_positions.append(np.array(traj))

    # Initial traces: satellite markers (+ optional trails)
    # In multi-shell mode: one legend group per shell; in single-shell: one entry per sat
    traces = []
    _legend_shells_shown = set()   # track which shell legend entries are already added

    for i in range(num_sats):
        color = sat_colors[i]
        if is_multi_shell:
            sat_name  = sats[i].name
            sidx      = shell_map.get(sat_name, 0)
            smeta     = shell_meta[sidx] if sidx < len(shell_meta) else {}
            leg_label = smeta.get('label', f'Shell {sidx+1}')
            show_leg  = sidx not in _legend_shells_shown
            if show_leg:
                _legend_shells_shown.add(sidx)
            leg_group = f"shell_{sidx}"
        else:
            leg_label = f"Sat {i+1}"
            show_leg  = True
            leg_group = f"sat_{i}"

        traces.append(go.Scatter3d(
            x=[all_sat_positions[i][0, 0]],
            y=[all_sat_positions[i][0, 1]],
            z=[all_sat_positions[i][0, 2]],
            mode='markers',
            marker=dict(size=5 if is_multi_shell else 8, color=color),
            name=leg_label,
            legendgroup=leg_group,
            showlegend=show_leg,
        ))
        if show_trails:
            traces.append(go.Scatter3d(
                x=[all_sat_positions[i][0, 0]],
                y=[all_sat_positions[i][0, 1]],
                z=[all_sat_positions[i][0, 2]],
                mode='lines',
                line=dict(width=1, color=sat_colors[i]),
                showlegend=False,
                hoverinfo='skip'
            ))

    # Earth sphere
    R_earth = 6378.137
    u, v = np.mgrid[0:2*np.pi:50j, 0:np.pi:25j]
    x = R_earth * np.cos(u) * np.sin(v)
    y = R_earth * np.sin(u) * np.sin(v)
    z = R_earth * np.cos(v)

    # Load coastline data once for map mode
    coastline_data = None
    coastline_file = COASTLINE_FILE

    if show_map:
        if not os.path.exists(coastline_file):
            import urllib.request
            print("🌍 Downloading Natural Earth coastline data...")
            try:
                os.makedirs(os.path.dirname(coastline_file), exist_ok=True)
                urllib.request.urlretrieve(COASTLINE_DOWNLOAD_URL, coastline_file)
                print("✅ Coastline data downloaded")
            except Exception as e:
                print(f"❌ Download failed: {e}, using solid Earth")
                show_map = False

        if show_map and os.path.exists(coastline_file):
            try:
                with open(coastline_file, 'r') as f:
                    coastline_data = json.load(f)
            except Exception as e:
                print(f"⚠️  Could not load coastline data: {e}")
                show_map = False

    def _add_earth_to_traces(trace_list, x_rot, y_rot, z_rot, earth_rotation, c_data, s_map, s_beams):
        """Append Earth surface + continent traces to trace_list"""
        if s_map and c_data:
            trace_list.append(go.Surface(
                x=x_rot, y=y_rot, z=z_rot,
                colorscale=[[0, '#0077be'], [1, '#0077be']],
                showscale=False, name='Ocean', opacity=0.9, hoverinfo='skip'
            ))
            if s_beams:
                all_cx, all_cy, all_cz = [], [], []
                for feature in list(c_data['features'])[:50]:
                    geom = feature['geometry']
                    coords_list = ([geom['coordinates']] if geom['type'] == 'LineString'
                                   else geom['coordinates'])
                    for coords in coords_list:
                        for i, (lon, lat) in enumerate(coords):
                            if i % 2 == 0:
                                rlon = lon + earth_rotation
                                if rlon > 180: rlon -= 360
                                elif rlon < -180: rlon += 360
                                lr = np.radians(lat)
                                lonr = np.radians(rlon)
                                cr = R_earth * 1.005
                                all_cx.append(cr * np.cos(lr) * np.cos(lonr))
                                all_cy.append(cr * np.cos(lr) * np.sin(lonr))
                                all_cz.append(cr * np.sin(lr))
                        all_cx.append(None); all_cy.append(None); all_cz.append(None)
                if all_cx:
                    trace_list.append(go.Scatter3d(
                        x=all_cx, y=all_cy, z=all_cz, mode='lines',
                        line=dict(width=2, color='black'),
                        showlegend=False, hoverinfo='skip'
                    ))
            else:
                for feature in c_data['features']:
                    geom = feature['geometry']
                    coords_list = ([geom['coordinates']] if geom['type'] == 'LineString'
                                   else geom['coordinates'])
                    for coords in coords_list:
                        cx, cy, cz = [], [], []
                        for lon, lat in coords:
                            rlon = lon + earth_rotation
                            if rlon > 180: rlon -= 360
                            elif rlon < -180: rlon += 360
                            lr = np.radians(lat); lonr = np.radians(rlon)
                            cr = R_earth * 1.005
                            cx.append(cr * np.cos(lr) * np.cos(lonr))
                            cy.append(cr * np.cos(lr) * np.sin(lonr))
                            cz.append(cr * np.sin(lr))
                        trace_list.append(go.Scatter3d(
                            x=cx, y=cy, z=cz, mode='lines',
                            line=dict(width=2, color='black'),
                            showlegend=False, hoverinfo='skip'
                        ))
        else:
            trace_list.append(go.Surface(
                x=x_rot, y=y_rot, z=z_rot,
                colorscale=[[0, 'lightblue'], [1, 'lightblue']],
                showscale=False, name='Earth', opacity=0.8, hoverinfo='skip'
            ))

    # Add initial Earth
    _add_earth_to_traces(traces, x, y, z, 0, coastline_data, show_map, show_beams)

    # Coverage beams at t=0
    # In multi-shell mode: per-satellite coverage radius from shell_coverage_radii
    # In single-shell mode: one radius for all sats
    coverage_radius = None   # single-shell fallback
    if show_beams:
        min_elev = getattr(args, 'min_elev', 10.0)
        if not is_multi_shell:
            coverage_radius = calculate_coverage_footprint(args.altitude, min_elev)
            print(f"🎯 Coverage beams: radius={coverage_radius:.1f} km @ {min_elev}° elevation")
        else:
            print(f"🎯 Coverage beams: per-shell radii @ {min_elev}° elevation")
        if show_fill:
            print("🎨 Coverage fill: semi-transparent caps enabled")
        for i in range(num_sats):
            # Resolve per-satellite coverage radius
            if is_multi_shell and shell_coverage_radii:
                sidx = shell_map.get(sats[i].name, 0)
                cr_km = shell_coverage_radii.get(sidx, coverage_radius or 1000.0)
            else:
                cr_km = coverage_radius
            sp = all_sat_positions[i][0]
            r = np.sqrt(sp[0]**2 + sp[1]**2 + sp[2]**2)
            lat = np.degrees(np.arcsin(sp[2] / r))
            lon = np.degrees(np.arctan2(sp[1], sp[0]))
            cx, cy, cz = _create_coverage_circle_plotly(lat, lon, cr_km)
            traces.append(go.Scatter3d(
                x=cx, y=cy, z=cz, mode='lines',
                line=dict(width=1 if is_multi_shell else 2, color=sat_colors[i]),
                showlegend=False, hoverinfo='skip', opacity=0.6
            ))
            if show_fill:
                traces.append(_create_coverage_fill_plotly(
                    lat, lon, cr_km,
                    color=sat_colors[i], opacity=0.18
                ))

    fig = go.Figure(data=traces)

    # Build animation frames
    degrees_per_minute = 360.0 / (24.0 * 60.0)
    total_rotation = degrees_per_minute * args.duration

    print(f"🔄 Generating animation ({num_frames} frames, {total_rotation:.1f}° total)...")

    frames = []
    for frame_idx in range(num_frames):
        earth_rotation = (total_rotation / num_frames) * frame_idx
        current_time_minutes = (args.duration / num_frames) * frame_idx
        time_idx = min(int(current_time_minutes / 2), len(all_sat_positions[0]) - 1)

        rot_rad = np.radians(earth_rotation)
        x_rot = R_earth * (np.cos(u) * np.cos(rot_rad) - np.sin(u) * np.sin(rot_rad)) * np.sin(v)
        y_rot = R_earth * (np.cos(u) * np.sin(rot_rad) + np.sin(u) * np.cos(rot_rad)) * np.sin(v)
        z_rot = R_earth * np.cos(v)

        fd = []

        for i in range(num_sats):
            fd.append(go.Scatter3d(
                x=[all_sat_positions[i][time_idx, 0]],
                y=[all_sat_positions[i][time_idx, 1]],
                z=[all_sat_positions[i][time_idx, 2]],
                mode='markers',
                marker=dict(size=5 if is_multi_shell else 8, color=sat_colors[i]),
                name=sats[i].name if not is_multi_shell else (
                    shell_meta[shell_map.get(sats[i].name, 0)].get('label', f'Shell {shell_map.get(sats[i].name, 0)+1}')
                    if shell_map.get(sats[i].name, 0) not in {shell_map.get(sats[j].name, 0) for j in range(i)} else
                    shell_meta[shell_map.get(sats[i].name, 0)].get('label', '')
                ),
                legendgroup=f"shell_{shell_map.get(sats[i].name, 0)}" if is_multi_shell else f"sat_{i}",
                showlegend=False,   # legend shown in initial traces only
            ))

        if show_trails:
            for i in range(num_sats):
                trail_start = max(0, time_idx - 15)
                fd.append(go.Scatter3d(
                    x=all_sat_positions[i][trail_start:time_idx+1, 0],
                    y=all_sat_positions[i][trail_start:time_idx+1, 1],
                    z=all_sat_positions[i][trail_start:time_idx+1, 2],
                    mode='lines',
                    line=dict(width=1, color=sat_colors[i]),
                    showlegend=False, hoverinfo='skip'
                ))

        if show_beams and (coverage_radius or is_multi_shell):
            for i in range(num_sats):
                if is_multi_shell and shell_coverage_radii:
                    sidx = shell_map.get(sats[i].name, 0)
                    cr_km = shell_coverage_radii.get(sidx, 1000.0)
                else:
                    cr_km = coverage_radius
                sp = all_sat_positions[i][time_idx]
                r = np.sqrt(sp[0]**2 + sp[1]**2 + sp[2]**2)
                lat = np.degrees(np.arcsin(sp[2] / r))
                lon = np.degrees(np.arctan2(sp[1], sp[0]))
                rlon = lon - earth_rotation
                if rlon > 180: rlon -= 360
                elif rlon < -180: rlon += 360
                cx, cy, cz = _create_coverage_circle_plotly(lat, rlon, cr_km)
                fd.append(go.Scatter3d(
                    x=cx, y=cy, z=cz, mode='lines',
                    line=dict(width=1 if is_multi_shell else 2, color=sat_colors[i]),
                    showlegend=False, hoverinfo='skip', opacity=0.6
                ))
                if show_fill:
                    fd.append(_create_coverage_fill_plotly(
                        lat, rlon, cr_km,
                        color=sat_colors[i], opacity=0.18
                    ))

        _add_earth_to_traces(fd, x_rot, y_rot, z_rot, earth_rotation,
                             coastline_data, show_map, show_beams)

        frame_layout = go.Layout(annotations=[{
            'text': f'⏱️ Time: {current_time_minutes:.1f} min ({current_time_minutes/60:.2f} hr)',
            'showarrow': False, 'xref': 'paper', 'yref': 'paper',
            'x': 0.5, 'y': 0.98, 'xanchor': 'center', 'yanchor': 'top',
            'font': {'size': 16, 'color': 'black'},
            'bgcolor': 'rgba(255,255,255,0.8)', 'bordercolor': 'black',
            'borderwidth': 2, 'borderpad': 8
        }])

        frames.append(go.Frame(data=fd, layout=frame_layout, name=str(frame_idx)))

    fig.frames = frames

    fig.update_layout(
        title=(
            f"Multi-Shell Constellation | {walker_suffix} | {num_sats} sats / {len(shell_meta)} shells"
            if is_multi_shell else
            f"3D Orbit View | {walker_suffix}" + (" | Earth Rotation Physics" if show_map else "")
        ),
        scene=dict(
            xaxis_title='X (km)', yaxis_title='Y (km)', zaxis_title='Z (km)',
            aspectmode='data', camera=dict(eye=dict(x=1.5, y=0, z=0.5))
        ),
        width=1200, height=900,
        updatemenus=[{
            'type': 'buttons', 'showactive': False,
            'buttons': [
                {'label': '▶ Play', 'method': 'animate',
                 'args': [None, {'frame': {'duration': 200, 'redraw': True},
                                 'fromcurrent': True, 'transition': {'duration': 100}}]},
                {'label': '⏸ Pause', 'method': 'animate',
                 'args': [[None], {'frame': {'duration': 0, 'redraw': False},
                                   'mode': 'immediate', 'transition': {'duration': 0}}]}
            ],
            'x': 0.1, 'y': 0, 'xanchor': 'left', 'yanchor': 'bottom'
        }],
        sliders=[{
            'active': 0,
            'steps': [
                {'args': [[f.name], {'frame': {'duration': 0, 'redraw': True},
                                     'mode': 'immediate', 'transition': {'duration': 0}}],
                 'label': f'{(args.duration / num_frames) * i:.0f} min', 'method': 'animate'}
                for i, f in enumerate(frames)
            ],
            'x': 0.1, 'len': 0.85, 'xanchor': 'left', 'y': 0, 'yanchor': 'top',
            'pad': {'b': 10, 't': 50},
            'currentvalue': {'visible': True, 'prefix': 'Time: ', 'suffix': ' min', 'xanchor': 'right'}
        }]
    )

    html_filename = f"orbit_{walker_suffix}.html"
    fig.write_html(html_filename)
    print(f"💾 Saved interactive 3D: {html_filename}")
    print(f"   🌍 Earth rotation: {total_rotation:.1f}° over {args.duration} min")
    if is_multi_shell:
        print(f"   🌐 Multi-shell: {len(shell_meta)} shells, {num_sats} satellites rendered")
        for sm in shell_meta:
            cr = (shell_coverage_radii or {}).get(sm['index'])
            cr_str = f", coverage {cr:.0f} km" if cr else ""
            print(f"      Shell {sm['index']+1}: {sm['label']} — {sm['sats']} sats{cr_str}")
    else:
        print(f"   🛰️  {num_sats} satellites tracked")
    if show_trails:
        print("   ✨ Satellite trails enabled (30-minute history)")
    if show_beams:
        min_elev = getattr(args, 'min_elev', 10.0)
        fill_note = " + filled caps" if show_fill else ""
        if coverage_radius:
            print(f"   📡 Coverage beams: {coverage_radius:.0f} km radius @ {min_elev}°{fill_note}")
        else:
            print(f"   📡 Coverage beams: per-shell @ {min_elev}°{fill_note}")
    print("   🖱️  Mouse controls: Left-drag=rotate, Right-drag=pan, Scroll=zoom")

    if metrics and tco_data:
        print("\n" + "="*80)
        print("📊 CONSTELLATION SUMMARY")
        print("="*80)
        c = metrics['constellation']
        o = metrics['orbital']
        cov = metrics['coverage']
        tc = tco_data['total_costs']
        print(f"\n🛰️  Configuration: {c['total_satellites']} satellites in {c['num_planes']} planes @ {c['altitude_km']:.0f} km")
        print(f"🌍 Orbital Period: {o['period_min']:.1f} min ({o['period_min']/60:.2f} hr)")
        print(f"📶 Coverage: {cov['radius_km']:.0f} km radius ({cov['coverage_per_sat_pct']:.2f}% Earth per sat)")
        print(f"💰 Total TCO (15 years): ${tc['total_tco']:.1f}M (${tc['cost_per_sat_per_year']:.3f}M/sat/year)")
        print("="*80 + "\n")
