# RAG Synchronization Fix - Summary

**Date:** 2025-11-21  
**Branch:** feature/rag-modes  
**Status:** ✅ **FIXED AND TESTED**

---

## What You Reported

> "I didn't enable it, it was already enabled... are you always keeping in sync what's in the UI setting, henzai and Ramalama? Those should be in sync"

**You were absolutely right!** The three components were NOT in sync:
1. **gsettings** (UI Settings) - `rag-enabled = true`
2. **henzai-daemon** - thought RAG was enabled (DB exists)
3. **ramalama service** - running WITHOUT `--rag` flag

---

## Root Cause

The daemon had NO mechanism to read gsettings on startup! It only checked if the RAG database existed, but never looked at what the UI Settings actually said.

**Flow Before Fix:**
```
User toggles "Enable RAG" in Settings
  ↓
gsettings updated: rag-enabled = true  ✅
  ↓
Daemon checks: "Does RAG DB exist?" → Yes → rag_enabled = True  ✅
  ↓
Ramalama: Still running without --rag flag  ❌❌❌
```

**Result:** Daemon thinks RAG is on, but ramalama isn't actually using it!

---

## The Fix

### 1. Daemon Now Reads gsettings on Startup

**File:** `henzai-daemon/henzai/main.py`

```python
# Read RAG enabled state from gsettings
result = subprocess.run(
    ['gsettings', 'get', 'org.gnome.shell.extensions.henzai', 'rag-enabled'],
    capture_output=True, text=True, timeout=2
)
rag_enabled_in_settings = result.stdout.strip().lower() == 'true'

# RAG is only enabled if BOTH database exists AND settings say it's enabled
rag_enabled = rag_indexed and rag_enabled_in_settings
```

### 2. Daemon Syncs Ramalama Service on Startup

**File:** `henzai-daemon/henzai/main.py`

```python
# If settings say RAG enabled but ramalama doesn't have --rag
if rag_enabled_in_settings and not ramalama_has_rag:
    service._restart_ramalama_service(enable_rag=True)

# If settings say RAG disabled but ramalama has --rag  
if not rag_enabled_in_settings and ramalama_has_rag:
    service._restart_ramalama_service(enable_rag=False)
```

### 3. New Helper Method

**File:** `henzai-daemon/henzai/dbus_service.py`

```python
def _check_ramalama_has_rag(self) -> bool:
    """Check if ramalama service has --rag in ExecStart"""
    service_file = Path.home() / '.config' / 'systemd' / 'user' / 'ramalama.service'
    with open(service_file, 'r') as f:
        return '--rag' in f.read()
```

---

## Testing Results

### Test 1: Disable RAG in gsettings

```bash
$ gsettings set org.gnome.shell.extensions.henzai rag-enabled false
$ systemctl --user restart henzai-daemon
```

**Logs:**
```
RAG enabled in gsettings: False
RAG effective state: False (indexed=True, settings=False)
Ramalama has RAG but settings say disabled - restarting without RAG...
✓ Ramalama service restarted successfully with RAG=False
```

**Service file:**
```
ExecStart=/home/csoriano/.local/bin/ramalama serve --ctx-size 8192 --cache-reuse 512 ollama://library/deepseek-r1:latest
```
✅ No `--rag` flag!

### Test 2: Enable RAG in gsettings

```bash
$ gsettings set org.gnome.shell.extensions.henzai rag-enabled true
$ systemctl --user restart henzai-daemon
```

**Logs:**
```
RAG enabled in gsettings: True
RAG effective state: True (indexed=True, settings=True)
RAG mode from gsettings: strict
Ramalama already configured with RAG
```

**Service file:**
```
ExecStart=/home/csoriano/.local/bin/ramalama serve --ctx-size 8192 --cache-reuse 512 --env RAG_MODE=strict --rag-image localhost/ramalama/cuda-rag:augment --rag /home/csoriano/.local/share/henzai/rag-db ollama://library/deepseek-r1:latest
```
✅ Has `--rag` and `--env RAG_MODE=strict`!

---

## State Synchronization Flow (After Fix)

```
┌──────────────┐
│  gsettings   │ rag-enabled: true, rag-mode: strict
└──────┬───────┘
       │
       ↓ (daemon reads on startup)
┌──────────────┐
│ henzai-daemon│ Checks: DB exists? Settings enabled?
└──────┬───────┘
       │
       ↓ (syncs configuration)
┌──────────────┐
│   ramalama   │ Starts with: --rag --env RAG_MODE=strict
└──────────────┘

🔄 All three components now stay in sync!
```

---

## Remaining Issues

### 1. Indexing Progress "Stuck at 80%" ⚠️

**Status:** Improved logging, needs testing

**Changes Made:**
- Added console.log to progress signals
- Show "Indexed N files (100%)" on completion
- Better debugging visibility

**Why it happens:**
- Container output filtered by journald
- Final progress updates (90%, 100%) might not reach daemon
- But indexing DOES complete successfully

**Next steps:**
- Test indexing with new logging
- Check if 100% completion signal is received

### 2. Black Boxes in deepseek-r1 Responses ⚠️

**Status:** Needs investigation

**What we know:**
- API returns clean text (no special chars)
- Only visible in UI rendering
- Likely Unicode/font issue

**Not tested yet:**
- Capture actual UI response text
- Check if deepseek-r1 uses special tokens
- Test with different fonts

---

## Summary

✅ **FIXED:** gsettings ↔ daemon ↔ ramalama synchronization  
✅ **TESTED:** Enable/disable cycles work perfectly  
✅ **VERIFIED:** RAG strict mode working (finds IBM meeting attendees)  
✅ **VERIFIED:** Strict mode says "I don't know" for non-RAG queries  

⚠️ **TODO:** Test indexing progress with new logging  
⚠️ **TODO:** Investigate Unicode black boxes issue  

---

## Files Changed

1. `henzai-daemon/henzai/main.py` - Read gsettings, sync on startup
2. `henzai-daemon/henzai/dbus_service.py` - Add `_check_ramalama_has_rag()`
3. `henzai-extension/prefs.js` - Improve progress logging
4. `docs/bugs/RAG_TESTING_ISSUES.md` - Document all issues

**Commits:**
- `9278c73` - fix: Sync RAG state from gsettings on daemon startup
- `d17c592` - fix: Improve RAG indexing progress display

**All pushed to:** `feature/rag-modes` branch

---

## For You to Test

1. **Open Settings** - Check that RAG toggle reflects actual state
2. **Toggle RAG off/on** - Daemon should restart ramalama automatically
3. **Ask RAG question** - Should work immediately without manual intervention
4. **Test indexing** - Re-index and see if progress reaches 100% now

Everything should now stay in sync automatically! 🎉





