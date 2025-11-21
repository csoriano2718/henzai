# Container Dependencies for Ramalama Patches

## Critical Issue Discovered

The Ramalama patches have **container dependencies** that must be documented:

### Patch 1: llama.cpp reasoning flags
**Changes:** `inference-spec/engines/llama.cpp.yaml`

**Container dependency:** The `quay.io/ramalama/cuda:latest` (or other inference runtime containers) must have the updated `llama.cpp.yaml` file at `/usr/share/ramalama/inference/llama.cpp.yaml`.

**Why:** The inference spec YAML is used **inside the container** that runs `llama-server`. Without the updated spec, the `--reasoning-format` and `--reasoning-budget` flags won't be added to the llama-server command, even if `--thinking true` is passed to ramalama.

**Solution:** Container images must be rebuilt OR users must manually update the spec file in running containers.

### Patch 2: RAG reasoning passthrough  
**Changes:** `container-images/scripts/rag_framework`

**Container dependency:** The RAG proxy containers (`quay.io/ramalama/cuda-rag`, `quay.io/ramalama/rocm-rag`, etc.) must have the updated `rag_framework` script at `/usr/bin/rag_framework`.

**Why:** The `rag_framework` script runs inside the RAG container and forwards requests to the model server. Without the `getattr()` fix, it will crash when encountering chunks without `reasoning_content`.

**Solution:** RAG container images must be rebuilt with the updated script.

### Patch 3: RAG mode enforcement
**Changes:** `container-images/scripts/rag_framework`

**Container dependency:** Same as Patch 2 - RAG proxy containers need the updated script.

**Why:** The mode enforcement logic is in the `rag_framework` script that runs inside the container.

**Solution:** Same RAG container rebuild as Patch 2.

## Implications for Upstream Submission

When submitting these patches upstream, we must:

1. **Update commit messages** to explicitly mention container rebuild requirements
2. **Update patch documentation** to include rebuild instructions
3. **Consider submitting container image updates** alongside code patches
4. **Add to TESTING.md** that testing requires container rebuilds

## Current Status

- ✅ Patch code committed to branches
- ❌ Container rebuild requirements NOT documented in commits
- ❌ Patch testing incomplete without container updates

## Action Items

1. Amend commit messages for all 3 patches to include container dependency notes
2. Update patch README to include rebuild instructions  
3. Create test scripts that verify container contents
4. Re-test all patches with properly updated containers

