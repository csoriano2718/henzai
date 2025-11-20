#!/bin/bash
# Restart nested GNOME Shell for UI testing

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                    Restart Nested GNOME Shell                                ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Kill everything
echo "🔪 Killing old nested shells..."
pkill -f "gnome-shell.*nested" 2>/dev/null
pkill -f "dev-ui.sh" 2>/dev/null
sleep 2

# Reinstall
echo "📦 Installing extension..."
cd "$(dirname "$0")/.." || exit 1
./install.sh > /dev/null 2>&1
echo "✅ Installed"
echo ""

# Start nested shell
echo "🚀 Starting nested shell..."
./dev/dev-ui.sh > /dev/null 2>&1 &
sleep 8

# Check if running
if ps aux | grep -q "[g]nome-shell.*nested"; then
    echo "✅ Nested shell is running!"
    echo ""
    echo "📝 Ready for testing"
    echo ""
else
    echo "❌ Failed to start nested shell"
    exit 1
fi

