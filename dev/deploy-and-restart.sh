#!/bin/bash
# Deploy changes and restart nested shell
# THIS SCRIPT MUST BE RUN AFTER ANY CODE CHANGES TO DAEMON OR EXTENSION

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "======================================="
echo "Deploy and Restart henzai Dev Environment"
echo "======================================="
echo ""

# Determine what changed
DAEMON_CHANGED=false
EXTENSION_CHANGED=false

if [ "$1" == "daemon" ] || [ "$1" == "both" ]; then
    DAEMON_CHANGED=true
fi

if [ "$1" == "extension" ] || [ "$1" == "both" ]; then
    EXTENSION_CHANGED=true
fi

# If no argument, assume both changed
if [ -z "$1" ]; then
    DAEMON_CHANGED=true
    EXTENSION_CHANGED=true
fi

# Deploy daemon if changed
if [ "$DAEMON_CHANGED" == "true" ]; then
    echo "[1/4] Installing daemon..."
    cd "$PROJECT_ROOT/henzai-daemon"
    pip install -e . --quiet
    echo "✅ Daemon installed"
fi

# Deploy extension if changed
if [ "$EXTENSION_CHANGED" == "true" ]; then
    echo "[2/4] Installing extension..."
    cp -r "$PROJECT_ROOT/henzai-extension/"* ~/.local/share/gnome-shell/extensions/henzai@csoriano/
    echo "✅ Extension installed"
fi

# Kill everything
echo "[3/4] Killing nested shell and daemons..."
pkill -9 -f "gnome-shell --nested" 2>/dev/null || true
pkill -9 -f "henzai-daemon-dev" 2>/dev/null || true
pkill -9 -f "henzai-nested-helper" 2>/dev/null || true
sleep 3
echo "✅ Processes killed"

# Restart nested shell
echo "[4/4] Starting nested shell..."
cd "$PROJECT_ROOT"
nohup ./dev/nested-with-daemon.sh > /tmp/henzai-deploy-restart.log 2>&1 &

echo ""
echo "Waiting for nested shell to start..."
for i in {1..30}; do
    sleep 1
    if pgrep -f "gnome-shell --nested" > /dev/null; then
        echo ""
        echo "======================================="
        echo "✅ NESTED SHELL IS RUNNING!"
        echo "======================================="
        echo ""
        echo "The window should be visible now."
        echo "Press Super+H to test henzai."
        echo ""
        exit 0
    fi
    echo -n "."
done

echo ""
echo "⚠️  Nested shell did not start within 30 seconds."
echo "Check logs: tail -f /tmp/henzai-deploy-restart.log"
exit 1

