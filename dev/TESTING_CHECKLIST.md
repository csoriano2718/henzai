# henzai Development Testing Checklist

## ⚠️ CRITICAL: Always Test with Fresh Install

**Problem**: Making code changes but forgetting to reinstall the extension means testing OLD code, leading to false errors and wasted debugging time.

**Solution**: ALWAYS run the dev-test.sh script which does a fresh install automatically.

---

## 🔄 Development Workflow

### 1. Make Code Changes
Edit files in:
- `henzai-extension/` - GNOME Shell extension (JavaScript)
- `henzai-daemon/` - Python daemon
- `henzai-extension/stylesheet.css` - UI styling

### 2. Test Changes (ALWAYS Fresh Install)

```bash
# From project root
cd /home/csoriano/henzAI
./dev/dev-test.sh
```

**What this does:**
1. ✅ Clears extension cache
2. ✅ Runs `install.sh` to copy latest code
3. ✅ **Verifies critical fixes are present in installed files**
4. ✅ Starts nested GNOME Shell with isolated D-Bus session
5. ✅ Starts dev daemon in same D-Bus session
6. ✅ Logs everything for debugging

### 3. Verify Installation

The script now automatically verifies:
- ✅ D-Bus timeout fix present (`call_finish`)
- ✅ GLib import present
- ✅ Version number correct

**If verification fails → Script exits with error**

---

## 🚫 Common Mistakes to Avoid

### ❌ DON'T: Assume code is installed
```bash
# This is WRONG - testing old code!
pkill -9 -f "gnome-shell --nested"
# ... make changes ...
# ... restart without reinstalling ...
```

### ✅ DO: Always use dev-test.sh
```bash
# This is RIGHT - fresh install every time!
./dev/dev-test.sh
```

---

## 🧪 Testing Specific Features

### Test Streaming Timeout Fix

1. Run nested shell: `./dev/dev-test.sh`
2. Open henzai: Press `Super+H` in nested window
3. Ask complex question: "Explain quantum entanglement"
4. Verify: No timeout errors in logs
5. Check logs: `tail -f /tmp/henzai-gnome-shell.log`

### Test Model Switching

1. Open henzai
2. Click model name at bottom
3. Click different model
4. Verify: Model changes, no errors

### Test Reasoning Mode

1. Ensure DeepSeek-R1 model is active
2. Ask question requiring reasoning
3. Verify: Purple thinking box appears
4. Verify: Lightbulb icon visible and correct opacity

---

## 📝 Before Declaring "It Works"

**CRITICAL CHECKLIST:**

- [ ] Made code changes in source files
- [ ] Ran `./dev/dev-test.sh` (fresh install)
- [ ] Script passed verification checks
- [ ] Nested window opened successfully
- [ ] Opened henzai with `Super+H`
- [ ] Sent test message
- [ ] **Verified actual behavior matches expected**
- [ ] Checked logs for errors: `grep -i error /tmp/henzai-gnome-shell.log`
- [ ] No D-Bus errors
- [ ] No JavaScript errors
- [ ] Response completed successfully

**Only after ALL checks pass → Feature is working**

---

## 🐛 Debugging Workflow

### When Something Breaks

1. **Check Logs First**
   ```bash
   # GNOME Shell errors
   tail -50 /tmp/henzai-gnome-shell.log | grep -i error
   
   # Daemon errors
   tail -50 /tmp/henzai-daemon-dev.log | grep -i error
   ```

2. **Verify Installation**
   ```bash
   # Check if fix is actually installed
   grep "call_finish" ~/.local/share/gnome-shell/extensions/henzai@csoriano/dbus/client.js
   ```

3. **Test D-Bus Separately**
   ```bash
   # Test daemon is responding
   python3 tests/test-dbus-timeout.py
   ```

4. **Make Fix**
   - Edit source files
   - **DO NOT assume it's installed**

5. **Test Fix (Fresh Install)**
   ```bash
   ./dev/dev-test.sh
   ```

6. **Verify Fix Actually Works**
   - Open henzai
   - Test the specific feature
   - Check logs
   - Confirm no errors

---

## 💡 Pro Tips

1. **Always tail logs during testing:**
   ```bash
   tail -f /tmp/henzai-gnome-shell.log
   ```

2. **Test Python daemon separately first:**
   ```bash
   python3 tests/test-dbus-timeout.py
   ```
   This isolates daemon vs extension issues.

3. **Use verification checks:**
   The dev-test.sh script now includes automatic verification.
   If it passes → code is installed.
   If it fails → fix the issue before testing.

4. **Document critical fixes:**
   When adding a critical fix, add it to the verification in dev-test.sh:
   ```bash
   if ! grep -q "YOUR_FIX_MARKER" ~/.local/share/.../file.js; then
       echo "ERROR: Fix not installed!"
       exit 1
   fi
   ```

---

## 📊 Success Metrics

**A feature is ONLY working when:**
- ✅ Fresh install succeeds
- ✅ Verification checks pass
- ✅ Nested shell starts
- ✅ No errors in logs
- ✅ **Feature behaves as expected in UI**
- ✅ User confirms it works

**Not working if:**
- ❌ Any error in logs
- ❌ Unexpected behavior
- ❌ "Should work" but not tested
- ❌ Tested old code by mistake

---

## 🎯 Remember

> **"It works in my code" ≠ "It works when installed"**
> 
> **Always test with fresh install!**

---

Generated (vibe-coded) by Cursor AI with Claude Sonnet 4.5

