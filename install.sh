#!/bin/bash
#
# Installation script for Satellite Constellation Simulator
# Installs all required Python packages and system dependencies
# Compatible with: Debian, Raspberry Pi OS, Red Hat/CentOS/Fedora
#

set -e  # Exit on error

echo "=========================================="
echo "Satellite Constellation Simulator Setup"
echo "=========================================="
echo

# Detect script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/venv"

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "Warning: This script is optimized for Linux systems"
fi

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed"
    echo "Please install Python 3.8 or later"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "Found Python $PYTHON_VERSION"

# Install system dependencies for matplotlib (fonts, etc.)
echo
echo "Checking system dependencies..."
if command -v apt-get &> /dev/null; then
    echo "Detected apt package manager (Debian/Ubuntu/Raspberry Pi)"
    echo "Installing system packages (may require sudo)..."
    sudo apt-get update
    sudo apt-get install -y \
        fonts-symbola \
        fonts-dejavu \
        python3-tk \
        python3-venv \
        python3-dev \
        libfreetype6-dev \
        libpng-dev \
        build-essential
elif command -v dnf &> /dev/null; then
    echo "Detected dnf package manager (Fedora/RHEL 8+)"
    sudo dnf install -y \
        gdouros-symbola-fonts \
        dejavu-sans-fonts \
        python3-tkinter \
        python3-devel \
        freetype-devel \
        libpng-devel \
        gcc \
        gcc-c++
elif command -v yum &> /dev/null; then
    echo "Detected yum package manager (RHEL/CentOS 7)"
    sudo yum install -y \
        gdouros-symbola-fonts \
        dejavu-sans-fonts \
        python3-tkinter \
        python3-devel \
        freetype-devel \
        libpng-devel \
        gcc \
        gcc-c++
else
    echo "Warning: Could not detect package manager"
    echo "You may need to manually install: Symbola fonts, DejaVu fonts, python3-tk, python3-venv"
fi

# Create virtual environment
echo
echo "=========================================="
echo "Setting up Python virtual environment..."
echo "=========================================="
echo

if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists at $VENV_DIR"
    read -p "Do you want to recreate it? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
        echo "Creating new virtual environment..."
        python3 -m venv "$VENV_DIR"
    fi
else
    echo "Creating virtual environment at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip in virtual environment
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python packages
echo
echo "=========================================="
echo "Installing Python packages..."
echo "=========================================="
echo

# Core dependencies
pip install --upgrade \
    numpy \
    matplotlib \
    skyfield \
    Pillow

echo
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo
echo "Installed packages:"
pip list | grep -E "(numpy|matplotlib|skyfield|Pillow)"
echo
echo "=========================================="
echo "How to use:"
echo "=========================================="
echo
echo "1. Activate the virtual environment:"
echo "   source $VENV_DIR/bin/activate"
echo
echo "2. Run the simulator:"
echo "   python satsim_radio.py sky --help"
echo "   python satsim_radio.py sky --location lisbon --comms ais --weather clear"
echo
echo "3. Deactivate when done:"
echo "   deactivate"
echo
echo "Or use the convenience wrapper script:"
echo "   ./run.sh sky --location lisbon --comms ais --weather clear"
echo

# Check Docker accessibility and give a clear warning if socket access fails
if command -v docker &> /dev/null; then
    echo
    echo "Checking Docker access..."
    if ! docker info > /dev/null 2>&1; then
        echo "WARNING: Unable to access the Docker daemon (permission denied)."
        echo "If you intended to run Docker commands, try prefixing with 'sudo' or add your user to the 'docker' group:" 
        echo "  sudo usermod -aG docker \$(whoami) && newgrp docker"
        echo "Alternatively, run the failing command with 'sudo' (you may be prompted for a password)."
        echo
    else
        echo "Docker daemon is accessible."
    fi
fi
