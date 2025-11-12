#!/bin/bash
# Cleanup script for nested shell sessions
# Prevents resource exhaustion by tracking and cleaning up all related processes

echo "=== henzai Nested Shell Cleanup ==="
echo ""

# Count processes before cleanup
NESTED_COUNT=$(pgrep -f "gnome-shell --nested" | wc -l)
DBUS_COUNT=$(pgrep -f "dbus-run-session.*gnome-shell" | wc -l)

echo "Found processes:"
echo "  - Nested shells: $NESTED_COUNT"
echo "  - DBus sessions: $DBUS_COUNT"
echo ""

if [ $NESTED_COUNT -eq 0 ] && [ $DBUS_COUNT -eq 0 ]; then
    echo "✓ No nested shells to clean up"
    exit 0
fi

# Get all nested shell PIDs and their children
echo "Cleaning up nested shell processes..."
for pid in $(pgrep -f "gnome-shell --nested"); do
    echo "  Killing nested shell PID $pid and children..."
    # Kill children first
    pkill -9 -P $pid 2>/dev/null || true
    # Then the main process
    kill -9 $pid 2>/dev/null || true
done

# Clean up dbus-run-session processes
echo "Cleaning up dbus sessions..."
for pid in $(pgrep -f "dbus-run-session.*gnome-shell"); do
    echo "  Killing dbus-run-session PID $pid..."
    kill -9 $pid 2>/dev/null || true
done

# Also clean up any orphaned dbus-daemon processes from nested shells
# (these have specific markers we can identify)
for pid in $(pgrep dbus-daemon); do
    # Check if this dbus-daemon is from a nested shell session
    if grep -q "gnome-shell.*nested" /proc/$pid/cmdline 2>/dev/null; then
        echo "  Killing orphaned dbus-daemon PID $pid..."
        kill -9 $pid 2>/dev/null || true
    fi
done

sleep 1

# Verify cleanup
REMAINING=$(pgrep -f "gnome-shell --nested" | wc -l)
if [ $REMAINING -eq 0 ]; then
    echo ""
    echo "✓ Cleanup complete - all nested shells stopped"
else
    echo ""
    echo "⚠ Warning: $REMAINING nested shells still running"
    echo "You may need to run: sudo systemctl restart systemd-logind"
fi

echo ""
echo "System resources:"
echo "  - Open files: $(lsof 2>/dev/null | wc -l)"
echo "  - Inotify watches: $(find /proc/*/fd -lname 'anon_inode:inotify' 2>/dev/null | wc -l)"


