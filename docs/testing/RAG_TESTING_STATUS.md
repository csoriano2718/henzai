# RAG Testing Status

**Last Updated:** 2025-11-20  
**Status:** ✅ **RAG E2E Testing Operational** (with limitations)

---

## Summary

The RAG E2E test suite has been successfully created and is now functional. Testing confirmed:

✅ **Fixed Issues:**
1. CUDA library version mismatch **resolved** after system reboot
2. RAG container (`quay.io/ramalama/cuda-rag:latest`) now starts correctly
3. Document indexing **works** (tested with 3 markdown files)
4. RAG database creation **works** 
5. GetRAGStatus D-Bus method **works** (returns JSON)

⚠️ **Known Limitations:**
1. **RAG+Reasoning Incompatibility** (documented as Issue #8 in `RAMALAMA_RFE.md`):
   - When reasoning models are used (e.g., deepseek-r1:14b), responses include long `<think>` sections
   - The model generates reasoning content but doesn't properly utilize RAG context
   - This is an **upstream issue** in Ramalama's RAG proxy implementation

2. **Docling file format restrictions**:
   - RAG container only supports specific formats: `.md`, `.pdf`, `.docx`, `.html`, etc.
   - Plain `.txt` files are **not supported** and cause indexing errors
   - Test suite now uses `.md` files exclusively

---

## Test Results (2025-11-20)

```
============================================================
RAG E2E TEST SUMMARY
============================================================
✅ PASS - Service Running
✅ PASS - RAG Indexing (3 markdown files, 6.4 seconds)
⚠️  PARTIAL - RAG Query Tests (blocked by RAG+Reasoning issue)
============================================================
```

### What Works

1. **Document Indexing:**
   - Successfully indexes markdown files
   - Creates RAG database at `~/.local/share/henzai/rag-db`
   - Returns proper JSON status via `GetRAGStatus`
   - Completes in ~6-7 seconds for 3 small documents

2. **LLM Server Integration:**
   - Ramalama service starts correctly
   - Model loads properly (deepseek-r1:14b)
   - Health endpoint responds
   - Queries execute successfully

3. **D-Bus API:**
   - `SetRAGConfig` - ✅ Works
   - `GetRAGStatus` - ✅ Works (returns JSON)
   - `SetRagEnabled` - ✅ Works
   - `SendMessage` - ✅ Works (with reasoning model caveats)
   - `DisableRAG` - ⏳ Needs testing after fixing query tests

### What Doesn't Work (Yet)

1. **RAG Query Accuracy:**
   - Queries return responses with long reasoning sections
   - Expected keywords often not found in responses
   - Model doesn't reliably use RAG context when reasoning is enabled
   - **Root cause:** Upstream RAG+Reasoning incompatibility

2. **Mode Testing:**
   - Cannot reliably test augment/strict/hybrid modes due to reasoning interference
   - Need a non-reasoning model (e.g., llama3.2) for proper mode validation

---

## Testing Methodology

### Test Environment
- **System:** Fedora Linux with NVIDIA CUDA 12.8.1
- **henzai-daemon:** Running from user space (`~/.local/bin/henzai-daemon`)
- **Ramalama:** v0.14.0 (dev version with RAG API improvements)
- **Model:** ollama://library/deepseek-r1:14b (reasoning model)

### Prerequisites
```bash
# 1. Ensure henzai-daemon is running
systemctl --user status henzai-daemon

# 2. Ensure ramalama service is running
systemctl --user status ramalama

# 3. Wait for model to load
curl http://127.0.0.1:8080/health  # Should return {"status":"ok"}
```

### Running Tests
```bash
cd /home/csoriano/henzAI
timeout 300 python3 tests/test-rag-e2e.py
```

---

## Current Blockers

### 1. ⚠️ **RAG+Reasoning Incompatibility** (Issue #8)
**Severity:** High  
**Impact:** Cannot reliably test RAG query accuracy with reasoning models  
**Workaround:** Test with non-reasoning models (e.g., llama3.2, qwen2.5)  
**Fix:** Requires upstream changes in Ramalama (documented in `RAMALAMA_RFE.md`)

---

## Fixed Issues (2025-11-20)

### ✅ **CUDA Library Version Mismatch**
**Problem:** Container was looking for `libEGL_nvidia.so.580.95.05` but system had `580.105.08`  
**Fix:** System reboot after NVIDIA driver update  
**Status:** Resolved

### ✅ **File Format Not Supported**
**Problem:** RAG container rejected `.txt` files  
**Fix:** Changed test to use `.md` files  
**Status:** Resolved

### ✅ **GetRAGStatus JSON Parsing**
**Problem:** Test was expecting string format, but API returns JSON  
**Fix:** Updated `get_rag_status()` to parse JSON properly  
**Status:** Resolved

### ✅ **Ramalama Service Path**
**Problem:** Service was using `/usr/bin/ramalama` (deleted) instead of `~/.local/bin/ramalama`  
**Fix:** Updated `~/.config/systemd/user/ramalama.service` and reloaded systemd  
**Status:** Resolved

---

## Recommendations

### Short-term (For Testing)
1. **Use a non-reasoning model** for RAG validation:
   ```bash
   # Switch to llama3.2 or qwen2.5 for testing
   systemctl --user stop ramalama
   # Edit ~/.config/systemd/user/ramalama.service to use llama3.2
   systemctl --user daemon-reload
   systemctl --user start ramalama
   ```

2. **Update test expectations** to account for reasoning tokens in responses

3. **Test RAG modes individually** with manual verification instead of automated checks

### Long-term (For Production)
1. **Fix RAG+Reasoning upstream** (documented in `RAMALAMA_RFE.md` Issue #8)
2. **Add RAG mode detection** to henzai daemon to auto-disable reasoning when RAG is enabled
3. **Improve test robustness** by stripping reasoning tokens before keyword matching

---

## Test Coverage

| Test Area | Status | Notes |
|-----------|--------|-------|
| Service Running | ✅ Pass | henzai-daemon operational |
| RAG Indexing | ✅ Pass | 3 markdown files indexed in 6.4s |
| RAG Status Check | ✅ Pass | JSON parsing works |
| RAG Augment Mode | ⚠️ Partial | Queries work but reasoning interferes |
| RAG Strict Mode | ⚠️ Partial | Queries work but reasoning interferes |
| RAG Hybrid Mode | ⚠️ Partial | Queries work but reasoning interferes |
| Document Relevance | ⏳ Blocked | Needs non-reasoning model |
| RAG Disable | ⏳ Needs Testing | Not yet validated |

---

## Next Steps

1. **Switch to non-reasoning model** for comprehensive RAG testing
2. **Complete test suite validation** with all modes
3. **Document mode-specific behavior** for each RAG mode
4. **Create issue in Ramalama repo** for RAG+Reasoning fix
5. **Add warning in henzai UI** when reasoning+RAG conflict detected

---

**Contributors:** AI Assistant, csoriano  
**Related Documents:**
- `docs/reference/RAMALAMA_RFE.md` - Upstream issues and RFEs
- `docs/reference/DBUS_API.md` - D-Bus API specification
- `tests/test-rag-e2e.py` - E2E test suite
