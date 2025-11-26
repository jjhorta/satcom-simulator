# Satcom - Satellite Constellation Simulator

A comprehensive Python-based simulator for satellite communications constellations. This tool enables the simulation of satellite orbital dynamics, ground station communications, and constellation management with support for various orbital patterns including Walker Delta constellations.

## Features

- **Orbital Mechanics**: Accurate Keplerian orbital propagation with support for all classical orbital elements
- **Constellation Management**: Easy creation and management of multi-satellite constellations
- **Walker Delta Patterns**: Built-in support for Walker Delta constellation patterns (common in LEO constellations)
- **Ground Station Communications**: Model ground stations with configurable visibility constraints
- **Coverage Analysis**: Real-time coverage statistics and analysis
- **Visualization**: 2D and 3D plotting capabilities with ground track visualization
- **Simulation Engine**: Time-stepped simulation with callback support
- **CLI Interface**: Command-line tools for quick simulations and visualizations

## Installation

### From source:

```bash
# Clone the repository
git clone https://github.com/jjhorta/satcom.git
cd satcom

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

### Dependencies:

- Python >= 3.8
- numpy >= 1.20.0
- matplotlib >= 3.3.0

## Quick Start

### Using Python API

```python
from satcom import Constellation, GroundStation, Simulator

# Create a constellation
constellation = Constellation(name="MyConstellation")

# Add satellites using Walker Delta pattern
# 24 satellites, 3 orbital planes, 550km altitude, 53° inclination
constellation.create_walker_delta_constellation(
    total_sats=24,
    planes=3,
    phasing=1,
    altitude=550.0,
    inclination=53.0,
)

# Add ground stations
gs = GroundStation("Seattle", latitude=47.6, longitude=-122.3)
constellation.add_ground_station(gs)

# Run simulation
simulator = Simulator(constellation, time_step=60.0)
simulator.run(duration=3600.0)  # 1 hour

# Get coverage statistics
stats = constellation.get_coverage_statistics()
print(f"Coverage: {stats['coverage_percentage']:.1f}%")
```

### Using CLI

```bash
# Run a simulation
satcom simulate --duration 3600 --output coverage.png

# Visualize constellation in 2D
satcom visualize --view 2d --output constellation.png

# Visualize with communication links
satcom visualize --view 2d --show-links --output links.png

# Visualize in 3D
satcom visualize --view 3d --output constellation_3d.png

# Track a specific satellite
satcom track sat_0_0 --duration 5400 --output ground_track.png
```

## Examples

See the `examples/` directory for more detailed usage examples:

- `basic_simulation.py`: Basic constellation simulation with coverage analysis

Run examples:
```bash
cd examples
python basic_simulation.py
```

## Architecture

The simulator consists of several key components:

- **orbital_mechanics.py**: Core orbital calculations (Keplerian elements, coordinate transformations)
- **satellite.py**: Satellite class with orbital state and propagation
- **ground_station.py**: Ground station class with visibility calculations
- **constellation.py**: Constellation manager for multiple satellites
- **simulator.py**: Simulation engine with time-stepping and callbacks
- **visualization.py**: Plotting and visualization tools
- **cli.py**: Command-line interface

## Orbital Parameters

Satellites are defined using Keplerian orbital elements:

- **Semi-major axis**: Size of the orbit (km)
- **Eccentricity**: Shape of the orbit (0 = circular, 0-1 = elliptical)
- **Inclination**: Tilt of orbital plane (degrees)
- **RAAN** (Right Ascension of Ascending Node): Orientation of orbital plane (degrees)
- **Argument of Perigee**: Orientation of ellipse in orbital plane (degrees)
- **Mean Anomaly**: Position of satellite in orbit (degrees)

## Walker Delta Constellations

Walker Delta is a satellite constellation pattern that provides uniform global coverage. It's parameterized as T/P/F:

- **T**: Total number of satellites
- **P**: Number of equally spaced orbital planes
- **F**: Phasing parameter (relative spacing between planes)

Example: A 24/3/1 constellation has 24 satellites in 3 planes with phasing factor 1.

## Testing

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run with coverage
pytest --cov=satcom tests/
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Acknowledgments

This simulator uses simplified two-body orbital mechanics. For production use cases requiring high accuracy, consider more sophisticated propagation methods (SGP4, numerical integration with perturbations, etc.).