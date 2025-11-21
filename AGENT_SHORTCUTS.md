# Agent Shortcuts - Quick Commands

**When the user says these phrases, run the corresponding scripts WITHOUT asking:**

---

## Installation & Deployment

### "install" / "install main" / "deploy main"
```bash
cd /home/csoriano/henzAI && ./install.sh
```
**What it does:**
- Installs henzai-daemon (Python) in user space
- Installs GNOME Shell extension
- Restarts daemon service
- **User must reload GNOME Shell after** (Alt+F2 → r → Enter)

### "install daemon" / "update daemon"
```bash
cd /home/csoriano/henzAI/henzai-daemon && \
pip install --user -e . && \
systemctl --user restart henzai-daemon
```
**What it does:**
- Only updates Python daemon code
- Restarts daemon service
- Faster than full install

### "install extension" / "update extension"
```bash
cd /home/csoriano/henzAI && \
rm -rf ~/.local/share/gnome-shell/extensions/henzai@csoriano && \
cp -r henzai-extension ~/.local/share/gnome-shell/extensions/henzai@csoriano
```
**What it does:**
- Only updates GNOME Shell extension
- **User must reload GNOME Shell after**

---

## Nested Shell Testing

### "test ui" / "nested shell" / "start nested"
```bash
cd /home/csoriano/henzAI && ./dev/dev-ui.sh
```
**What it does:**
- Starts nested GNOME Shell with extension loaded
- Uses main session's daemon
- Safe for testing UI changes

### "test full" / "full test" / "e2e test"
```bash
cd /home/csoriano/henzAI && ./dev/dev-test.sh
```
**What it does:**
- Starts nested shell with isolated daemon
- Complete E2E environment
- For testing daemon + extension together

### "restart nested" / "reload nested"
```bash
cd /home/csoriano/henzAI && ./dev/restart-nested.sh
```
**What it does:**
- Kills old nested shells
- Reinstalls extension
- Starts fresh nested shell

### "cleanup nested" / "kill nested"
```bash
cd /home/csoriano/henzAI && ./dev/cleanup-nested.sh
```
**What it does:**
- Kills all nested shells
- Cleans up processes

---

## Quick Reload (After Changes)

### "quick reload" / "reload extension"
```bash
cd /home/csoriano/henzAI && ./dev/reload-extension.sh
```
**What it does:**
- Disables extension
- Copies files
- Re-enables extension
- **User must reload GNOME Shell after**

### "deploy and restart"
```bash
cd /home/csoriano/henzAI && ./dev/deploy-and-restart.sh
```
**What it does:**
- Copies extension files
- Restarts daemon
- One-step update for both

---

## Service Management

### "restart daemon"
```bash
systemctl --user restart henzai-daemon
```

### "restart ramalama"
```bash
systemctl --user restart ramalama
```

### "restart services" / "restart all"
```bash
systemctl --user restart henzai-daemon ramalama
```

### "daemon logs" / "show logs"
```bash
journalctl --user -u henzai-daemon -n 50 --no-pager
```

### "daemon logs live" / "tail logs"
```bash
journalctl --user -u henzai-daemon -f
```
**Note:** This follows logs (Ctrl+C to stop)

### "ramalama logs"
```bash
journalctl --user -u ramalama -n 50 --no-pager
```

---

## Status Checks

### "check status" / "status"
```bash
systemctl --user status henzai-daemon ramalama --no-pager
```

### "check extension" / "extension status"
```bash
gnome-extensions info henzai@csoriano
```

### "check rag" / "rag status"
```bash
python3 -c "
import dbus
bus = dbus.SessionBus()
proxy = bus.get_object('org.gnome.henzai', '/org/gnome/henzai')
iface = dbus.Interface(proxy, 'org.gnome.henzai')
status = iface.GetRAGStatus('/home/csoriano/Documents/rag', True)
print(status)
"
```

---

## Common Workflows

### User says: "test my changes"
1. `./install.sh`
2. `./dev/restart-nested.sh`
3. Tell user to reload main GNOME Shell

### User says: "I changed daemon code"
1. `cd henzai-daemon && pip install --user -e . && systemctl --user restart henzai-daemon`
2. Done (daemon changes don't need GNOME Shell reload)

### User says: "I changed extension code"
1. `./dev/reload-extension.sh`
2. Tell user to reload GNOME Shell (Alt+F2 → r)

### User says: "test in nested"
1. `./dev/restart-nested.sh` (includes install)
2. Tell user nested window should appear

---

## Rules for Agent

1. **NEVER** manually pack extensions with `gnome-extensions pack`
2. **ALWAYS** use `./install.sh` for full installs
3. **ALWAYS** mention "reload GNOME Shell" after extension changes
4. **NEVER** use `sudo` for henzai installation
5. **ALWAYS** use scripts in `/home/csoriano/henzAI/dev/` for testing
6. When user says "install", run `./install.sh` - don't overthink it!

---

## Quick Reference Card

| User Says | Run This |
|-----------|----------|
| "install" | `./install.sh` |
| "install daemon" | `cd henzai-daemon && pip install --user -e . && systemctl --user restart henzai-daemon` |
| "test ui" | `./dev/dev-ui.sh` |
| "restart nested" | `./dev/restart-nested.sh` |
| "daemon logs" | `journalctl --user -u henzai-daemon -n 50 --no-pager` |
| "restart daemon" | `systemctl --user restart henzai-daemon` |
| "check status" | `systemctl --user status henzai-daemon ramalama --no-pager` |

---

**Last Updated:** 2025-11-21
**Always check this file at session start!**

