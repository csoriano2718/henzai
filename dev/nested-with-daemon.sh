#!/usr/bin/env bash
# Start nested GNOME Shell with henzai daemon
# This creates an isolated D-Bus session for testing
set -e

echo "Starting nested GNOME Shell with henzai daemon..."
echo "Window size: 1600x1200"
echo "Press Ctrl+C to stop"
echo ""

# Create new D-Bus session and start both daemon and nested shell
dbus-run-session -- bash -c '
    # Start the daemon in this session using the installed command
    echo "Starting henzai daemon..."
    ~/.local/bin/henzai-daemon &
    DAEMON_PID=$!
    
    # Wait a moment for daemon to initialize
    sleep 3
    
    # Start nested shell with bigger window
    echo "Starting nested shell..."
    MUTTER_DEBUG_DUMMY_MODE_SPECS=1600x1200 gnome-shell --nested --wayland
    
    # Clean up daemon when shell exits
    kill $DAEMON_PID 2>/dev/null || true
'
