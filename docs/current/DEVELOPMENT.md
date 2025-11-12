# henzai Development Guide

This guide explains how to set up a development environment for henzai.

---

## Prerequisites

### System Requirements
- Fedora 42 (or compatible Linux with GNOME 47)
- Python 3.12+
- GNOME Shell 47
- Ramalama installed and configured

### Install Dependencies

```bash
# GNOME development tools
sudo dnf install gnome-shell-extension-tool

# Python development
sudo dnf install python3-devel python3-pip python3-dasbus

# D-Bus tools (for debugging)
sudo dnf install d-feet busctl

# Ramalama (if not installed)
# Follow: https://github.com/containers/ramalama
```

---

## Development Setup

### 1. Clone and Navigate

```bash
cd /home/csoriano/henzAI
```

### 2. Install Python Daemon in Development Mode

```bash
cd henzai-daemon
pip install --user -e .
```

### 3. Link GNOME Extension

```bash
# Create symlink for development
ln -sf $(pwd)/henzai-extension ~/.local/share/gnome-shell/extensions/henzai@csoriano

# Enable the extension
gnome-extensions enable henzai@csoriano
```

### 4. Start Daemon Manually (for development)

```bash
cd henzai-daemon
python -m henzai.main
```

Or use systemd:

```bash
systemctl --user enable --now henzai-daemon.service
```

---

## Development Workflow

### Testing Changes

**Python Daemon:**
```bash
# Stop the service
systemctl --user stop henzai-daemon

# Run manually for debugging
python -m henzai.main

# Restart service
systemctl --user start henzai-daemon
```

**GNOME Extension:**
```bash
# Reload GNOME Shell
# X11: Alt+F2, type 'r', press Enter
# Wayland: Log out and log back in

# Or disable/enable extension
gnome-extensions disable henzai@csoriano
gnome-extensions enable henzai@csoriano
```

### Viewing Logs

**Daemon logs:**
```bash
journalctl --user -u henzai-daemon.service -f
```

**GNOME Shell logs:**
```bash
journalctl -f /usr/bin/gnome-shell
```

**Extension errors:**
```bash
# Looking Glass (Alt+F2, type 'lg')
# Check Extensions tab for errors
```

### D-Bus Debugging

```bash
# List available services
busctl --user list | grep henzai

# Introspect the service
busctl --user introspect org.gnome.henzai /org/gnome/henzai

# Call a method manually
busctl --user call org.gnome.henzai /org/gnome/henzai org.gnome.henzai GetStatus

# Use d-feet GUI for interactive debugging
d-feet
```

---

## Project Structure

See `DOCUMENTATION_INDEX.md` for complete file organization.

**Key files to modify:**

- **Daemon logic**: `henzai-daemon/henzai/*.py`
- **Extension UI**: `henzai-extension/ui/chatPanel.js`
- **D-Bus interface**: Both `henzai-daemon/henzai/dbus_service.py` and `henzai-extension/dbus/client.js`
- **System actions**: `henzai-daemon/henzai/tools.py`

---

## Testing

### Manual Testing Checklist

- [ ] Daemon starts without errors
- [ ] Extension loads in GNOME Shell
- [ ] Chat panel opens with Super+Space
- [ ] Can send message and receive response
- [ ] App launching works ("open firefox")
- [ ] Settings control works ("enable dark mode")
- [ ] Conversation history persists after restart

### Unit Tests

```bash
cd henzai-daemon
pytest tests/
```

---

## Common Issues

### Extension won't load
- Check GNOME Shell version compatibility in `metadata.json`
- View errors: `journalctl -f /usr/bin/gnome-shell`
- Check syntax: `gjs extension.js`

### Daemon not responding
- Check if running: `systemctl --user status henzai-daemon`
- Check logs: `journalctl --user -u henzai-daemon -n 50`
- Test D-Bus manually with `busctl`

### Ramalama errors
- Verify Ramalama is installed: `ramalama --version`
- Check if model is downloaded: `ramalama list`
- Test model directly: `ramalama run <model> "Hello"`

---

## Contributing

1. Follow the AI Assistant Checklist (`AI_ASSISTANT_CHECKLIST.md`)
2. Check existing code before creating new files
3. Update documentation when changing interfaces
4. Test both daemon and extension after changes
5. Keep commits focused and well-described

---

## Additional Resources

- [GNOME Shell Extension Documentation](https://gjs.guide/extensions/)
- [D-Bus Specification](https://dbus.freedesktop.org/doc/dbus-specification.html)
- [Ramalama Documentation](https://github.com/containers/ramalama)
- [GJS API Reference](https://gjs-docs.gnome.org/)










