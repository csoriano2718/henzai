# Agent Shortcuts - Quick Commands

**When the user says these phrases, run the corresponding commands WITHOUT asking:**

---

## Installation (Main Use Case)

### "install" / "deploy" / "install main"
```bash
cd /home/csoriano/henzAI && ./install.sh
```
**What it does:**
- Installs daemon (Python) + extension (GNOME Shell)
- Restarts daemon service
- **User must reload GNOME Shell after** (Alt+F2 → r → Enter)

**Use this for:**
- After making any changes (daemon OR extension)
- Initial setup
- Deploying to main session

---

## Testing (Optional - Only if Worried About Crashes)

### "test" / "test nested" / "nested"
```bash
cd /home/csoriano/henzAI && ./dev/dev-test.sh
```
**What it does:**
- Opens nested GNOME Shell window
- Isolated daemon (won't affect main session)
- Safe for testing risky changes

**Reality check:**
- Still need to reload main GNOME Shell (Alt+F2 → r)
- Adds ~10 seconds vs just testing in main
- **Most of the time, just use `./install.sh` and test in main session**

### "kill nested" / "cleanup nested"
```bash
cd /home/csoriano/henzAI && ./dev/cleanup-nested.sh
```
**What it does:**
- Kills all nested shell processes
- Run if nested window gets stuck

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

### "logs" / "daemon logs"
```bash
journalctl --user -u henzai-daemon -n 50 --no-pager
```

### "ramalama logs"
```bash
journalctl --user -u ramalama -n 50 --no-pager
```

### "status" / "check status"
```bash
systemctl --user status henzai-daemon ramalama --no-pager
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

## Testing (Automated Tests)

### "run tests" / "test all"
```bash
cd /home/csoriano/henzAI && ./tests/run-tests.sh
```
**What it does:**
- Runs all automated tests (unit + integration + RAG)
- Checks prerequisites (starts services if needed)
- Shows pass/fail summary

### "test rag" / "test rag only"
```bash
cd /home/csoriano/henzAI && ./tests/run-tests.sh rag
```
**What it does:**
- Runs only RAG tests (e2e + reasoning)
- Verifies RAG modes work correctly
- Tests reasoning + RAG integration

### "test unit" / "unit tests"
```bash
cd /home/csoriano/henzAI && ./tests/run-tests.sh unit
```
**What it does:**
- Runs daemon unit tests only
- Fast (no service dependencies)

---

## Rules for Agent

1. **DEFAULT ACTION:** When user says "install" → run `./install.sh` → tell user to reload GNOME Shell
2. **NEVER** manually pack extensions or copy files
3. **NEVER** use `sudo` for henzai installation
4. **ALWAYS** mention "reload GNOME Shell (Alt+F2 → r)" after installing
5. **NESTED TESTING:** Only suggest if user is worried about crashes
6. Most of the time: `./install.sh` + reload + test in main session is enough!

---

## Quick Reference

| User Says | Run This | Then Tell User |
|-----------|----------|----------------|
| **"install"** | `./install.sh` | "Reload GNOME Shell: Alt+F2 → r" |
| **"test"** | `./dev/dev-test.sh` | "Check the nested window + reload main shell" |
| **"run tests"** | `./tests/run-tests.sh` | Show test results |
| **"test rag"** | `./tests/run-tests.sh rag` | Show RAG test results |
| **"logs"** | `journalctl --user -u henzai-daemon -n 50 --no-pager` | Show output |
| **"status"** | `systemctl --user status henzai-daemon ramalama --no-pager` | Show output |
| **"restart daemon"** | `systemctl --user restart henzai-daemon` | "Restarted" |

---

**Keep it simple: `./install.sh` is your main tool. Use it!**

