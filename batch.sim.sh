#!/bin/bash

# ==============================================================================
# SATELLITE CONSTELLATION BATCH SIMULATOR
# ==============================================================================
# Enhanced batch simulator with modular view generation
# Usage: ./batch.sim.sh [command] [options]
# ==============================================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/venv"
PYTHON_SCRIPT="$SCRIPT_DIR/satsim_radio.py"

# Activate virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Error: Virtual environment not found at $VENV_DIR"
    echo "Please run ./install.sh first"
    exit 1
fi
source "$VENV_DIR/bin/activate"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

show_help() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}SATELLITE CONSTELLATION BATCH SIMULATOR${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}USAGE:${NC}"
    echo "    ./batch.sim.sh <command> <name> [options]"
    echo ""
    echo -e "${YELLOW}COMMANDS:${NC}"
    echo -e "    ${GREEN}orbit${NC}      - Generate 3D orbital view animation"
    echo -e "    ${GREEN}track${NC}      - Generate ground track visualization"
    echo -e "    ${GREEN}coverage${NC}   - Run coverage analysis (sky views + CSV)"
    echo -e "    ${GREEN}heatmap${NC}    - Generate global coverage heatmap (geometric)"
    echo -e "    ${GREEN}heatmap-rf${NC} - Generate RF link budget heatmap"
    echo -e "    ${GREEN}all${NC}        - Generate all views above"
    echo -e "    ${GREEN}help${NC}       - Show this help message"
    echo ""
    echo -e "${YELLOW}REQUIRED ARGUMENTS:${NC}"
    echo "    <name>         - Simulation name (used for output directory)"
    echo ""
    echo -e "${YELLOW}CONSTELLATION OPTIONS:${NC}"
    echo "    --sats <n>     - Number of satellites (default: 66)"
    echo "    --planes <n>   - Number of orbital planes (default: 6)"
    echo "    --inc <deg>    - Inclination in degrees (default: 87.4)"
    echo "    --alt <km>     - Altitude in kilometers (default: 600)"
    echo "    --phasing <n>  - Walker phasing parameter (default: 1)"
    echo ""
    echo -e "${YELLOW}PAYLOAD & WEATHER:${NC}"
    echo "    --comms <type> - Payload type (default: vdes)"
    echo "                     Options: ais, vdes, gsm, lte, 5g, mss, starlink_ku"
    echo "    --weather <w>  - Weather scenario (default: clear)"
    echo "                     Options: clear, smoke, drizzle, rain, storm, tropical"
    echo ""
    echo -e "${YELLOW}SIMULATION OPTIONS:${NC}"
    echo "    --sso          - Use Sun-Synchronous Orbit (auto-calculate inclination)"
    echo "    --bidi         - Enable bidirectional link calculations"
    echo "    --trails       - Show satellite trails in animations"
    echo "    --frames <n>   - Animation frames for orbit/track (default: 100)"
    echo "    --speed <s>    - Simulation speed in seconds/frame (default: 60)"
    echo ""
    echo -e "${YELLOW}COVERAGE OPTIONS:${NC}"
    echo "    --coverage-type <type>  - Coverage location set (default: both)"
    echo "                              Options: '', sea, arctic, both, all"
    echo ""
    echo -e "${YELLOW}HEATMAP OPTIONS:${NC}"
    echo "    --res <deg>    - Heatmap grid resolution in degrees (default: 5.0)"
    echo ""
    echo -e "${YELLOW}EXAMPLES:${NC}"
    echo "    # Generate all views for a 66-sat SSO constellation"
    echo "    ./batch.sim.sh all MyConstellation --sats 66 --planes 6 --alt 600 --sso"
    echo ""
    echo "    # Generate only heatmap for Starlink-like constellation"
    echo "    ./batch.sim.sh heatmap Starlink_Shell1 --sats 1584 --planes 72 --inc 53 --alt 550"
    echo ""
    echo "    # Coverage analysis with storm weather"
    echo "    ./batch.sim.sh coverage Maritime_AIS --sats 60 --planes 6 --sso --comms ais --weather storm"
    echo ""
    echo "    # Orbit view with trails"
    echo "    ./batch.sim.sh orbit Polar_Constellation --sats 24 --planes 4 --inc 87 --alt 800 --trails"
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
}

# Function to create output directory and move files
organize_outputs() {
    local NAME=$1
    local OUTPUT_DIR="output_sims/$NAME"
    
    echo -e "${BLUE}📁 Organizing outputs to: $OUTPUT_DIR${NC}"
    mkdir -p "$OUTPUT_DIR"
    
    # Move all generated files (using proper globbing)
    shopt -s nullglob  # Don't expand if no match
    local files_moved=0
    
    for pattern in "*.gif" "*.png" "*.csv" "heatmap_*.csv" "coverage_*.csv"; do
        for file in $pattern; do
            if [ -f "$file" ]; then
                mv "$file" "$OUTPUT_DIR/" 2>/dev/null && ((files_moved++))
            fi
        done
    done
    
    shopt -u nullglob
    
    if [ $files_moved -gt 0 ]; then
        echo -e "${GREEN}✅ Files organized in: $OUTPUT_DIR ($files_moved files moved)${NC}"
    else
        echo -e "${YELLOW}⚠️  No output files found to organize${NC}"
    fi
}

# Run orbit view
run_orbit() {
    local NAME=$1
    shift
    local ARGS="$@"
    
    # Filter to orbit-specific args: --sats, --planes, --altitude, --phasing, --inclination, --inc, --sso, --trails, --save
    local ORBIT_ARGS=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --inc)
                ORBIT_ARGS="$ORBIT_ARGS --inclination $2"
                shift 2
                ;;
            --sats|--planes|--altitude|--phasing|--inclination|--sso|--trails|--save)
                ORBIT_ARGS="$ORBIT_ARGS $1"
                [[ $1 != --sso && $1 != --trails && $1 != --save ]] && { ORBIT_ARGS="$ORBIT_ARGS $2"; shift; }
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    echo -e "${YELLOW}🛰️  Generating 3D Orbit View for: $NAME${NC}"
    python "$PYTHON_SCRIPT" orbit $ORBIT_ARGS --save
    organize_outputs "$NAME"
}

# Run track view
run_track() {
    local NAME=$1
    shift
    local ARGS="$@"
    
    # Filter to track-specific args: --sats, --planes, --altitude, --phasing, --inclination, --inc, --sso, --save
    local TRACK_ARGS=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --inc)
                TRACK_ARGS="$TRACK_ARGS --inclination $2"
                shift 2
                ;;
            --sats|--planes|--altitude|--phasing|--inclination|--sso|--save)
                TRACK_ARGS="$TRACK_ARGS $1"
                [[ $1 != --sso && $1 != --save ]] && { TRACK_ARGS="$TRACK_ARGS $2"; shift; }
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    echo -e "${YELLOW}🗺️  Generating Ground Track for: $NAME${NC}"
    python "$PYTHON_SCRIPT" track $TRACK_ARGS --save
    organize_outputs "$NAME"
}

# Run coverage analysis
run_coverage() {
    local NAME=$1
    shift
    local ARGS="$@"
    
    # Filter to sky-specific args: all constellation params + comms, weather, duration, speed, trails, bidi, coverage, location, save
    local SKY_ARGS=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --inc)
                SKY_ARGS="$SKY_ARGS --inclination $2"
                shift 2
                ;;
            --sats|--planes|--altitude|--phasing|--inclination|--sso|--bidi|--comms|--weather|--duration|--speed|--trails|--coverage|--location|--save)
                SKY_ARGS="$SKY_ARGS $1"
                [[ $1 != --sso && $1 != --bidi && $1 != --trails && $1 != --save ]] && { SKY_ARGS="$SKY_ARGS $2"; shift; }
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    # Add defaults for sky-specific params if not present
    if [[ ! "$SKY_ARGS" =~ "--comms" ]]; then SKY_ARGS="$SKY_ARGS --comms vdes"; fi
    if [[ ! "$SKY_ARGS" =~ "--weather" ]]; then SKY_ARGS="$SKY_ARGS --weather clear"; fi
    if [[ ! "$SKY_ARGS" =~ "--duration" ]]; then SKY_ARGS="$SKY_ARGS --duration 3600"; fi
    if [[ ! "$SKY_ARGS" =~ "--speed" ]]; then SKY_ARGS="$SKY_ARGS --speed 60"; fi
    
    echo -e "${YELLOW}📊 Running Coverage Analysis for: $NAME${NC}"
    python "$PYTHON_SCRIPT" sky $SKY_ARGS --save
    organize_outputs "$NAME"
}

# Run heatmap generation
run_heatmap() {
    local NAME=$1
    shift
    local ARGS="$@"
    
    # Filter to heatmap-specific args: --sats, --planes, --altitude, --phasing, --inclination, --inc, --sso, --bidi, --comms, --weather, --res
    local HEATMAP_ARGS=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --inc)
                HEATMAP_ARGS="$HEATMAP_ARGS --inclination $2"
                shift 2
                ;;
            --sats|--planes|--altitude|--phasing|--inclination|--sso|--bidi|--comms|--weather|--res)
                HEATMAP_ARGS="$HEATMAP_ARGS $1"
                [[ $1 != --sso && $1 != --bidi ]] && { HEATMAP_ARGS="$HEATMAP_ARGS $2"; shift; }
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    # Add defaults for heatmap-specific params if not present
    if [[ ! "$HEATMAP_ARGS" =~ "--comms" ]]; then HEATMAP_ARGS="$HEATMAP_ARGS --comms vdes"; fi
    if [[ ! "$HEATMAP_ARGS" =~ "--weather" ]]; then HEATMAP_ARGS="$HEATMAP_ARGS --weather clear"; fi
    if [[ ! "$HEATMAP_ARGS" =~ "--res" ]]; then HEATMAP_ARGS="$HEATMAP_ARGS --res 5.0"; fi
    
    echo -e "${YELLOW}🌡️  Generating Coverage Heatmap for: $NAME${NC}"
    python "$PYTHON_SCRIPT" heatmap $HEATMAP_ARGS
    organize_outputs "$NAME"
}

# Run RF link budget heatmap
run_heatmap_rf() {
    local NAME=$1
    shift

    local HEATMAP_RF_ARGS=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --inc)
                HEATMAP_RF_ARGS="$HEATMAP_RF_ARGS --inclination $2"
                shift 2
                ;;
            --sats|--planes|--altitude|--phasing|--inclination|--sso|--bidi|--comms|--weather|--res|--min-elev)
                HEATMAP_RF_ARGS="$HEATMAP_RF_ARGS $1"
                [[ $1 != --sso && $1 != --bidi ]] && { HEATMAP_RF_ARGS="$HEATMAP_RF_ARGS $2"; shift; }
                shift
                ;;
            *)
                shift
                ;;
        esac
    done

    if [[ ! "$HEATMAP_RF_ARGS" =~ "--comms" ]]; then HEATMAP_RF_ARGS="$HEATMAP_RF_ARGS --comms vdes"; fi
    if [[ ! "$HEATMAP_RF_ARGS" =~ "--weather" ]]; then HEATMAP_RF_ARGS="$HEATMAP_RF_ARGS --weather clear"; fi
    if [[ ! "$HEATMAP_RF_ARGS" =~ "--res" ]]; then HEATMAP_RF_ARGS="$HEATMAP_RF_ARGS --res 5.0"; fi

    echo -e "${YELLOW}📡 Generating RF Link Budget Heatmap for: $NAME${NC}"
    python "$PYTHON_SCRIPT" heatmap-rf $HEATMAP_RF_ARGS
    organize_outputs "$NAME"
}

# Run all views
run_all() {
    local NAME=$1
    local CATEGORY=$2
    shift 2
    local ARGS="$@"
    
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}🚀 FULL SIMULATION SUITE: $NAME${NC}"
    if [ -n "$CATEGORY" ]; then
        echo -e "${BLUE}Category: $CATEGORY${NC}"
    fi
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    
    run_orbit "$NAME" $ARGS --map --trails
    run_track "$NAME" $ARGS --map
    run_heatmap "$NAME" $ARGS
    #run_coverage "$NAME" $ARGS
    
    # If category is provided, organize into category-based structure
    if [ -n "$CATEGORY" ]; then
        local OUTPUT_DIR="output_sims/$CATEGORY/$NAME"
        echo -e "${BLUE}📁 Organizing into category structure: $OUTPUT_DIR${NC}"
        mkdir -p "$OUTPUT_DIR"
        
        # Move from flat output_sims/$NAME to categorized structure
        if [ -d "output_sims/$NAME" ]; then
            mv "output_sims/$NAME"/* "$OUTPUT_DIR/" 2>/dev/null
            rmdir "output_sims/$NAME" 2>/dev/null
            echo -e "${GREEN}✅ Files organized in: $OUTPUT_DIR${NC}"
        fi
    fi
    
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ SIMULATION COMPLETE: $NAME${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
}

# ==============================================================================
# MAIN EXECUTION - PARSE COMMAND LINE
# ==============================================================================

# Parse command
COMMAND=$1
NAME=$2

if [ -z "$COMMAND" ] || [ "$COMMAND" == "help" ] || [ "$COMMAND" == "-h" ] || [ "$COMMAND" == "--help" ]; then
    show_help
    exit 0
fi

# ==============================================================================
# PREDEFINED SCENARIO CONFIGURATIONS
# ==============================================================================

# Define scenarios as associative arrays (scenario name -> parameters)
declare -A SCENARIOS=(
    ["ais_legacy_spire1"]="--sats 60 --planes 6 --sso --comms ais --phasing 1"
    ["ais_legacy_spire2"]="--sats 33 --inc 51.6 --altitude 400 --planes 6 --sso --comms ais --phasing 1"
    ["ais_legacy_spire3"]="--sats 4 --inc 82 --altitude 400 --planes 4 --sso --comms ais --phasing 1"
    ["iridium"]="--sats 66 --planes 11 --inc 86.4 --altitude 780 --comms mss --phasing 1 --bidi"
    ["vdes_3planes"]="--sats 12 --planes 3 --inc 53.0 --altitude 600 --comms vdes --phasing 1"
    ["vdes_4planes"]="--sats 12 --planes 4 --inc 53.0 --altitude 600 --comms vdes --phasing 1"
    ["vdes_phase2"]="--sats 24 --planes 8 --inc 53.0 --altitude 600 --comms vdes --phasing 1"
    ["weather_test_clear"]="--sats 66 --planes 6 --sso --comms vdes --weather clear"
    ["weather_test_tropical"]="--sats 66 --planes 6 --sso --comms vdes --weather tropical"
    ["storm_test"]="--sats 66 --planes 6 --sso --comms vdes --weather storm --bidi"
    ["highres"]="--sats 66 --planes 6 --sso --comms vdes --res 2.0"
)

declare -A SCENARIO_NAMES=(
    ["ais_legacy_spire1"]="Competitor_AIS_Legacy"
    ["ais_legacy_spire2"]="Competitor_AIS_Legacy"
    ["ais_legacy_spire3"]="Competitor_AIS_Legacy"
    ["iridium"]="Competitor_MSS_Iridium"
    ["vdes_3planes"]="MyConstellation_OptionA"
    ["vdes_4planes"]="MyConstellation_OptionB"
    ["vdes_phase2"]="MyConstellation_Phase2"
    ["weather_test_clear"]="Clear_Weather_Test"
    ["weather_test_tropical"]="Tropical_Test_Coverage"
    ["storm_test"]="Storm_Test_Coverage"
    ["highres"]="HighRes_Global_Coverage"
)

declare -A SCENARIO_CATEGORIES=(
    ["ais_legacy_spire1"]="01_Competitor_Analysis"
    ["ais_legacy_spire2"]="01_Competitor_Analysis"
    ["ais_legacy_spire3"]="01_Competitor_Analysis"
    ["iridium"]="01_Competitor_Analysis"
    ["vdes_3planes"]="02_VDES_Options"
    ["vdes_4planes"]="02_VDES_Options"
    ["vdes_phase2"]="03_Phase2_Expansion"
    ["weather_test_clear"]="04_Weather_Testing"
    ["weather_test_tropical"]="04_Weather_Testing"
    ["storm_test"]="04_Weather_Testing"
    ["highres"]="05_High_Resolution"
)

# Check if command is a scenario command
if [[ "$COMMAND" =~ ^(scenario|sc)$ ]]; then
    SCENARIO_KEY=$NAME
    VIEW_TYPE=$3
    
    if [ -z "$SCENARIO_KEY" ]; then
        echo -e "${RED}❌ Error: Scenario key required${NC}"
        echo ""
        echo -e "${YELLOW}Available scenarios:${NC}"
        echo "  ais_legacy_spire1       - Spire AIS constellation variant 1 (60 sats, SSO)"
        echo "  ais_legacy_spire2       - Spire AIS constellation variant 2 (33 sats, 51.6°)"
        echo "  ais_legacy_spire3       - Spire AIS constellation variant 3 (4 sats, 82°)"
        echo "  iridium                 - Iridium NEXT style MSS (66 sats, 86.4°, bidirectional)"
        echo "  vdes_3planes            - Maritime VDES Option A (12 sats, 3 planes)"
        echo "  vdes_4planes            - Maritime VDES Option B (12 sats, 4 planes)"
        echo "  vdes_phase2             - Phase 2 Expansion (24 sats, 8 planes)"
        echo "  weather_test_clear      - Clear weather baseline (66 sats, SSO)"
        echo "  weather_test_tropical   - Tropical weather testing (66 sats, SSO)"
        echo "  storm_test              - Storm weather testing (66 sats, SSO, bidirectional)"
        echo "  highres                 - High-resolution heatmap (66 sats, SSO, 2° grid)"
        echo ""
        echo -e "${YELLOW}Usage:${NC}"
        echo "  ./batch.sim.sh scenario <scenario_key> <view_type>"
        echo "  ./batch.sim.sh sc <scenario_key> <view_type>"
        echo ""
        echo -e "${YELLOW}View types:${NC} orbit, track, coverage, heatmap, all"
        echo ""
        echo -e "${YELLOW}Examples:${NC}"
        echo "  ./batch.sim.sh scenario ais_legacy_spire1 all"
        echo "  ./batch.sim.sh sc iridium heatmap"
        echo "  ./batch.sim.sh scenario vdes_3planes orbit"
        echo "  ./batch.sim.sh sc storm_test all"
        exit 1
    fi
    
    if [ -z "$VIEW_TYPE" ]; then
        echo -e "${RED}❌ Error: View type required${NC}"
        echo "Valid view types: orbit, track, coverage, heatmap, all"
        exit 1
    fi
    
    if [[ ! -v SCENARIOS[$SCENARIO_KEY] ]]; then
        echo -e "${RED}❌ Error: Unknown scenario '$SCENARIO_KEY'${NC}"
        echo ""
        echo -e "${YELLOW}Available scenarios:${NC}"
        for key in "${!SCENARIOS[@]}"; do
            echo "  $key"
        done | sort
        exit 1
    fi
    
    SCENARIO_PARAMS="${SCENARIOS[$SCENARIO_KEY]}"
    SCENARIO_NAME="${SCENARIO_NAMES[$SCENARIO_KEY]}"
    SCENARIO_CATEGORY="${SCENARIO_CATEGORIES[$SCENARIO_KEY]}"
    
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}📡 Running Scenario: $SCENARIO_KEY${NC}"
    echo -e "${BLUE}Name:${NC} $SCENARIO_NAME"
    echo -e "${BLUE}Category:${NC} $SCENARIO_CATEGORY"
    echo -e "${BLUE}View:${NC} $VIEW_TYPE"
    echo -e "${BLUE}Parameters:${NC} $SCENARIO_PARAMS"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    
    case "$VIEW_TYPE" in
        orbit)
            run_orbit "$SCENARIO_NAME" $SCENARIO_PARAMS
            ;;
        track)
            run_track "$SCENARIO_NAME" $SCENARIO_PARAMS
            ;;
        coverage)
            # Add coverage-type for coverage runs if not already in params
            if [[ ! "$SCENARIO_PARAMS" =~ "--coverage" ]]; then
                SCENARIO_PARAMS="$SCENARIO_PARAMS --coverage both"
            fi
            run_coverage "$SCENARIO_NAME" $SCENARIO_PARAMS
            ;;
        heatmap)
            run_heatmap "$SCENARIO_NAME" $SCENARIO_PARAMS
            ;;
        heatmap-rf)
            run_heatmap_rf "$SCENARIO_NAME" $SCENARIO_PARAMS
            ;;
        all)
            run_all "$SCENARIO_NAME" "$SCENARIO_CATEGORY" $SCENARIO_PARAMS
            ;;
        *)
            echo -e "${RED}❌ Error: Unknown view type '$VIEW_TYPE'${NC}"
            echo "Valid view types: orbit, track, coverage, heatmap, heatmap-rf, all"
            exit 1
            ;;
    esac
    
    exit 0
fi

# ==============================================================================
# MAIN EXECUTION - REGULAR COMMANDS
# ==============================================================================

if [ -z "$NAME" ]; then
    echo -e "${RED}❌ Error: Simulation name required${NC}"
    echo "Usage: ./batch.sim.sh <command> <name> [options]"
    echo "Run './batch.sim.sh help' for more information"
    exit 1
fi

# Remove command and name from arguments
shift 2
ARGS="$@"

# Set defaults if not specified (only common constellation parameters)
DEFAULT_ARGS=""
if [[ ! "$ARGS" =~ "--sats" ]]; then DEFAULT_ARGS="$DEFAULT_ARGS --sats 66"; fi
if [[ ! "$ARGS" =~ "--planes" ]]; then DEFAULT_ARGS="$DEFAULT_ARGS --planes 6"; fi
if [[ ! "$ARGS" =~ "--inc" ]] && [[ ! "$ARGS" =~ "--sso" ]]; then DEFAULT_ARGS="$DEFAULT_ARGS --inclination 87.4"; fi
if [[ ! "$ARGS" =~ "--alt" ]]; then DEFAULT_ARGS="$DEFAULT_ARGS --altitude 600"; fi
if [[ ! "$ARGS" =~ "--phasing" ]]; then DEFAULT_ARGS="$DEFAULT_ARGS --phasing 1"; fi

# Combine default and user args
FULL_ARGS="$DEFAULT_ARGS $ARGS"

# Execute command
case "$COMMAND" in
    orbit)
        run_orbit "$NAME" $FULL_ARGS --map --trails
        ;;
    track)
        run_track "$NAME" $FULL_ARGS --map
        ;;
    coverage)
        run_coverage "$NAME" $FULL_ARGS
        ;;
    heatmap)
        run_heatmap "$NAME" $FULL_ARGS
        ;;
    heatmap-rf)
        run_heatmap_rf "$NAME" $FULL_ARGS
        ;;
    all)
        # Extract category if provided via --category flag
        CATEGORY=""
        if [[ "$FULL_ARGS" =~ --category[[:space:]]+([^[:space:]]+) ]]; then
            CATEGORY="${BASH_REMATCH[1]}"
            FULL_ARGS=$(echo "$FULL_ARGS" | sed -E 's/--category[[:space:]]+[^[:space:]]+//')
        fi
        run_all "$NAME" "$CATEGORY" $FULL_ARGS
        ;;
    *)
        echo -e "${RED}❌ Error: Unknown command '$COMMAND'${NC}"
        echo "Valid commands: orbit, track, coverage, heatmap, heatmap-rf, all, scenario, sc, help"
        exit 1
        ;;
esac

# ==============================================================================
# EXAMPLE MANUAL COMMANDS (for reference)
# ==============================================================================

# Run predefined scenarios using the scenario command:
# ./batch.sim.sh scenario ais_legacy all
# ./batch.sim.sh scenario iridium heatmap
# ./batch.sim.sh scenario vdes_3planes orbit
# ./batch.sim.sh scenario vdes_4planes track
# ./batch.sim.sh scenario vdes_phase2 coverage
# ./batch.sim.sh scenario weather_test coverage
# ./batch.sim.sh scenario highres heatmap

# Or use the short form 'sc':
# ./batch.sim.sh sc ais_legacy all
# ./batch.sim.sh sc iridium heatmap

# Manual commands (original style):
# ./batch.sim.sh all "Competitor_AIS_Legacy" --sats 60 --planes 6 --sso --comms ais --phasing 1
# ./batch.sim.sh all "Competitor_MSS_Iridium" --sats 66 --planes 6 --inc 86.4 --altitude 780 --comms mss --phasing 1 --bidi
# ./batch.sim.sh all "MyConstellation_OptionA" --sats 12 --planes 3 --inc 53.0 --altitude 600 --comms vdes --phasing 1
# ./batch.sim.sh all "MyConstellation_OptionB" --sats 12 --planes 4 --inc 53.0 --altitude 600 --comms vdes --phasing 1
# ./batch.sim.sh all "MyConstellation_Phase2" --sats 24 --planes 8 --inc 53.0 --altitude 600 --comms vdes --phasing 1
# ./batch.sim.sh coverage "weather_test_Coverage" --sats 66 --planes 6 --sso --comms vdes --weather storm --coverage-type all
# ./batch.sim.sh heatmap "HighRes_Global_Coverage" --sats 66 --planes 6 --sso --comms vdes --res 2.0
