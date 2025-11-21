# Ramalama Upstream Patches

This directory contains patches for upstream Ramalama that were developed as part of henzai's RAG+reasoning integration.

## Patches

### 1. `ramalama-fix-llama-cpp-reasoning.patch`
**Status:** Ready for upstream PR  
**Branch:** `fix/llama-cpp-reasoning-default`  
**Target:** Ramalama main branch

**Summary:**
Add `--reasoning-format` flag support for proper reasoning when `--thinking` is enabled.

**Changes:**
- Add `--reasoning-format auto` when `args.thinking` is true
- Add `--reasoning-budget -1` when `args.thinking` is true
- Keep `--reasoning-budget 0` when `args.thinking` is false (existing behavior)

**Impact:**
- Reasoning models work correctly when `--thinking` flag is used
- **No change to default behavior** - reasoning remains disabled unless `--thinking` is passed
- Preserves Ramalama's ability to disable reasoning
- Backward compatible

**Rationale:**
Previously, even when `--thinking` was enabled, the `--reasoning-budget` was always 0 (disabled).
This patch adds the missing `--reasoning-format auto` flag and sets `--reasoning-budget -1`
when `--thinking` is requested, allowing reasoning models to actually generate reasoning content.

**Testing:**
- Tested with deepseek-r1:14b + `--thinking` (reasoning works)
- Tested with llama3.2:3b without `--thinking` (no reasoning, as expected)
- Both models work correctly

---

### 2. `ramalama-rag-reasoning-passthrough.patch`
**Status:** Ready for upstream PR  
**Branch:** `fix/rag-framework-reasoning-passthrough`  
**Target:** Ramalama container-images

**Summary:**
Pass through `reasoning_content` field in RAG proxy streaming responses.

**Changes:**
- Add `reasoning_content` to `Delta` model in rag_framework
- Extract and forward `reasoning_content` from upstream LLM
- Preserve reasoning content in streaming chunks

**Impact:**
- Reasoning models work correctly with RAG enabled
- UI can display model's thought process even when RAG is active
- Fixes regression where RAG proxy was stripping reasoning content

**Testing:**
- Tested with deepseek-r1:14b + RAG in strict/augment modes
- Verified reasoning content appears in UI
- Confirmed no impact on non-reasoning models

---

### 3. `ramalama-rag-mode-enforcement.patch`
**Status:** Ready for upstream PR  
**Branch:** `fix/rag-framework-mode-enforcement`  
**Target:** Ramalama container-images

**Summary:**
Implement `RAG_MODE` environment variable for behavior control.

**Changes:**
- Read `RAG_MODE` environment variable (strict/hybrid/augment)
- Generate different system prompts based on mode
- **strict**: Documents only, refuses out-of-context queries
- **hybrid**: Prefers documents, falls back to general knowledge
- **augment** (default): Freely uses both documents and general knowledge

**Impact:**
- Applications can control RAG behavior without modifying rag_framework
- Strict mode properly enforces document-only responses
- Addresses common user complaint: "RAG still answers general knowledge"

**Usage:**
```bash
# Strict mode - documents only
ramalama serve --env RAG_MODE=strict --rag /path/to/db model

# Hybrid mode - prefer documents
ramalama serve --env RAG_MODE=hybrid --rag /path/to/db model

# Augment mode - use both (default)
ramalama serve --env RAG_MODE=augment --rag /path/to/db model
```

**Testing:**
- Tested all three modes with various queries
- Strict mode correctly refuses out-of-context queries
- Augment mode answers both document and general knowledge
- Hybrid mode shows preference for documents

---

## How to Apply Patches

### For Ramalama Maintainers

```bash
# Clone ramalama
git clone https://github.com/containers/ramalama.git
cd ramalama

# Apply llama.cpp reasoning fix
git checkout -b fix/llama-cpp-reasoning-default
git am < /path/to/ramalama-fix-llama-cpp-reasoning.patch

# Apply RAG reasoning passthrough
git checkout main
git checkout -b fix/rag-framework-reasoning-passthrough
git am < /path/to/ramalama-rag-reasoning-passthrough.patch

# Apply RAG mode enforcement
git checkout main
git checkout -b fix/rag-framework-mode-enforcement
git am < /path/to/ramalama-rag-mode-enforcement.patch
```

### For Container Image Maintainers

The RAG framework changes (patches 2 and 3) need to be applied to the container images:

**Affected containers:**
- `quay.io/ramalama/cuda-rag:*` (CUDA/NVIDIA)
- `quay.io/ramalama/rocm-rag:*` (AMD ROCm)
- Any other RAG-enabled container variants

**Files to update:**
- `container-images/scripts/rag_framework`

**Steps:**
1. Apply patches 2 and 3 to your container build source
2. Rebuild container images
3. Tag and push to registries

---

## Submission Checklist

### Before Creating PRs

- [x] Patches tested locally with henzai
- [x] Patches apply cleanly to Ramalama main
- [x] Commit messages follow Ramalama conventions
- [x] Changes are backward compatible
- [ ] Create GitHub PRs for each patch
- [ ] Add to Ramalama issue tracker if needed

### PR Descriptions

Each PR should include:
- Problem statement (what doesn't work currently)
- Solution approach
- Testing methodology
- Example usage
- Screenshots/logs (if applicable)

---

## Rationale

### Why These Changes Matter

1. **Reasoning Support**: Reasoning models are becoming mainstream (deepseek-r1, qwq). Ramalama should support them out of the box without requiring manual configuration.

2. **RAG + Reasoning**: Users expect both features to work together. Currently, enabling RAG breaks reasoning models, which is unexpected behavior.

3. **RAG Mode Control**: Different use cases need different RAG behaviors:
   - **Strict**: Legal/medical apps need document-only responses
   - **Augment**: General assistants benefit from both documents and knowledge
   - **Hybrid**: Research tools prefer documents but allow fallback

### Design Decisions

- **Environment variables over config files**: Easier to set per-service without modifying files
- **Auto-detection over explicit flags**: Better DX, harder to misconfigure
- **Strong prompt language for strict mode**: LLMs need explicit instructions to refuse queries
- **Backward compatibility**: All changes default to current behavior

---

## Related Issues

- henzai issue: RAG + reasoning not working together
- henzai issue: Strict RAG mode not actually strict
- Upstream Ramalama: (to be created)

---

## Contact

For questions about these patches:
- henzai repo: https://github.com/csoriano2718/henzai
- Ramalama repo: https://github.com/containers/ramalama

Patches maintained by: henzai project contributors

