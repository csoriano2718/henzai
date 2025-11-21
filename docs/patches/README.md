# Ramalama Upstream Patches

This directory contains patches ready for submission to the Ramalama upstream project.

## Patches Overview

We have **2 patches** ready for submission:

### Patch 2: RAG Reasoning Passthrough
**Branch**: `fix/rag-framework-reasoning-passthrough`  
**File**: `container-images/scripts/rag_framework`

**Problem**: Direct access to `delta.reasoning_content` causes AttributeError when the OpenAI client's ChoiceDelta object doesn't have this attribute (happens on metadata/initial chunks).

**Solution**: Use `getattr(delta, 'reasoning_content', None)` for safe access.

**Impact**: Enables reasoning models (deepseek-r1, qwq, etc.) to work with RAG without crashes.

### Patch 3: RAG Mode Enforcement
**Branch**: `fix/rag-framework-mode-enforcement`  
**File**: `container-images/scripts/rag_framework`

**Problem**: RAG had weak enforcement - models would answer out-of-context questions even in "strict" mode.

**Solution**: Implement `RAG_MODE` environment variable that modifies system prompts:
- `strict`: Refuses out-of-context queries with "I don't know"
- `hybrid`: Prefers documents, indicates when using general knowledge
- `augment`: Uses both documents and general knowledge freely

**Usage**:
```bash
ramalama serve --env RAG_MODE=strict --rag /path/to/db model
```

## Why No Patch 1?

Originally we had "Patch 1: llama.cpp reasoning flags" but discovered it's unnecessary:
- llama-server already has correct defaults: `--reasoning-format auto` and `--reasoning-budget -1`
- Reasoning works perfectly without explicit flags
- The patch just made explicit what was already the default
- Adding complexity with no functional benefit

## Testing

All patches tested with:
- Ramalama v0.14.0 (latest upstream)
- deepseek-r1:14b reasoning model
- Full end-to-end RAG + reasoning integration

See `FINAL_STATUS.md` for detailed test results.

## Submission Process

1. Create **draft PRs** on Ramalama repository
2. Reference container rebuild requirements
3. Include test results and documentation
4. Mark as "Assisted-by: Cursor with Claude Sonnet 4.5" per Fedora AI policy

## Files

- `ramalama-rag-reasoning-passthrough.patch` - Patch 2
- `ramalama-rag-mode-enforcement.patch` - Patch 3
- `FINAL_STATUS.md` - Complete testing summary
- `CONTAINER_DEPENDENCIES.md` - Container rebuild info
- `TEST_REPORT.md` - Detailed test procedures
