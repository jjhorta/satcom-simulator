# 🛰️ Satellite Constellation & Communications Simulator

A comprehensive physics-based simulator for analyzing satellite constellation coverage and link budget performance for maritime, terrestrial, and Arctic communications.

---

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
- [Strategic Importance](#strategic-importance)
- [Coverage Locations](#coverage-locations)
- [Parameters Reference](#parameters-reference)

---

## 🚀 Installation

### Prerequisites
- Python 3.8+
- Linux/macOS/WSL environment
- ~500MB disk space for dependencies

### Step 1: Clone/Download the Project
```bash
cd /home/lusospace/constellation_simulator
```

### Step 2: Run Installation Script
The installation script will automatically:
- Create a Python virtual environment
- Install all required dependencies (matplotlib, skyfield, numpy, etc.)

```bash
chmod +x install.sh
./install.sh
```

### Step 3: Verify Installation
```bash
./run.sh --help
```

If successful, you'll see the simulator's help menu.

---

## 🎯 Quick Start

### Activate Virtual Environment (Manual)
If you need to activate the venv manually:
```bash
source venv/bin/activate
```

### Basic Simulation
Generate a sky view from Lisbon with 12 satellites using AIS payload:
```bash
./run.sh sky --location lisbon --save
```

### Advanced Example: 5G Coverage from Cape Town
```bash
./run.sh sky --location cape_town --comms 5g --weather rain --bidi --save --sats 24 --planes 3
```

---

## 💡 Usage Examples

### Analysis Modes Overview

**The simulator provides four complementary analysis modes:**

| Mode | Purpose | Speed | Accuracy | Best For |
|------|---------|-------|----------|----------|
| **heatmap** | Global geometric coverage | Fast | Geometric only | Constellation design, coverage patterns |
| **sky** | Point-specific link budget | Medium | Full RF analysis | Service validation, specific locations |
| **route** | Path-specific coverage | Medium | Full RF analysis | Maritime/Arctic route validation |
| **orbit** | 3D visualization + dashboard | Slow | Visual + metrics | Presentations, design review |

⚠️ **Important**: `heatmap` and `sky`/`route` modes use different coverage criteria:
- **heatmap**: Shows if satellites are geometrically visible above minimum elevation (ignores link budget)
- **sky/route**: Shows if RF link actually works (includes SNR, weather, power budget)
- **Result**: Heatmap will show ≥ coverage % compared to sky/route mode for the same location

---

### 1. Global Coverage Heatmap
```bash
# Fast global analysis - geometric visibility only
./run.sh heatmap --sats 12 --planes 3 --inc 53 --alt 550 --res 5.0 --min-elev 10

# High-resolution heatmap with stricter elevation (slower)
./run.sh heatmap --sats 66 --planes 6 --inc 87 --alt 1200 --res 1.0 --min-elev 25

# Sun-synchronous orbit at specific altitude
./run.sh heatmap --sats 24 --planes 4 --alt 600 --sso --res 5.0
```
**Output**: `heatmap_<comms>_walker_<inc>_<sats>_<planes>.csv` + `.png`  
**Use case**: Quick constellation design comparison, coverage gap identification

---

### 2. Single Location Link Budget Analysis
```bash
# AIS coverage from Gibraltar (clear weather, downlink only)
./run.sh sky --location gibraltar --comms ais --weather clear --save

# Starlink Ku-band from North Pole with bidirectional link
./run.sh sky --location nuuk --comms starlink_ku --weather storm --bidi --save --inc 53 --alt 550
```
**Output**: Animated GIF with real-time link budget dashboard  
**Use case**: Service validation, worst-case weather scenarios

---

### 3. Batch Coverage Analysis (Multiple Locations)
```bash
# Test all port locations (default)
./run.sh sky --coverage --comms vdes --weather clear --bidi --save --sats 24 --planes 3

# Test only sea route waypoints
./run.sh sky --coverage sea --comms vdes --weather clear --save

# Test only Arctic routes
./run.sh sky --coverage arctic --comms mss --weather clear --bidi --save

# Test everything (ports + sea routes + Arctic)
./run.sh sky --coverage all --comms 5g --weather rain --bidi --save --sats 66 --planes 6
```
**Output**: `coverage_<type>_<comms>_walker_<inc>_<sats>_<planes>.csv`  
**Use case**: Service area validation, SLA verification

---

### 4. Route-Specific Coverage Analysis
```bash
# Analyze North Atlantic shipping corridor (Titan Corridor)
./run.sh route --route titan_corridor --comms vdes --sats 24 --planes 4 --inc 53 --alt 550 --bidi --min-elev 10

# Arctic Northern Sea Route analysis with strict elevation
./run.sh route --route borealis_run --comms mss --sats 24 --planes 4 --inc 97 --alt 600 --bidi --sso --min-elev 35

# Pacific Dragon Path with extended duration
./run.sh route --route dragon_path --comms ais --sats 12 --planes 3 --inc 53 --alt 550 --bidi --duration 7200

# Test all available routes (sea routes):
#   - titan_corridor (North Atlantic)
#   - dragon_path (Pacific)
#   - silk_vein (Indian Ocean)
#   - roaring_passage (Southern Ocean)
# Arctic routes:
#   - borealis_run (Northern Sea Route)
#   - franklin_maze (Northwest Passage)
#   - midnight_sun_arc (Transpolar)
```
**Output**: `route_<name>_<comms>_walker_<inc>_<sats>_<planes>.csv` + summary statistics  
**Use case**: Maritime service validation, shipping route SLA verification, Arctic operations planning

---

### 5. 3D Orbital Visualization + Engineering Dashboard
```bash
# AIS coverage from Gibraltar (clear weather, downlink only)
./run.sh sky --location gibraltar --comms ais --weather clear --save

# Starlink Ku-band from North Pole with bidirectional link
./run.sh sky --location nuuk --comms starlink_ku --weather storm --bidi --save --inc 53 --alt 550
```

### 2. Global Coverage Analysis
```bash
# Test all port locations (default)
./run.sh sky --coverage --comms vdes --weather clear --bidi --save --sats 24 --planes 3

# Test only sea route waypoints
./run.sh sky --coverage sea --comms vdes --weather clear --save

# Test only Arctic routes
./run.sh sky --coverage arctic --comms mss --weather clear --bidi --save

# Test everything (ports + sea routes + Arctic)
./run.sh sky --coverage all --comms 5g --weather rain --bidi --save --sats 66 --planes 6
```

### 5. 3D Orbital Visualization + Engineering Dashboard
```bash
# Complete constellation analysis with rotating Earth, coverage beams, and metrics
./run.sh orbit --sats 12 --planes 3 --inc 53 --alt 550 --beams --map --trails --min-elev 30 --save

# Fast preview without continents or beams
./run.sh orbit --sats 66 --planes 6 --inc 87 --alt 1200 --duration 120
```
**Output**: Animated GIF + comprehensive engineering dashboard (shown on startup)  
**Dashboard includes**:
- Orbital mechanics (period, velocity, orbits/day)
- Coverage metrics (radius, area, revisit time)
- Link budget basics (frequency, path loss)
- Satellite lifetime & replacement rate
- Launch planning (batch size, launches/year)

**Use case**: Executive presentations, design review meetings

---

### 6. Constellation Design Comparison
```bash
# Starlink-like (550km, 53° inclination)
./run.sh heatmap --sats 66 --planes 6 --inc 53 --alt 550 --res 5.0
./run.sh sky --coverage all --comms starlink_ku --sats 66 --planes 6 --inc 53 --alt 550 --save --bidi

# OneWeb-like (1200km, 87.9° polar)
./run.sh heatmap --sats 48 --planes 6 --inc 87.9 --alt 1200 --res 5.0
./run.sh sky --coverage all --comms 5g --sats 48 --planes 6 --inc 87.9 --alt 1200 --save --bidi

# Custom LEO (800km, 60° inclination)
./run.sh heatmap --sats 36 --planes 4 --inc 60 --alt 800 --res 5.0
./run.sh sky --coverage arctic --comms vdes --sats 36 --planes 4 --inc 60 --alt 800 --save
```

---

### 7. Visual Options
```bash
# Sky view with satellite trails (observer perspective)
./run.sh sky --location strait_of_hormuz --trails --save --frames 400

# 3D orbital view with coverage beams and rotating continents
./run.sh orbit --sats 24 --planes 3 --inc 53 --alt 560 --beams --map --trails --save --duration 180

# Ground track view (Mercator projection)
./run.sh track --sats 24 --planes 3 --inc 87 --alt 1200 --save --frames 300
```

---

## 🌍 Strategic Importance

### Why Satellite Coverage Simulation Matters

**1. Maritime Safety & Efficiency**
- **Search and Rescue (SAR)**: Real-time position tracking via AIS/VDES for distress response
- **Weather Routing**: Reduced fuel costs and safer passages
- **Piracy Prevention**: Enhanced monitoring of high-risk zones (Gulf of Aden, Strait of Malacca)

**2. Global Trade Continuity**
- **90% of global trade** moves by sea through critical chokepoints
- Suez/Panama Canal disruptions cost **$400M+ per day**
- Arctic routes offer **40% shorter distances** (Europe-Asia) but require robust communication

**3. Geopolitical Security**
- **Chokepoints as Control Points**: Hormuz, Malacca, Bosphorus control energy/trade flows
- **Arctic Competition**: Russia's Northern Sea Route vs. Canada's Northwest Passage
- **Backup Routes**: Cape of Good Hope as Suez alternative requires continuous coverage

**4. Emerging Arctic Sovereignty**
- Melting ice opens **new trade routes** by 2040+
- Need for **24/7 connectivity** in extreme latitudes (70°N+)
- Strategic military/commercial competition (Russia, USA, Canada, Nordic nations)

**5. Direct-to-Cell (D2C) Revolution**
- **5G/4G from space** enables smartphone connectivity anywhere
- Critical for remote operations, disaster zones, and underserved markets
- Requires **higher power, larger antennas** than traditional satcom

### Link Budget Realism
This simulator calculates:
- **Free Space Path Loss (FSPL)** at various altitudes/frequencies
- **Rain attenuation** using ITU-R models (tropical storms = 100mm/hr)
- **Uplink vs Downlink asymmetry** (phones = 0.2W, satellites = 50-100W)
- **Bidirectional feasibility** (both links must close for duplex comms)

---

## 📍 Coverage Locations

### Category 1: PRIMARY CHOKEPOINTS (Critical Infrastructure)
**Global trade bottlenecks** - Disruption causes cascading economic impacts.

| Location | Coordinates | Strategic Value |
|----------|-------------|-----------------|
| **Panama Canal** | 8.98°N, 79.52°W | Atlantic ↔ Pacific shortcut (14,000+ ships/year) |
| **Suez Canal** | 30.59°N, 32.40°E | Europe ↔ Asia shortcut (12% of global trade) |
| **Strait of Malacca** | 1.35°N, 103.82°E | 25% of world's traded goods pass through |
| **Strait of Hormuz** | 26.57°N, 56.25°E | 21% of global oil supply (Achilles heel) |
| **Bab el-Mandeb** | 12.59°N, 43.34°E | Red Sea gateway (Houthi attacks 2023-2024) |
| **Gibraltar** | 36.14°N, 5.35°W | Mediterranean-Atlantic access |
| **Bosphorus** | 41.01°N, 28.98°E | Only exit for Black Sea (Russia/Ukraine) |
| **Cape of Good Hope** | 34.35°S, 18.47°E | Suez alternative for supertankers |

### Category 2: MEGA-PORTS (>20M TEU/year)
**Global logistics engines** - Hub-and-spoke model relies on these.

| Port | Coordinates | Rank |
|------|-------------|------|
| **Shanghai** | 31.23°N, 121.47°E | #1 Global (47M TEU) |
| **Singapore** | 1.29°N, 103.85°E | #2 Global (Transshipment King) |
| **Ningbo-Zhoushan** | 29.87°N, 121.54°E | #3 Global (China's megahub) |
| **Shenzhen** | 22.54°N, 114.06°E | #4 Global (Tech exports) |
| **Los Angeles** | 33.73°N, 118.26°W | #1 North America |
| **Rotterdam** | 51.92°N, 4.48°E | #1 Europe |

### Category 3: ARCTIC FRONTIERS (Emerging Trade Routes)
**The "New North"** - Climate change unlocks shorter routes by 2040.

#### Northern Sea Route (Russia) - Most Active
| Port | Coordinates | Role |
|------|-------------|------|
| **Murmansk** | 68.96°N, 33.08°E | Nuclear icebreaker HQ |
| **Sabetta** | 71.27°N, 72.07°E | LNG mega-port (Yamal) |
| **Pevek** | 69.70°N, 170.31°E | Deep-water expansion |

#### Northwest Passage (Canada) - Slower Development
| Port | Coordinates | Role |
|------|-------------|------|
| **Iqaluit** | 63.75°N, 68.52°W | New deep-sea port (2022) |
| **Churchill** | 58.77°N, 94.17°W | Arctic grain export |
| **Nanisivik** | 73.04°N, 84.55°W | Naval refueling (2025) |

#### Transpolar Route (Future) - Direct Over North Pole
| Waypoint | Coordinates | Notes |
|----------|-------------|-------|
| **North Pole** | 90.0°N, 0.0°E | Geographic pole crossing |
| **Fram Strait** | 80.0°N, 5.0°E | Greenland-Svalbard gap |

### Category 4: OPEN OCEAN ROUTES (Mid-Sea Waypoints)
**High-seas navigation corridors** - No terrestrial infrastructure.

#### Titan Corridor (North Atlantic)
- **10 waypoints** from UK to New York
- Busiest ocean highway (Titanic's grave nearby)

#### Dragon Path (Trans-Pacific)
- **10 waypoints** from Tokyo to Los Angeles
- Great Circle route (curves north near Aleutians)

#### Silk Vein (Indian Ocean)
- **10 waypoints** from Suez to Malacca
- Ancient spice route modernized

#### Borealis Run (Northern Sea Route)
- **12 waypoints** from Barents Sea to Bering Strait
- Requires icebreaker escort most of year

#### Franklin's Maze (Northwest Passage)
- **12 waypoints** through Canadian Arctic Archipelago
- Named after doomed 1845 expedition

#### Midnight Sun Arc (Transpolar - Theoretical)
- **12 waypoints** directly over North Pole
- Only viable with heavy icebreakers (2040+)

---

## 🔧 Parameters Reference

### Constellation Parameters
| Parameter | Flag | Default | Description |
|-----------|------|---------|-------------|
| Satellites | `--sats` | 12 | Total satellites in constellation |
| Planes | `--planes` | 3 | Number of orbital planes |
| Inclination | `--inc` | 53.0 | Orbital inclination (degrees) |
| Altitude | `--alt` | 560.0 | Orbital altitude (km) |
| Phasing | `--phasing` | 1 | Walker phasing parameter |

### Simulation Parameters
| Parameter | Flag | Default | Description |
|-----------|------|---------|-------------|
| View Mode | `view` | - | `heatmap`, `sky`, `orbit`, or `track` |
| Location | `--location` | lisbon | Observer location (sky mode only) |
| Frames | `--frames` | 200 | Number of animation frames |
| Speed | `--speed` | 30 | Simulation speed (seconds/frame) |
| Trails | `--trails` | off | Show satellite trails |
| Save | `--save` | off | Save to GIF/PNG file |
| Min Elevation | `--min-elev` | 10.0 | Minimum elevation angle (degrees) |
| Duration | `--duration` | 360 | Simulation duration in minutes (orbit mode) |
| Resolution | `--res` | 5.0 | Grid resolution in degrees (heatmap mode) |
| Beams | `--beams` | off | Show coverage circles (orbit mode) |
| Map | `--map` | off | Show rotating continents (orbit mode) |

### Communications Parameters
| Parameter | Flag | Default | Options |
|-----------|------|---------|---------|
| Payload | `--comms` | ais | `ais`, `vdes`, `gsm`, `lte`, `5g`, `mss`, `starlink_ku` |
| Weather | `--weather` | clear | `clear`, `smoke`, `drizzle`, `rain`, `storm`, `tropical` |
| Bidirectional | `--bidi` | off | Enable uplink + downlink calculation |

### Coverage Analysis
| Parameter | Flag | Options | Description |
|-----------|------|---------|-------------|
| Coverage | `--coverage` | `""` (default) | LOCATIONS only |
|           |              | `sea` | SEA_ROUTES waypoints |
|           |              | `arctic` | ARCTIC_ROUTES waypoints |
|           |              | `both` | LOCATIONS + SEA_ROUTES |
|           |              | `all` | LOCATIONS + SEA_ROUTES + ARCTIC_ROUTES |

### Payload Specifications

| Payload | Frequency | Bandwidth | Use Case |
|---------|-----------|-----------|----------|
| **AIS** | 162 MHz | 25 kHz | Ship tracking (mandatory SOLAS) |
| **VDES** | 157/161 MHz | 50 kHz | Maritime data (next-gen AIS) |
| **GSM** | 890/935 MHz | 200 kHz | 2G direct-to-cell (basic SMS) |
| **LTE** | 1920/2110 MHz | 5 MHz | 4G direct-to-cell (voice/data) |
| **5G** | 1980/2170 MHz | 20 MHz | 5G direct-to-cell (high-speed) |
| **MSS** | 1626/1620 MHz | 100 kHz | Satellite phones (Iridium/Inmarsat) |
| **Starlink Ku** | 14/12 GHz | 250 MHz | Broadband (Dishy terminals) |

---

## 📊 Output Files

### Generated Files

#### Single Simulations
```
<location>_<view>_<comms>_<mode>_<weather>_walker_<inc>_<sats>_<planes>_output.gif
```
Example: `strait_of_hormuz_sky_vdes_bidi_rain_walker_53.0_24_3_output.gif`

#### Coverage Analysis
```
coverage_<type>_<comms>_<mode>_walker_<inc>_<sats>_<planes>.csv
```
Example: `coverage_all_5g_bidi_walker_53.0_66_6.csv`

### CSV Format
```csv
location,latitude,longitude,connectivity_pct
panama_canal,8.9824,-79.5199,87.5
suez_canal,30.5852,32.3999,92.3
...
```

---

## 🐛 Troubleshooting

### Virtual Environment Issues
```bash
# If venv is corrupted, recreate it
rm -rf venv
./install.sh
```

### Font Warnings (Emoji glyphs)
```bash
# Install emoji font support (Ubuntu/Debian)
sudo apt install fonts-noto-color-emoji

# Clear matplotlib cache
rm -rf ~/.cache/matplotlib
```

### Slow Performance
- Reduce `--frames` (default 200 → 100)
- Disable `--trails` flag
- Use `--coverage` without `--save` for testing
- Avoid `--bidi` unless needed (2x faster)

---

## 📚 References

- **ITU-R Recommendations**: Rain attenuation models
- **Walker Constellation Theory**: Optimal satellite phasing
- **Friis Transmission Equation**: Link budget calculations
- **Skyfield Library**: High-precision orbital propagation

---

## 📝 License

MIT License - Free for academic and commercial use.

---

## 🤝 Contributing

Contributions welcome! Areas of interest:
- Additional payload types (Ka-band, optical links)
- Atmospheric models (ionospheric scintillation)
- Handover analysis (satellite switching)
- Cost modeling (launch + operations)

---

**Last Updated**: November 2025  
**Version**: 2.0  
**Author**: John Horta