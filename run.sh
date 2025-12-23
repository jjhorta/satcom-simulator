#!/bin/bash
#
# Convenience wrapper to run the simulator
# Automatically activates the virtual environment
#

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/venv"

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Error: Virtual environment not found at $VENV_DIR"
    echo "Please run ./install.sh first"
    exit 1
fi

# Activate virtual environment and run the simulator
source "$VENV_DIR/bin/activate"
python "$SCRIPT_DIR/satsim_radio.py" "$@"

#
#Starlink's Shell 1 configuration is:
#
#Altitude: 550 km
#
#Inclination: 53°
#
#Total Satellites: 1,584
#
#Planes: 72 (22 satellites per plane)
