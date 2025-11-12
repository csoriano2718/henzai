# henzai TODO

## Pending External Dependencies

### Ramalama --reasoning-budget Support
**Status**: Waiting for upstream  
**GitHub Issue**: https://github.com/containers/ramalama/issues/XXX (file this!)  
**Priority**: Medium

**Problem**:
- The `--thinking 0` flag in Ramalama doesn't fully prevent DeepSeek-R1 from generating reasoning tokens
- This is a known llama.cpp limitation (issues #13160, #13189, #15401)
- llama.cpp added `--reasoning-budget 0` flag to fix this, but Ramalama doesn't expose it yet

**Current Workaround**:
- Reasoning toggle is disabled in settings UI (`henzai-extension/prefs.js`)
- Reasoning is always enabled for reasoning-capable models (DeepSeek-R1, etc.)
- Simple and straightforward - no complex client-side filtering needed

**Action Items**:
1. [ ] File RFE at https://github.com/containers/ramalama/issues/new
2. [ ] Update issue number in code (search for `issues/XXX`)
3. [ ] Monitor issue for Ramalama release with `--reasoning-budget` support
4. [ ] Once released, enable reasoning toggle:
   - Remove `sensitive: false` from `henzai-extension/prefs.js`
   - Implement proper `SetReasoningEnabled()` in daemon to use `--reasoning-budget`
   - Update subtitle to describe what the toggle does
   - Remove TODO comments

**Files to Update**:
- `henzai-extension/prefs.js` (lines 108-121)
- `henzai-daemon/henzai/dbus_service.py` (lines 434-464)
- `henzai-daemon/henzai/llm.py` (lines 598-607)

---

## Future Features

(Add new features here as they come up)

