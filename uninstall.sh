#!/usr/bin/env bash
# Uninstallation script for henzai

set -e

echo "======================================"
echo "henzai Uninstallation Script"
echo "======================================"
echo

# Stop and disable services
echo "Stopping services..."
systemctl --user stop henzai-daemon.service || true
systemctl --user disable henzai-daemon.service || true
systemctl --user stop ramalama.service || true
systemctl --user disable ramalama.service || true

# Remove systemd services
echo "Removing systemd services..."
rm -f ~/.config/systemd/user/henzai-daemon.service
rm -f ~/.config/systemd/user/ramalama.service
systemctl --user daemon-reload

# Disable and remove extension
echo "Removing GNOME Shell extension..."
gnome-extensions disable henzai@csoriano || true
rm -rf ~/.local/share/gnome-shell/extensions/henzai@csoriano

# Uninstall Python package
echo "Uninstalling Python package..."
pip3 uninstall -y henzai || true

echo
echo "======================================"
echo "Uninstallation Complete!"
echo "======================================"
echo
echo "Note: Conversation history and settings remain at:"
echo "  ~/.local/share/henzai/"
echo
echo "To completely remove all data:"
echo "  rm -rf ~/.local/share/henzai/"
echo





