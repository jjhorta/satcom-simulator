# Graphics Backends Guide

The constellation simulator now supports multiple graphics backends for enhanced visualization and interactivity.

## Available Backends

### 1. **matplotlib** (Default)
- **Type:** Static image generation
- **Output:** PNG files
- **Best for:** 
  - Publication-quality static images
  - Batch processing and automation
  - When no interactivity is needed
- **Installation:** `pip install matplotlib`

**Example:**
```bash
python satsim_radio.py --backend matplotlib heatmap --sats 12 --planes 3
```

### 2. **plotly** (Recommended for 3D)
- **Type:** Interactive HTML visualization
- **Output:** HTML files with JavaScript interactivity
- **Best for:**
  - 3D orbit visualizations with rotation/zoom/pan
  - Interactive data exploration
  - Sharing visualizations via web browser
- **Installation:** `pip install plotly`

**Features:**
- Fully interactive 3D orbit views
- Rotate, zoom, and pan with mouse
- Interactive heatmaps with hover tooltips
- Export to static images (requires kaleido)

**Example:**
```bash
# Interactive 3D orbit view
python satsim_radio.py --backend plotly orbit --sats 12 --planes 3

# Interactive heatmap
python satsim_radio.py --backend plotly heatmap --sats 24 --planes 4 --res 5
```

### 3. **bokeh** (Optimized for 2D)
- **Type:** Interactive HTML visualization
- **Output:** HTML files with JavaScript interactivity
- **Best for:**
  - Fast interactive 2D heatmaps
  - Large datasets with hover tooltips
  - Lightweight interactive plots
- **Installation:** `pip install bokeh`

**Features:**
- Fast rendering for large grids
- Hover tooltips showing exact values
- Pan and zoom capabilities
- Optimized for 2D visualizations

**Example:**
```bash
python satsim_radio.py --backend bokeh heatmap --sats 12 --planes 3 --res 2
```

## Installation

### Install all backends:
```bash
pip install -r requirements.txt
```

### Install specific backends:
```bash
# Matplotlib only (default)
pip install matplotlib numpy skyfield Pillow

# Add Plotly for interactive 3D
pip install plotly

# Add Bokeh for interactive 2D
pip install bokeh

# Optional: Static image export for Plotly
pip install kaleido
```

## Usage Examples

### Heatmap Comparison

**Static PNG (matplotlib):**
```bash
python satsim_radio.py --backend matplotlib heatmap --sats 97 --planes 11 --res 2
# Output: heatmap_vdes_walker_87_97_11.png (static image)
```

**Interactive HTML (plotly):**
```bash
python satsim_radio.py --backend plotly heatmap --sats 97 --planes 11 --res 2
# Output: heatmap_vdes_walker_87_97_11.html (interactive, zoomable)
```

**Optimized 2D (bokeh):**
```bash
python satsim_radio.py --backend bokeh heatmap --sats 97 --planes 11 --res 2
# Output: heatmap_vdes_walker_87_97_11.html (fast rendering)
```

### 3D Orbit Visualization

**Best with Plotly:**
```bash
python satsim_radio.py --backend plotly orbit --sats 24 --planes 4 --duration 360
# Output: orbit_walker_87_24_4.html
# Open in browser and use mouse to:
#   - Left click + drag: Rotate
#   - Right click + drag: Pan
#   - Scroll wheel: Zoom
```

**Static with Matplotlib:**
```bash
python satsim_radio.py --backend matplotlib orbit --sats 24 --planes 4
# Output: orbit_walker_87_24_4.png (static snapshot)
```

### Route Analysis

All backends work with route mode:
```bash
# Static image
python satsim_radio.py --backend matplotlib route --route dragon_path --sats 53 --planes 12

# Interactive exploration
python satsim_radio.py --backend plotly route --route borealis_run --sats 97 --planes 11
```

## Performance Considerations

### Matplotlib
- **Speed:** Fast for static images
- **Memory:** Low memory usage
- **File size:** Small PNG files (1-5 MB)

### Plotly
- **Speed:** Moderate (processes all data in Python)
- **Memory:** Higher memory for complex 3D scenes
- **File size:** Larger HTML files (3-10 MB) with embedded data
- **Best for:** Interactive exploration, 3D visualizations

### Bokeh
- **Speed:** Very fast for 2D plots
- **Memory:** Efficient for large grids
- **File size:** Medium HTML files (2-6 MB)
- **Best for:** Large heatmaps, fast 2D interactivity

## Output Files

### Matplotlib Backend
```
heatmap_vdes_walker_87_12_3.png        # Static image
heatmap_vdes_walker_87_12_3.csv        # Data export (WKT geometry)
```

### Plotly/Bokeh Backends
```
heatmap_vdes_walker_87_12_3.html       # Interactive visualization
heatmap_vdes_walker_87_12_3.csv        # Data export (WKT geometry)
```

## Advanced Features

### Plotly-Specific Features
- **3D Orbit Animation:** Full rotation and zoom
- **Multiple satellites:** Color-coded trajectories
- **Earth sphere:** Semi-transparent for visibility
- **Export to static:** Can save to PNG if kaleido is installed

### Bokeh-Specific Features
- **Hover tooltips:** Show exact coverage percentage
- **Color mapping:** Customizable palettes
- **Fast rendering:** Optimized for large grids

## Troubleshooting

### "Backend not installed" error
Install the missing backend:
```bash
pip install plotly  # or bokeh
```

### Interactive plots not opening
The HTML files are saved to the current directory. Open them manually:
```bash
firefox heatmap_vdes_walker_87_12_3.html
# or
google-chrome orbit_walker_87_24_4.html
```

### Large file sizes
For plotly HTML files, consider:
- Reducing grid resolution (`--res 5` instead of `--res 1`)
- Limiting orbit duration (`--duration 120` instead of `--duration 360`)
- Using matplotlib for final publication images

### Memory issues with large constellations
For large constellations (>100 sats):
- Use matplotlib for batch processing
- Reduce grid resolution
- Limit the number of satellites shown in 3D plots

## Recommended Workflows

### Quick Exploration
```bash
# Use plotly for interactive exploration
python satsim_radio.py --backend plotly orbit --sats 24 --planes 4
```

### Publication Figures
```bash
# Use matplotlib for high-quality static images
python satsim_radio.py --backend matplotlib heatmap --sats 97 --planes 11 --res 1
```

### Batch Analysis
```bash
# Use matplotlib in scripts for automation
for sats in 12 24 48 97; do
    python satsim_radio.py --backend matplotlib heatmap --sats $sats --planes 3 --res 5
done
```

### Interactive Sharing
```bash
# Use plotly/bokeh and share HTML files
python satsim_radio.py --backend plotly heatmap --sats 53 --planes 12 --res 2
# Email or host the .html file
```

## Backend Selection Matrix

| Use Case | Recommended Backend | Why |
|----------|-------------------|-----|
| 3D Orbit Exploration | Plotly | Best interactivity |
| Large Heatmaps | Bokeh | Fast rendering |
| Publication Figures | Matplotlib | High quality, small files |
| Batch Processing | Matplotlib | Scriptable, fast |
| Web Sharing | Plotly/Bokeh | Self-contained HTML |
| Low-res Quick View | Matplotlib | Fastest |
| High-res Analysis | Plotly | Interactive zoom |

## Future Enhancements

Planned features:
- Export plotly animations to video
- Custom color schemes per backend
- Combined multi-backend outputs
- Real-time streaming visualizations
