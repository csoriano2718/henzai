# Critical Finding: llama.cpp Version Mismatch

## Problem

Even with Patch 1 applied (adding `--reasoning-format` and `--reasoning-budget` flags to the YAML spec), reasoning doesn't work because:

**The llama-server binary in `quay.io/ramalama/cuda:latest` is too old!**

## Evidence

1. ✅ Flags ARE being passed: `--reasoning-format auto --reasoning-budget -1`
2. ❌ llama-server logs show: `srv init: thinking = 0`
3. ❌ No `reasoning_content` returned from model

## Root Cause

The `--reasoning-format` and `--reasoning-budget` flags were added to llama.cpp recently (for deepseek-r1 support). The llama-server binary in the container predates these flags, so it:
- Ignores the unknown flags (doesn't error)
- Sets `thinking = 0` (default behavior)
- Never generates reasoning content

## Solution

The CUDA container (and other inference containers) must be rebuilt with a **newer version of llama.cpp** that supports:
- `--reasoning-format` flag
- `--reasoning-budget` flag  
- Reasoning models like deepseek-r1

## Implications for Upstream Submission

**Patch 1 CANNOT be submitted alone!**

It requires:
1. Updating llama.cpp in the containers to a version that supports reasoning
2. OR documenting minimum llama.cpp version requirements
3. OR adding version detection and graceful degradation

## Testing Status

- ✅ Patch 1: YAML spec changes are correct
- ✅ Patch 2: RAG proxy passthrough works (getattr)
- ✅ Patch 3: RAG mode enforcement works (hybrid mode behavior confirmed)
- ❌ **Integration test BLOCKED**: Container has old llama.cpp binary

## Next Steps

1. Check when reasoning support was added to llama.cpp upstream
2. Rebuild CUDA container with latest llama.cpp
3. Re-test all patches with updated container
4. Document container rebuild requirements in patch submission

