#!/bin/bash
# Full testing - main session with daemon
# Use this for testing daemon changes and full functionality

set -e

echo "==========================================="
echo "henzai Full Test (Main Session)"
echo "==========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}[1/4]${NC} Reinstalling extension..."
./install.sh > /dev/null 2>&1
echo -e "${GREEN}✓${NC} Done"

echo -e "${BLUE}[2/4]${NC} Restarting daemon..."
systemctl --user restart henzai-daemon
sleep 1
if systemctl --user is-active --quiet henzai-daemon; then
    echo -e "${GREEN}✓${NC} Daemon is running"
else
    echo -e "${RED}✗${NC} Daemon failed to start"
    echo "Check logs: journalctl --user -u henzai-daemon -n 50"
    exit 1
fi

echo -e "${BLUE}[3/4]${NC} Reloading extension..."
gnome-extensions disable henzai@csoriano 2>/dev/null || true
sleep 1
gnome-extensions enable henzai@csoriano 2>/dev/null || true
echo -e "${GREEN}✓${NC} Done"

echo -e "${BLUE}[4/4]${NC} Checking status..."
VERSION=$(gnome-extensions info henzai@csoriano | grep "Version:" | awk '{print $2}')
STATE=$(gnome-extensions info henzai@csoriano | grep "State:" | awk '{print $2}')
echo -e "${GREEN}✓${NC} Extension v${VERSION} is ${STATE}"

echo ""
echo "==========================================="
echo -e "${GREEN}Ready to test!${NC}"
echo "==========================================="
echo ""
echo "Press Super+A to open henzai"
echo ""
echo -e "${YELLOW}To view daemon logs:${NC}"
echo "  journalctl --user -u henzai-daemon -f"
echo ""
echo -e "${YELLOW}To view extension logs:${NC}"
echo "  journalctl -f /usr/bin/gnome-shell | grep -i henzai"







