#!/usr/bin/env bash
# Start nested GNOME Shell with bigger window for testing
# This uses the same D-Bus session so the extension can connect to the daemon
set -e

echo "Starting nested GNOME Shell (1600x1200)..."
echo "Press Ctrl+C to stop"
echo ""

# Use existing D-Bus session so extension can connect to main daemon
# The nested shell will inherit the parent session's D-Bus environment
MUTTER_DEBUG_DUMMY_MODE_SPECS=1600x1200 exec gnome-shell --nested --wayland

