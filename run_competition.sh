#!/bin/bash

# ==============================================================================
# COMPETITIVE ANALYSIS BATCH RUNNER
# ==============================================================================
# Simple wrapper to run all predefined scenarios
# Uses batch.sim.sh with scenario command - much simpler!
# ==============================================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BATCH_SCRIPT="$SCRIPT_DIR/batch.sim.sh"

# Force non-interactive matplotlib backend (save only, no display)
export MPLBACKEND=Agg

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# All predefined scenarios
SCENARIOS=("ais_legacy_spire1" "ais_legacy_spire2" "ais_legacy_spire3"  "vdes_3planes" "vdes_4planes" "vdes_phase2" "iridium" "storm_test" "highres")

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}🚀 COMPETITIVE CONSTELLATION ANALYSIS SUITE${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}Total Scenarios:${NC} ${#SCENARIOS[@]}"
echo -e "${CYAN}Output Location:${NC} output_sims/"
echo ""
echo -e "${YELLOW}This will run ALL scenarios with ALL views (orbit, track, heatmap)${NC}"
echo -e "${BLUE}Note: Orbit views include --map and --trails, Track views include --map${NC}"
echo ""
read -p "Press ENTER to start competitive analysis, or Ctrl+C to cancel..."

# Run each scenario
TOTAL=0
SUCCESS=0
FAIL=0

for scenario in "${SCENARIOS[@]}"; do
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Running scenario: $scenario${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    TOTAL=$((TOTAL + 1))
    
    if "$BATCH_SCRIPT" scenario "$scenario" all; then
        SUCCESS=$((SUCCESS + 1))
        echo -e "${GREEN}✓ Scenario $scenario completed successfully${NC}"
    else
        FAIL=$((FAIL + 1))
        echo -e "${RED}✗ Scenario $scenario failed${NC}"
    fi
done

# Print final summary
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ COMPETITIVE ANALYSIS COMPLETE${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Statistics:${NC}"
echo -e "  Total Scenarios: $TOTAL"
echo -e "  ${GREEN}Successful: $SUCCESS${NC}"
echo -e "  ${RED}Failed: $FAIL${NC}"
echo ""
echo -e "${CYAN}Results organized in:${NC}"
echo "  output_sims/"
echo "    ├── 01_Competitor_Analysis/"
echo "    │   ├── Competitor_AIS_Legacy/"
echo "    │   └── Competitor_MSS_Iridium/"
echo "    ├── 02_VDES_Options/"
echo "    │   ├── MyConstellation_OptionA/"
echo "    │   └── MyConstellation_OptionB/"
echo "    ├── 03_Phase2_Expansion/"
echo "    │   └── MyConstellation_Phase2/"
echo "    ├── 04_Weather_Testing/"
echo "    │   └── Tropical_Test_Coverage/"
echo "    └── 05_High_Resolution/"
echo "        └── HighRes_Global_Coverage/"
echo ""

exit 0
