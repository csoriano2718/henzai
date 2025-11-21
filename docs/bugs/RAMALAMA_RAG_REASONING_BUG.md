# Ramalama Bug: RAG+Reasoning Incompatibility

**Date Found:** 2025-11-21  
**Reporter:** AI Assistant / csoriano  
**Severity:** High  
**Status:** Root cause identified, fix proposed

---

## Summary

The `--thinking` parameter is **not passed through** when RAG is enabled in Ramalama, causing reasoning models to not work properly with RAG.

---

## Root Cause

**File:** `/usr/local/lib/python3.13/site-packages/ramalama/command/context.py`

### The Problem

When RAG is enabled (`serve --rag` or `run --rag`), Ramalama uses `RamalamaRagArgsContext` instead of `RamalamaArgsContext`:

```python
# Lines 76-91: RamalamaRagArgsContext
class RamalamaRagArgsContext:
    def __init__(self) -> None:
        self.debug: bool | None = None
        self.port: str | None = None
        self.model_host: str | None = None
        self.model_port: str | None = None
        # ❌ MISSING: self.thinking
```

Compare to the regular context:

```python
# Lines 10-30: RamalamaArgsContext (used without RAG)
class RamalamaArgsContext:
    def __init__(self) -> None:
        self.cache_reuse: Optional[int] = None
        self.container: Optional[bool] = None
        self.ctx_size: Optional[int] = None
        # ... many other fields ...
        self.thinking: Optional[bool] = None  # ✅ Present here!
```

### Context Selection Logic

```python
# Lines 157-162: How context is chosen
if cli_args.subcommand == "rag":
    args = RamalamaRagGenArgsContext.from_argparse(cli_args)
elif cli_args.subcommand in ("run --rag", "serve --rag"):
    args = RamalamaRagArgsContext.from_argparse(cli_args)  # ❌ Uses RAG context (no thinking!)
else:
    args = RamalamaArgsContext.from_argparse(cli_args)    # ✅ Uses full context (has thinking!)
```

---

## Impact

### What Breaks

1. **Command:** `ramalama serve --rag /path/to/db --thinking=true ollama://library/deepseek-r1:14b`
   - **Expected:** RAG + reasoning tokens
   - **Actual:** RAG works, but `--thinking` is silently ignored

2. **API Response:**
   - **Expected:** Returns both `content` and `reasoning_content` fields
   - **Actual:** Only returns `content` field (reasoning stripped)

3. **User Experience:**
   - Reasoning models produce generic answers instead of detailed reasoning
   - No `<think>` sections in responses
   - RAG context not used effectively by reasoning process

### Test Results

| Configuration | Works? | Details |
|---------------|--------|---------|
| `serve --thinking=true` (no RAG) | ✅ Yes | Full reasoning tokens |
| `serve --rag /db` (no reasoning) | ✅ Yes | RAG works normally |
| `serve --rag /db --thinking=true` | ❌ **NO** | `--thinking` ignored! |

---

## The Fix

### Option 1: Add `thinking` to `RamalamaRagArgsContext` (Recommended)

**File:** `ramalama/command/context.py`

```python
class RamalamaRagArgsContext:
    def __init__(self) -> None:
        self.debug: bool | None = None
        self.port: str | None = None
        self.model_host: str | None = None
        self.model_port: str | None = None
        self.thinking: bool | None = None  # ✅ ADD THIS LINE

    @staticmethod
    def from_argparse(args: argparse.Namespace) -> "RamalamaRagArgsContext":
        ctx = RamalamaRagArgsContext()
        ctx.debug = getattr(args, "debug", None)
        ctx.port = getattr(args, "port", None)
        ctx.model_host = getattr(args, "model_host", None)
        ctx.model_port = getattr(args, "model_port", None)
        ctx.thinking = getattr(args, "thinking", None)  # ✅ ADD THIS LINE
        return ctx
```

### Option 2: Use Full `RamalamaArgsContext` for RAG

Change line 160 to use the full context:

```python
elif cli_args.subcommand in ("run --rag", "serve --rag"):
    args = RamalamaArgsContext.from_argparse(cli_args)  # Use full context
```

**Pros:** All parameters available  
**Cons:** Might expose unneeded parameters

---

## Testing the Fix

### Before Fix

```bash
# Start with reasoning + RAG
ramalama serve --rag /path/to/db --thinking=true ollama://library/deepseek-r1:14b

# Query
curl http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"library/deepseek-r1","messages":[{"role":"user","content":"test"}]}'

# Result: No "reasoning_content" field ❌
```

### After Fix

```bash
# Same command
ramalama serve --rag /path/to/db --thinking=true ollama://library/deepseek-r1:14b

# Query
curl http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"library/deepseek-r1","messages":[{"role":"user","content":"test"}]}'

# Result: Has "reasoning_content" field ✅
```

---

## Verification

### API Response Format

**With `--thinking=true` (reasoning enabled):**

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "The answer is...",
      "reasoning_content": "Let me think through this..."
    }
  }]
}
```

**Without `--thinking` or when it's ignored:**

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "The answer is..."
      // ❌ No reasoning_content field!
    }
  }]
}
```

---

## Upstream Issue

This bug should be reported to the Ramalama project:
- **Repository:** https://github.com/containers/ramalama
- **Title:** "RAG: --thinking parameter not passed through RamalamaRagArgsContext"
- **Labels:** bug, rag, reasoning

### Issue Description Template

```markdown
## Bug Description

The `--thinking` parameter is not passed through when RAG is enabled, causing reasoning models to fail with RAG.

## Root Cause

`RamalamaRagArgsContext` (used for `serve --rag`) does not include the `thinking` field that exists in `RamalamaArgsContext`.

**File:** `ramalama/command/context.py`  
**Lines:** 76-91

## Expected Behavior

```bash
ramalama serve --rag /path/to/db --thinking=true ollama://library/deepseek-r1:14b
```

Should enable both RAG and reasoning tokens.

## Actual Behavior

The `--thinking` parameter is silently ignored, and the API response lacks the `reasoning_content` field.

## Proposed Fix

Add `thinking` field to `RamalamaRagArgsContext`:

[Include fix from above]

## Impact

- Reasoning models (deepseek-r1, qwq, etc.) cannot be used effectively with RAG
- Users expect RAG+Reasoning to work together
- No error message - fails silently
```

---

## Workaround (Until Fixed)

**For henzai users:**

1. **Option A: Use non-reasoning models with RAG**
   - Use `llama3.2`, `qwen2.5`, or other standard models
   - These work perfectly with RAG

2. **Option B: Disable RAG when using reasoning models**
   - Use deepseek-r1 without RAG
   - Get detailed reasoning but no document grounding

3. **Option C: Manually patch Ramalama**
   - Apply the fix above to your local Ramalama installation
   - Restart the service

---

## Related Files

- **henzai:** `docs/reference/RAMALAMA_RFE.md` (Issue #8)
- **henzai:** `docs/testing/RAG_TESTING_STATUS.md`
- **Ramalama:** `ramalama/command/context.py` (bug location)

---

**Next Steps:**
1. ✅ Root cause identified
2. ✅ Fix proposed
3. ⏳ Create upstream issue in Ramalama repo
4. ⏳ Submit pull request with fix
5. ⏳ Wait for merge and release

