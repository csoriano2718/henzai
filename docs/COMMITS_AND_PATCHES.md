# Commits and Upstream Patches Summary

## henzai Repository

### Branch: `feature/rag-modes`

#### Commit 1: Test Suite and RAG Fixes
**Hash:** `f535338`  
**Message:** "Add comprehensive test suite and fix RAG mode enforcement"

**Changes:**
- Added `test-rag-reasoning.py` for RAG+reasoning integration testing
- Added `run-tests.sh` test runner script
- Added GitHub Actions CI workflow (Fedora-based)
- Created comprehensive test documentation
- Fixed `install.sh` to restart daemon automatically
- Fixed gsettings/daemon/ramalama synchronization on startup
- Updated AGENT_SHORTCUTS.md with test commands

**Files:**
- `.github/workflows/tests.yml` (new)
- `docs/TESTING.md` (new)
- `tests/run-tests.sh` (new)
- `tests/test-rag-reasoning.py` (new)
- `tests/README.md` (modified)
- `install.sh` (modified)
- `henzai-daemon/henzai/main.py` (modified)
- `henzai-daemon/henzai/dbus_service.py` (modified)
- `AGENT_SHORTCUTS.md` (modified)

---

#### Commit 2: Upstream Patches
**Hash:** `b41be80`  
**Message:** "docs: Add Ramalama upstream patches for RAG+reasoning fixes"

**Changes:**
- Created three patches for Ramalama upstream submission
- Documented patch rationale, testing, and submission process
- Ready for PR creation to containers/ramalama

**Files:**
- `docs/patches/README.md` (new)
- `docs/patches/ramalama-fix-llama-cpp-reasoning.patch` (new)
- `docs/patches/ramalama-rag-reasoning-passthrough.patch` (new)
- `docs/patches/ramalama-rag-mode-enforcement.patch` (new)

---

## Ramalama Repository (Patches for Upstream)

### Patch 1: llama.cpp Reasoning Support
**File:** `docs/patches/ramalama-fix-llama-cpp-reasoning.patch`  
**Branch:** `fix/llama-cpp-reasoning-default`  
**Target:** `inference-spec/engines/llama.cpp.yaml`

**Summary:**
Enable reasoning by default with auto-detection in llama.cpp inference spec.

**Key Changes:**
```yaml
# Before (reasoning disabled by default)
- name: "--reasoning-budget"
  value: "0"
  if: "{{ not args.thinking }}"

# After (reasoning enabled with auto-detection)
- name: "--reasoning-format"
  value: "auto"
- name: "--reasoning-budget"
  value: "-1"
```

**Impact:**
- Reasoning models work out of the box
- No manual `--thinking` flag required
- Backward compatible with non-reasoning models

---

### Patch 2: RAG Reasoning Passthrough
**File:** `docs/patches/ramalama-rag-reasoning-passthrough.patch`  
**Branch:** `fix/rag-framework-reasoning-passthrough`  
**Target:** `container-images/scripts/rag_framework`

**Summary:**
Pass through `reasoning_content` field in RAG proxy streaming responses.

**Key Changes:**
```python
# Add reasoning_content to Delta model
class Delta(BaseModel):
    role: str | None = None
    content: str | None = None
    reasoning_content: str | None = None  # NEW

# Extract and forward reasoning content
async for chunk in response:
    if chunk.choices and chunk.choices[0].delta:
        delta = chunk.choices[0].delta
        content = delta.content
        reasoning_content = delta.reasoning_content  # NEW
        
        stream_chunk = ChatCompletionStreamResponse(
            choices=[StreamChoice(
                index=0,
                delta=Delta(
                    content=content,
                    reasoning_content=reasoning_content  # NEW
                ),
                finish_reason=None
            )]
        )
```

**Impact:**
- Reasoning models work with RAG enabled
- UI displays model's thought process
- Fixes RAG proxy stripping reasoning content

---

### Patch 3: RAG Mode Enforcement
**File:** `docs/patches/ramalama-rag-mode-enforcement.patch`  
**Branch:** `fix/rag-framework-mode-enforcement`  
**Target:** `container-images/scripts/rag_framework`

**Summary:**
Implement `RAG_MODE` environment variable for behavior control (strict/hybrid/augment).

**Key Changes:**
```python
# Read RAG_MODE environment variable
rag_mode = os.getenv("RAG_MODE", "strict").lower()

# Generate different prompts based on mode
if rag_mode == "strict":
    system_prompt = """
    You are a strict document-based assistant.
    You MUST ONLY answer from the provided context.
    If answer is NOT in context, respond: "I don't know."
    Do NOT use general knowledge.
    """
elif rag_mode == "hybrid":
    system_prompt = """
    Prefer documents, fall back to general knowledge with indication.
    """
else:  # augment (default)
    system_prompt = """
    Use both documents and general knowledge freely.
    """
```

**Usage:**
```bash
# Strict mode
ramalama serve --env RAG_MODE=strict --rag /path/to/db model

# Hybrid mode
ramalama serve --env RAG_MODE=hybrid --rag /path/to/db model

# Augment mode (default)
ramalama serve --env RAG_MODE=augment --rag /path/to/db model
```

**Impact:**
- Applications control RAG behavior via environment variable
- Strict mode properly enforces document-only responses
- No code modification required for mode changes

---

## Container Image Updates Required

The RAG framework patches (2 and 3) need to be applied to **all RAG-enabled container images**:

### Affected Images
- `quay.io/ramalama/cuda-rag:*` (NVIDIA CUDA)
- `quay.io/ramalama/rocm-rag:*` (AMD ROCm)
- Any custom RAG container variants

### Update Process
1. Apply patches to container build source
2. Rebuild images with updated `rag_framework` script
3. Tag and push to registries
4. Update documentation to mention RAG_MODE support

---

## Next Steps

### For henzai

- [x] Commit changes to henzai repo
- [x] Create patches for Ramalama
- [x] Document patches and rationale
- [x] Push to feature/rag-modes branch
- [ ] Create PR to merge feature/rag-modes → main
- [ ] Tag release after merge

### For Ramalama Upstream

- [ ] Create GitHub account/fork for Ramalama (if needed)
- [ ] Create three PRs to containers/ramalama:
  1. PR for llama.cpp reasoning support
  2. PR for RAG reasoning passthrough
  3. PR for RAG mode enforcement
- [ ] Link PRs in henzai issues for tracking
- [ ] Monitor PR reviews and address feedback
- [ ] Update henzai after patches are merged upstream

### For Container Maintainers

- [ ] Notify Ramalama container maintainers about patches
- [ ] Request rebuild of RAG containers with updated rag_framework
- [ ] Verify updated containers work with henzai
- [ ] Update henzai documentation to reference official images

---

## Testing Summary

All patches have been tested with:
- ✅ deepseek-r1:14b (reasoning model)
- ✅ llama3.2:3b (non-reasoning model)
- ✅ RAG enabled (all three modes)
- ✅ RAG disabled
- ✅ Streaming responses
- ✅ Non-streaming responses

Test results:
- All combinations work correctly
- No regressions detected
- Backward compatible with existing setups

---

## Files Changed Summary

### henzai Repository
```
Changes:
- 16 files modified/created
- +1738 lines added
- -45 lines removed

Key files:
- .github/workflows/tests.yml (new CI)
- tests/test-rag-reasoning.py (new test)
- tests/run-tests.sh (new runner)
- docs/patches/*.patch (upstream patches)
- install.sh (auto-restart daemon)
```

### Ramalama (Patches)
```
Patch 1 (llama.cpp):
- 1 file changed
- +5 lines added
- -3 lines removed

Patch 2 (RAG reasoning):
- 1 file changed
- +6 lines added
- -3 lines removed

Patch 3 (RAG modes):
- 1 file changed
- +60 lines added
- -12 lines removed
```

---

## Maintainer Contact

**henzai maintainer:** csoriano  
**Ramalama project:** https://github.com/containers/ramalama  
**Issue tracking:** henzai GitHub issues

For questions about patches or integration, see `docs/patches/README.md`.

