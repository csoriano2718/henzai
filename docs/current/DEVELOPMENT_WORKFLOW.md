# henzai Development Workflow

## Quick Reference

```bash
# UI-only changes (fast, nested shell)
./dev-ui.sh

# Full testing with daemon (main session)
./dev-full.sh

# One-time initial install
./install.sh
```

## Workflow Details

### 1. UI Development (`dev-ui.sh`)
**Use for:** Colors, layout, styling, animations, UI components

**What it does:**
- Reinstalls extension with latest code
- Launches nested GNOME Shell (1600x1200 window)
- Fast iteration - just close and rerun

**Limitations:**
- No daemon connection (D-Bus error is expected)
- Can't test AI responses or system actions
- Just for visual/UI testing

**Logs:**
- `/tmp/henzai-gnome-shell.log`

---

### 2. Full Testing (`dev-full.sh`)
**Use for:** Daemon changes, AI responses, system actions, D-Bus, full integration

**What it does:**
- Reinstalls extension
- Restarts daemon service
- Reloads extension in your main session

**Testing:**
- Press `Super+H` in your main desktop
- Full functionality available
- Real daemon connection

**Logs:**
- Extension: `journalctl -f /usr/bin/gnome-shell | grep -i henzai`
- Daemon: `journalctl --user -u henzai-daemon -f`

---

## Development Iteration Examples

### UI Change (button color)
```bash
# 1. Edit stylesheet.css
nano henzai-extension/stylesheet.css

# 2. Test in nested shell
./dev-ui.sh

# 3. Repeat until satisfied
```

### Daemon Change (new tool)
```bash
# 1. Edit tools.py
nano henzai-daemon/henzai/tools.py

# 2. Test in main session
./dev-full.sh

# 3. Check logs
journalctl --user -u henzai-daemon -n 50
```

### Full Feature (UI + Daemon)
```bash
# 1. Develop UI first with ./dev-ui.sh (fast iteration)
./dev-ui.sh

# 2. Then test full integration with ./dev-full.sh
./dev-full.sh
```

---

## Troubleshooting

### Extension Not Reloading
On Wayland, extensions cache heavily. If changes don't appear:
1. Log out and log back in (most reliable)
2. Or use nested shell for UI changes

### Daemon Not Starting
```bash
# Check status
systemctl --user status henzai-daemon

# View recent logs
journalctl --user -u henzai-daemon -n 50

# Restart manually
systemctl --user restart henzai-daemon
```

### Nested Shell Issues
- D-Bus errors are expected (no daemon in nested session)
- Close window and rerun script for new changes
- Check logs: `cat /tmp/henzai-gnome-shell.log`

---

## Log Locations

| Component | Log Location |
|-----------|-------------|
| Nested Shell | `/tmp/henzai-gnome-shell.log` |
| Main Extension | `journalctl -f /usr/bin/gnome-shell \| grep -i henzai` |
| Daemon | `journalctl --user -u henzai-daemon` |
| Daemon (dev script) | `/tmp/henzai-daemon-dev.log` |

---

## Best Practices

1. **Use `dev-ui.sh` for fast UI iteration** - much faster than logging out
2. **Use `dev-full.sh` before committing** - test full integration
3. **Check logs after each test** - catch errors early
4. **Version number in UI** - increment `vXX` in chatPanel.js to verify reloads
5. **Git commit frequently** - small, working increments

---

## Script Internals

Both scripts:
1. Run `./install.sh` to copy files
2. Enable the extension
3. Set up logging
4. Launch test environment

The main difference:
- `dev-ui.sh`: Nested shell (isolated, no daemon)
- `dev-full.sh`: Main session (full integration)







