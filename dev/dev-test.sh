#!/bin/bash
# Development testing script for henzai extension
# Runs a nested GNOME Shell session with its own daemon instance

set -e

# Log files
LOG_FILE="/tmp/henzai-dev-test.log"
GNOME_LOG="/tmp/henzai-gnome-shell.log"
DAEMON_LOG="/tmp/henzai-daemon-dev.log"

# Dev daemon socket
DEV_DBUS_ADDRESS="unix:path=/tmp/henzai-dev-dbus.sock"

echo "======================================"
echo "henzai Development Test Environment"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Clear previous logs
> "$LOG_FILE"
> "$GNOME_LOG"
> "$DAEMON_LOG"

# Cleanup function
cleanup() {
    echo ""
    echo -e "${BLUE}Cleaning up...${NC}"
    
    # Kill any remaining nested shells
    pkill -9 -f "gnome-shell --nested" 2>/dev/null || true
    
    # Kill dev daemon processes
    pkill -9 -f "python3 -m henzai.main" 2>/dev/null || true
    
    # Clean up PID files
    rm -f /tmp/henzai-dev-daemon.pid
    
    echo -e "${GREEN}✓${NC} Cleanup complete"
}

# Set trap to cleanup on exit
trap cleanup EXIT INT TERM

# Step 1: Reinstall extension
# CRITICAL: Always reinstall to test latest code changes!
# This is a fresh install every time to catch any errors.
echo -e "${BLUE}[1/3]${NC} Reinstalling extension (FRESH INSTALL)..."
echo "  → Clearing cache..."
rm -rf ~/.cache/gnome-shell/extensions/henzai@csoriano 2>/dev/null || true
echo "  → Running install.sh..."
./install.sh > /dev/null 2>&1
echo -e "${GREEN}✓${NC} Extension files updated"

# Verify version and critical files
INSTALLED_VERSION=$(grep '"version":' ~/.local/share/gnome-shell/extensions/henzai@csoriano/metadata.json | grep -oP '\d+')
echo "  Installed version: v${INSTALLED_VERSION}"

# CRITICAL: Verify key files exist and have latest changes
echo "  → Verifying critical files..."
if ! grep -q "import GLib" ~/.local/share/gnome-shell/extensions/henzai@csoriano/dbus/client.js; then
    echo -e "${RED}✗${NC} ERROR: client.js missing GLib import!"
    exit 1
fi
if ! grep -q "g_default_timeout = -1" ~/.local/share/gnome-shell/extensions/henzai@csoriano/dbus/client.js; then
    echo -e "${RED}✗${NC} ERROR: client.js missing proxy timeout fix!"
    exit 1
fi
echo -e "${GREEN}✓${NC} All critical fixes verified in installed extension"

# Step 2: Enable extension
echo -e "${BLUE}[2/3]${NC} Enabling extension..."
gnome-extensions enable henzai@csoriano 2>/dev/null || true
echo -e "${GREEN}✓${NC} Extension enabled"

# Step 3: Launch nested shell with daemon in same D-Bus session
echo -e "${BLUE}[3/3]${NC} Launching nested shell with daemon..."
echo ""
echo -e "${YELLOW}Instructions:${NC}"
echo "  • A large nested GNOME Shell window will open (1600x1200)"
echo "  • Press Super+A to test the extension"
echo "  • Daemon and shell share the same D-Bus session"
echo "  • All output is logged for debugging"
echo "  • Close the window when done testing"
echo ""
echo -e "${YELLOW}Logs:${NC}"
echo "  Main log:     ${LOG_FILE}"
echo "  GNOME log:    ${GNOME_LOG}"
echo "  Daemon log:   ${DAEMON_LOG}"
echo ""
echo -e "${GREEN}Starting nested shell with daemon...${NC}"
echo ""

# Launch nested session with daemon in same D-Bus
chmod +x "$(dirname "$0")/nested-with-daemon.sh"
dbus-run-session -- "$(dirname "$0")/nested-with-daemon.sh"

echo ""
echo -e "${GREEN}✓${NC} Nested shell closed"
echo ""
echo -e "${BLUE}Logs saved to:${NC}"
echo "  • GNOME Shell: ${GNOME_LOG}"
echo "  • Daemon:      ${DAEMON_LOG}"
echo ""
echo -e "${YELLOW}To view henzai errors:${NC}"
echo "  grep -i 'henzai.*error' ${GNOME_LOG}"
echo ""
echo -e "${YELLOW}To view daemon logs:${NC}"
echo "  cat ${DAEMON_LOG}"
echo ""
echo "Run './dev-test.sh' again to test new changes!"

