#!/bin/bash
#
# Graphics Backend Comparison Demo
# Generates the same visualization using different backends
#

echo "🎨 Graphics Backend Comparison Demo"
echo "===================================="
echo ""
echo "This script will generate the same constellation visualization"
echo "using three different graphics backends to demonstrate the differences."
echo ""

# Configuration
SATS=12
PLANES=3
RES=15
ALTITUDE=600

echo "Configuration:"
echo "  Satellites: $SATS"
echo "  Planes: $PLANES"
echo "  Grid Resolution: ${RES}°"
echo "  Altitude: ${ALTITUDE} km"
echo ""

# Test 1: Matplotlib (default)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  MATPLOTLIB Backend (Static PNG)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
./run.sh --backend matplotlib heatmap --sats $SATS --planes $PLANES --res $RES --altitude $ALTITUDE
echo ""
echo "✅ Matplotlib output: heatmap_vdes_walker_*_${SATS}_${PLANES}.png"
echo ""

# Test 2: Plotly (interactive)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  PLOTLY Backend (Interactive HTML)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
./run.sh --backend plotly heatmap --sats $SATS --planes $PLANES --res $RES --altitude $ALTITUDE
echo ""
echo "✅ Plotly output: heatmap_vdes_walker_*_${SATS}_${PLANES}.html"
echo "   Open in browser to zoom/pan interactively!"
echo ""

# Test 3: 3D Orbit with Plotly
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  PLOTLY 3D Orbit View"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
./run.sh --backend plotly orbit --sats $SATS --planes $PLANES --altitude $ALTITUDE --duration 120
echo ""
echo "✅ 3D Orbit: orbit_walker_*_${SATS}_${PLANES}.html"
echo "   Rotate with mouse, zoom with scroll wheel!"
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Generated files:"
ls -lh heatmap_vdes_walker_*_${SATS}_${PLANES}.* orbit_walker_*_${SATS}_${PLANES}.* 2>/dev/null | tail -10
echo ""
echo "Backend Comparison:"
echo "┌─────────────┬───────────┬──────────────┬─────────────────┐"
echo "│ Backend     │ File Type │ File Size    │ Interactivity   │"
echo "├─────────────┼───────────┼──────────────┼─────────────────┤"
echo "│ matplotlib  │ PNG       │ ~1-3 MB      │ None (static)   │"
echo "│ plotly      │ HTML      │ ~3-8 MB      │ Full (3D/zoom)  │"
echo "│ bokeh       │ HTML      │ ~2-5 MB      │ Medium (2D)     │"
echo "└─────────────┴───────────┴──────────────┴─────────────────┘"
echo ""
echo "🌐 To view interactive HTML files:"
echo "   firefox heatmap_vdes_walker_*_${SATS}_${PLANES}.html"
echo "   firefox orbit_walker_*_${SATS}_${PLANES}.html"
echo ""
echo "📖 Full documentation: documentation/graphics_backends.md"
echo ""
