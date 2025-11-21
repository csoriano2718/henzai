# Ramalama Patches - Submission Checklist

## Ready for Submission ✅

### Patch 2: RAG Reasoning Passthrough
- ✅ Branch: `fix/rag-framework-reasoning-passthrough`
- ✅ Fork: `csoriano2718/ramalama`
- ✅ Tested with Ramalama v0.14.0
- ✅ Commit message includes Assisted-by tag
- ✅ Patch file generated
- ✅ Documentation complete

**PR Creation**:
```bash
# Create draft PR from csoriano2718/ramalama:fix/rag-framework-reasoning-passthrough
# Target: containers/ramalama:main
# Mark as: Draft
```

### Patch 3: RAG Mode Enforcement
- ✅ Branch: `fix/rag-framework-mode-enforcement`
- ✅ Fork: `csoriano2718/ramalama`
- ✅ Tested with Ramalama v0.14.0
- ✅ Commit message includes Assisted-by tag
- ✅ Patch file generated
- ✅ Documentation complete

**PR Creation**:
```bash
# Create draft PR from csoriano2718/ramalama:fix/rag-framework-mode-enforcement
# Target: containers/ramalama:main
# Mark as: Draft
```

## PR Template

```markdown
## Summary
[Brief description of what the patch does]

## Problem
[What issue does this address?]

## Solution
[How does the patch fix it?]

## Testing
- Tested with Ramalama v0.14.0
- Model: deepseek-r1:14b
- Full end-to-end RAG + reasoning integration
- See: [link to test documentation]

## Container Dependencies
This patch requires rebuilding RAG container images (cuda-rag, rocm-rag, etc.) 
with the updated `/usr/bin/rag_framework` script.

## Compliance
Assisted-by: Cursor with Claude Sonnet 4.5
(Per Fedora AI Contribution Policy)
```

## Pre-Submission Checks

- [x] Both branches pushed to fork
- [x] Commits have Assisted-by tags
- [x] Documentation complete
- [x] Tests passing
- [x] Fedora AI policy compliance
- [x] Container dependencies documented
- [x] Patch 1 removed (unnecessary)

## Next Actions

1. Create draft PR for Patch 2
2. Create draft PR for Patch 3
3. Wait for maintainer feedback
4. Iterate if needed
5. Mark as ready for review when approved

## Notes

- Both PRs should be marked as **drafts** initially
- Patches can be submitted independently
- Patch 3 doesn't depend on Patch 2
- Both work with unmodified CUDA/ROCm containers
