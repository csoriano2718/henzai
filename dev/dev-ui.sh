#!/bin/bash
# Quick UI testing - nested shell without daemon
# Use this for UI-only changes (colors, layout, animations, etc.)

set -e

GNOME_LOG="/tmp/henzai-gnome-shell.log"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Cleanup function
cleanup() {
    echo ""
    echo "Cleaning up nested shell..."
    # Use dedicated cleanup script
    "$SCRIPT_DIR/cleanup-nested.sh" >/dev/null 2>&1 || {
        # Fallback if cleanup script fails
        pkill -TERM -f "gnome-shell --nested" 2>/dev/null || true
        sleep 1
        pkill -9 -f "gnome-shell --nested" 2>/dev/null || true
        pkill -9 -f "dbus-run-session.*gnome-shell" 2>/dev/null || true
    }
    echo "Cleanup complete"
}

# Set trap to cleanup on exit
trap cleanup EXIT INT TERM

echo "======================================"
echo "henzai UI Development (Nested Shell)"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check for resource issues before starting
NESTED_COUNT=$(pgrep -f "gnome-shell --nested" 2>/dev/null | wc -l)
if [ $NESTED_COUNT -gt 3 ]; then
    echo -e "${RED}⚠ Warning: $NESTED_COUNT nested shells already running${NC}"
    echo "Running cleanup first..."
    "$SCRIPT_DIR/cleanup-nested.sh"
    sleep 2
fi

# Clean up any existing nested shells
echo "Cleaning up old sessions..."
pkill -9 -f "gnome-shell --nested" 2>/dev/null || true
pkill -9 -f "dbus-run-session.*gnome-shell" 2>/dev/null || true
sleep 1

# Clear log
> "$GNOME_LOG"

echo -e "${BLUE}[1/3]${NC} Reinstalling extension..."
./install.sh > /dev/null 2>&1
echo -e "${GREEN}✓${NC} Done"

echo -e "${BLUE}[2/3]${NC} Enabling extension..."
gnome-extensions enable henzai@csoriano 2>/dev/null || true
echo -e "${GREEN}✓${NC} Done"

echo -e "${BLUE}[3/3]${NC} Launching nested shell (1600x1200)..."
echo ""
echo -e "${YELLOW}Test UI:${NC} Press Super+A"
echo -e "${YELLOW}Note:${NC} Daemon not available (UI testing only)"
echo -e "${YELLOW}Log:${NC} $GNOME_LOG"
echo ""

MUTTER_DEBUG_NUM_DUMMY_MONITORS=1 \
MUTTER_DEBUG_DUMMY_MODE_SPECS=1400x1000 \
dbus-run-session -- gnome-shell --nested --wayland --replace 2>&1 | tee -a "$GNOME_LOG"

echo ""
echo -e "${GREEN}✓${NC} Done. Run './dev-ui.sh' again for new UI changes!"





