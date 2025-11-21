# RAG Issues - Testing Results

**Date:** 2025-11-21  
**Branch:** feature/rag-modes  
**Status:** 🟡 **PARTIALLY WORKING** (manual intervention needed)

---

## Summary

RAG functionality **IS working** when properly enabled, but there are several UX/UI issues preventing smooth operation.

---

## Issue #1: Settings Toggle Doesn't Enable RAG ❌

**Severity:** HIGH  
**Status:** CONFIRMED BUG

### What Happens

1. User indexes documents (works - 9 PDFs indexed successfully)
2. User toggles "Enable RAG" in Settings
3. **gsettings updated** (`rag-enabled` = true)
4. **But `SetRagEnabled` D-Bus call never executed**
5. Ramalama not restarted with `--rag` flag
6. RAG remains inactive despite toggle showing "on"

### Expected Behavior

When toggle switched on → Settings should call `SetRagEnabled` D-Bus method → Daemon restarts ramalama with RAG enabled

### Actual Behavior

Toggle updates gsettings but D-Bus call doesn't fire (or fails silently)

### Manual Workaround

```bash
python3 -c "
import dbus
bus = dbus.SessionBus()
proxy = bus.get_object('org.gnome.henzai', '/org/gnome/henzai')
iface = dbus.Interface(proxy, 'org.gnome.henzai')
result = iface.SetRagEnabled(True, 'strict')
print(result)
"
```

After manual call, RAG works perfectly!

### Files Involved

- `henzai-extension/prefs.js` lines 185-188 (signal handler)
- `henzai-extension/prefs.js` lines 672-732 (`_setRagEnabled` method)

### Possible Causes

1. **Signal timing issue**: Settings bind might trigger signal before indexing completes?
2. **Error swallowed**: D-Bus proxy creation might fail silently
3. **Settings isolation**: prefs.js runs in separate process, logs not visible?

### Debug Needed

- Add console.log in `_setRagEnabled` to confirm it's called
- Add error handling around D-Bus proxy creation
- Test if signal fires at all when toggle switched

---

## Issue #2: Indexing Progress Stuck at 80% ⚠️

**Severity:** MEDIUM (Cosmetic)  
**Status:** CONFIRMED

### What Happens

Settings shows: "Processing document 19... (80%)"  
But indexing actually completes successfully (9 files indexed in 51.2s)

### Expected Behavior

Progress should reach 100% when indexing completes

### Actual Behavior

UI stuck at last progress signal received before completion

### Root Cause

Container output filtered by journald → Final progress updates (90%, 100%) never reach daemon

Daemon logs show:
```
2025-11-21 20:53:25 - Indexing completed successfully in 51.2s
```

But UI never received 100% progress signal before completion

### Fix Options

**Option A (Current - Line 542):** Settings explicitly sets 100% on RAGIndexingComplete  
**Status:** Should work, but maybe not applied in your build?

Let me check if this is in your code:

---

## Issue #3: Black Boxes in Responses (deepseek-r1) ⚠️

**Severity:** LOW (Model-specific)  
**Status:** NEEDS INVESTIGATION

### What Happens

User reports: "2+2" query shows black box characters in:
- Thinking/reasoning text
- Answer text (after "4")

### API Test Results

Direct API curl shows clean text:
```
Reasoning: "First, the user asked \"What is 2+2?\"..."
Content: "2 + 2 equals 4."
```

No special characters in API response!

### Likely Cause

**UI rendering issue**, not API issue. Possible causes:
1. deepseek-r1 outputs special Unicode (reasoning delimiters?)
2. Clutter.Text not handling certain Unicode ranges
3. Font missing glyphs for model's tokens

### Debug Needed

- Capture actual response text from UI
- Check if `reasoning_content` has special chars
- Test with different fonts
- Check if deepseek-r1 has known Unicode issues

---

## Issue #4: Strict Mode Working ✅

**Severity:** N/A  
**Status:** WORKING CORRECTLY

### Test Results

**Query:** "What is the capital of France?"  
**Expected:** "I don't know" (not in RAG documents)  
**Actual:** "I don't know" ✅

**Query:** "Who attended RHEL Lightspeed IBM meeting?"  
**Expected:** List of attendees from indexed PDF  
**Actual:** Full attendee list retrieved correctly ✅

```
Brian J King, Thomas Staudt, Brian Smith, Sarah Wright,
Joshua Miller, Nihar Panda, Stefan Weinhuber, etc.
```

### Conclusion

**RAG strict mode is working perfectly** once `SetRagEnabled` is called!

---

## Issue #5: Reasoning Not Working with RAG ⚠️

**Severity:** EXPECTED (Upstream limitation)  
**Status:** Ramalama proxy doesn't pass `reasoning_content` yet

### What Happens

When RAG enabled, API returns no `reasoning_content` field

### Root Cause

RAG proxy container strips reasoning (known limitation, see RAMALAMA_RFE.md Issue #8)

### Status

- ✅ Fix submitted to ramalama (`fix/rag-thinking` branch)
- ⏳ Waiting for upstream merge
- ⏳ Need to rebuild RAG proxy image with fix

---

## Working Configuration (Manual Enable)

```bash
# 1. Check RAG is indexed
python3 -c "
import dbus
bus = dbus.SessionBus()
proxy = bus.get_object('org.gnome.henzai', '/org/gnome/henzai')
iface = dbus.Interface(proxy, 'org.gnome.henzai')
status = iface.GetRAGStatus('/home/csoriano/Documents/rag', True)
print(status)
"

# Output: {"enabled": true, "indexed": true, "file_count": 9, ...}

# 2. Enable RAG (workaround)
python3 -c "
import dbus
bus = dbus.SessionBus()
proxy = bus.get_object('org.gnome.henzai', '/org/gnome/henzai')
iface = dbus.Interface(proxy, 'org.gnome.henzai')
result = iface.SetRagEnabled(True, 'strict')
print(result)
"

# Output: {"success": true, "message": "RAG enabled successfully (mode: strict)"}

# 3. Verify ramalama restarted with RAG
systemctl --user status ramalama | grep "rag-image"

# Should show: --rag-image localhost/ramalama/cuda-rag:augment --rag /path/to/db

# 4. Test query
curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-r1",
    "messages": [{"role": "user", "content": "Who attended the IBM meeting?"}],
    "stream": false
  }' | jq '.choices[0].message.content'
```

---

## Priority Fixes Needed

### Priority 1: Enable Toggle
Fix Settings → Enable RAG toggle to actually call `SetRagEnabled`

**Files:** `henzai-extension/prefs.js`

**Changes needed:**
- Add debug logging to `_setRagEnabled`
- Add error handling for D-Bus proxy creation
- Possibly defer signal handler to avoid timing issues

### Priority 2: Progress Display
Ensure 100% shown when indexing completes

**Files:** `henzai-extension/prefs.js` line 542

**Verify:** RAGIndexingComplete handler sets `statusRow.set_subtitle` to 100%

### Priority 3: Black Boxes
Investigate Unicode rendering issue with deepseek-r1

**Files:** `henzai-extension/ui/chatPanel.js`, possibly `scrollableTextInput.js`

**Debug:** Capture raw response text, check for special chars

---

## Test Matrix

| Scenario | Status | Notes |
|----------|--------|-------|
| **Index 9 PDFs** | ✅ Works | 51.2s, all files processed |
| **Progress UI** | ⚠️ Stuck 80% | Indexing completes, UI misleading |
| **Enable RAG toggle** | ❌ Broken | Doesn't call SetRagEnabled |
| **Manual SetRagEnabled** | ✅ Works | Ramalama restarts correctly |
| **Strict mode** | ✅ Works | "I don't know" for non-RAG queries |
| **RAG retrieval** | ✅ Works | Finds IBM meeting attendees |
| **Reasoning display** | ❌ Expected | Proxy strips reasoning (upstream) |
| **Black boxes (2+2)** | ⚠️ Needs debug | Only in UI, not API |

---

## Conclusion

**RAG implementation is solid** - all backend code works correctly!

**Issues are UX/UI-level:**
1. Settings toggle doesn't trigger D-Bus call (HIGH)
2. Progress display cosmetic issue (MEDIUM)
3. Unicode rendering with deepseek-r1 (LOW)

**Workaround exists** - manual `SetRagEnabled` call makes everything work.

**Next steps:**
1. Fix Settings toggle to call D-Bus properly
2. Test with fresh GNOME Shell session
3. Add better error handling/logging in Settings UI
4. Investigate deepseek-r1 Unicode issue separately

