# Ramalama Issues and RFEs

**Created**: 2025-11-14  
**Last Updated**: 2025-11-17  
**Ramalama Version**: 0.14.0 (dev)  
**Context**: henzai as a ramalama wrapper

---

## About This Document

This document tracks issues and RFEs (Request For Enhancement) discovered while integrating ramalama into henzai. As henzai is designed to be a **wrapper for ramalama features** rather than reimplementing them, we often discover limitations or bugs in ramalama itself.

**This list will grow over time** as we explore more ramalama features and edge cases. Each issue is documented with:
- Problem description
- Impact on users
- Workarounds (if any)
- Suggested fixes for ramalama team

---

## Summary

Current known issues:

1. **RFE #1163**: `ramalama serve --rag` doesn't properly expose RAG-augmented API (✅ Fixed in v0.14.0)
2. **Bug (unreported)**: Port parsing error when using `--rag` flag (⚠️ Cosmetic - works anyway)
3. **RFE (unreported)**: No incremental RAG updates (must delete entire database to re-index)
4. **RFE (unreported)**: No RAG retrieval metadata in API responses
5. **🚨 CRITICAL**: RAG mode disables general knowledge (becomes document-only chatbot)
6. **RFE #6a (unreported)**: Missing `whisper` in RAG container (audio/video transcription fails)
7. **RFE #6b (unreported)**: No graceful degradation for missing optional dependencies
8. **🚨 CRITICAL**: RAG mode disables reasoning/thinking for reasoning-capable models

---

## Issue 1: RAG with serve (RFE)

**Issue**: https://github.com/containers/ramalama/issues/1163  
**Title**: "rag: ramalama serve --rag doesn't take into account of RAG"  
**Status**: Open (since April 2025)  
**Being worked on**: Yes

### Current Behavior

When running `ramalama serve --rag <rag-db>`, the API exposed on the port is the **raw llama-server**, not the RAG-augmented proxy.

```bash
# This command succeeds but exposes wrong endpoint
$ ramalama serve --rag ~/.local/share/henzai/rag-db ollama://library/llama3.2:1b
```

**What happens:**
- Model server starts on specified port (e.g., 8080)
- RAG proxy container (`rag_framework`) is NOT exposed to clients
- Clients connect directly to llama-server (no RAG augmentation)

**Expected behavior:**
- RAG proxy should be on the specified port (8080)
- RAG proxy internally connects to model server
- Clients get RAG-augmented responses

### Workarounds

**Option A: Use `ramalama run --rag` (interactive mode)**
```bash
$ ramalama run --rag ~/.local/share/henzai/rag-db ollama://library/llama3.2:1b
```
- ✅ Works correctly (RAG-augmented)
- ❌ Interactive mode only (not suitable for daemon)
- ❌ Requires specifying prompt in command

**Option B: Client-side RAG (henzai's approach)**
- Henzai implements RAG retrieval in Python daemon
- Query qdrant database directly
- Augment prompt before sending to `ramalama serve` (without `--rag`)
- ✅ Works with persistent server
- ❌ Reimplements functionality that should be in ramalama

### Status from ramalama team

Last update (Aug 2025):
> "Still working on this! Theres a couple of ways we can go about doing this. The llamastack way isnt what I had hoped in terms of functionality so its still on going work. There is a pr out that is a poc for model swap that uses a proxy. We can utilize a transparent proxy to initiate rag server here as well"

---

## Issue 2: Port Parsing Bug (Unreported)

**Status**: Not yet reported to ramalama  
**Ramalama Version**: 0.14.0 (and main branch as of 2025-11-14)

### Bug Description

When using `--rag` flag with a custom `--port`, ramalama crashes with:

```
Error: parsing container port: invalid port number: strconv.Atoi: parsing "None": invalid syntax
```

### Reproduction

```bash
# This fails with port parsing error
$ ramalama serve --port 9999 --rag ~/.local/share/henzai/rag-db ollama://library/llama3.2:1b

# This also fails
$ ramalama run --port 9000 --rag ~/.local/share/henzai/rag-db ollama://library/llama3.2:1b
```

### Root Cause

File: `ramalama/cli.py`, function `_rag_args()` (lines 1119-1120 in v0.14.0)

```python
def _rag_args(args):
    # ... setup code ...
    
    # If --port was specified, use it for the RAG proxy, and
    # select a random port for the model
    args.port = None  # ❌ BUG: Sets port to None
    rag_args.model_port = args.port = compute_serving_port(args, exclude=[rag_args.port])
    # Later, args.port (None) is used in port mapping string → "parsing 'None'" error
```

**The problem:**
1. User specifies `--port 9999`
2. `_rag_args()` sets `args.port = None`
3. Somewhere in port mapping, `None` is converted to string `"None"`
4. Port parsing fails: `strconv.Atoi: parsing "None": invalid syntax`

### Impact

- ✅ `ramalama rag` (indexing) works fine
- ⚠️ `ramalama serve --rag --port 8080` **shows error but works** (ports 8080/8081)
- ❌ `ramalama run --rag --port` fails with custom port
- ✅ `ramalama run --rag` (no port, interactive) works

**UPDATE 2025-11-17**: Testing shows the error is cosmetic - the service starts correctly with ports 8080 (RAG proxy) and 8081 (LLM). The error can be ignored. **We now use `--port 8080` in henzai** to ensure consistent ports.

### Suggested Fix

The intent seems to be:
1. RAG proxy uses the user-specified port (e.g., 9999)
2. Model server uses a random available port (e.g., 8086)
3. RAG proxy forwards to model server internally

The fix should be:
```python
def _rag_args(args):
    # ... setup code ...
    
    # Save user's requested port for RAG proxy
    rag_port = args.port
    
    # Compute a different port for the model server (avoiding rag_port)
    args.port = None  # Reset before computing
    model_port = compute_serving_port(args, exclude=[rag_port])
    
    # Set up correctly
    rag_args.port = rag_port  # RAG proxy gets user's port
    rag_args.model_port = model_port  # Model server gets computed port
    args.port = model_port  # Pass model port to model container
```

### Should we report this?

**Yes**, but consider:
- Issue #1163 (RAG with serve not working) is still open since April 2025
- Even if this bug is fixed, RAG with serve won't work properly (wrong endpoint exposed)
- The ramalama team is already working on RAG architecture changes

**Recommendation**: File the bug report with the fix suggestion, but note it's blocked on #1163 being resolved first.

---

## Impact on henzai

### Current Status

henzai uses `ramalama serve` (without `--rag`) for the persistent model server, because:
1. We need a persistent daemon (can't use interactive `run`)
2. `ramalama serve --rag` doesn't work (Issue #1163 + port bug)
3. We're a wrapper for ramalama features, not a reimplementation

### Decision: Wait or Implement?

**Option A: Wait for ramalama to fix RAG**
- ✅ Aligns with henzai's role as a ramalama wrapper
- ✅ Less maintenance burden
- ❌ Users can't use RAG until ramalama fixes it (6+ months pending)

**Option B: Implement client-side RAG as temporary workaround**
- ✅ Users can use RAG now
- ✅ Can be removed later when ramalama fixes it
- ❌ Reimplements ramalama functionality
- ❌ More code to maintain

**Option C: Help fix ramalama**
- ✅ Benefits entire ramalama community
- ✅ Aligns with open source contribution
- ❌ Requires coordination with ramalama team
- ❌ Still blocked on #1163 architecture work

### Recommendation

**Short term (now):**
1. Document RAG limitation in henzai
2. Show error message: "RAG requires ramalama serve --rag support (pending: github.com/containers/ramalama/issues/1163)"
3. Don't implement client-side RAG (not our role)

**Medium term (if ramalama takes too long):**
1. Implement minimal client-side RAG as workaround
2. Document it as temporary until ramalama fixes #1163
3. Add TODO to remove it when ramalama supports it

**Long term:**
1. File bug report for port parsing issue
2. Monitor #1163 progress
3. Switch to `ramalama serve --rag` when available

---

## Related Issues

- #1163: RAG with serve doesn't work (main blocker)
- #2004: ramalama serve crashes when using --rag
- #2129: Ramalama serve with RAG failed to start after 10 seconds
- #2148: Ramalama run --rag incorrectly uses `rw=true` on --mount with docker
- #1701: RAG not saved on OSX

---

## Testing RAG

### What Works

```bash
# ✅ Create RAG database
ramalama rag /path/to/docs ~/.local/share/henzai/rag-db

# ✅ Interactive RAG query (no port specified)
ramalama run --rag ~/.local/share/henzai/rag-db ollama://library/llama3.2:1b
> What is in the documentation?
```

### What Doesn't Work

```bash
# ❌ Persistent RAG server
ramalama serve --rag ~/.local/share/henzai/rag-db ollama://library/llama3.2:1b

# ❌ RAG with custom port
ramalama serve --port 9999 --rag ~/.local/share/henzai/rag-db ollama://library/llama3.2:1b

# ❌ RAG run with port (daemon mode)
ramalama run --port 9000 --rag ~/.local/share/henzai/rag-db ollama://library/llama3.2:1b
```

---

## Issue 3: No Incremental RAG Updates (RFE)

**Status**: Not yet reported  
**Severity**: Usability issue

### Problem

`ramalama rag` always creates a new collection. If a collection already exists with the same name, it fails with:

```
Error: Collection rag already exists
```

This means:
- **Can't update existing documents** in the index
- **Can't add new documents** to existing index
- **Must delete entire database** to re-index

### Impact on Users

**Bad UX:**
```bash
# User indexes folder once
$ ramalama rag ~/docs ~/.local/share/app/rag-db
✓ Success

# User adds new document to ~/docs
# User tries to update index
$ ramalama rag ~/docs ~/.local/share/app/rag-db
✗ Error: Collection rag already exists

# User forced to delete everything and start over
$ rm -rf ~/.local/share/app/rag-db
$ ramalama rag ~/docs ~/.local/share/app/rag-db
✓ Success (but wasteful - re-indexed EVERYTHING)
```

**Current workaround in henzai:**
- Detect if same folder being re-indexed
- Delete entire database before calling `ramalama rag`
- Re-index all documents (even unchanged ones)

### Requested Feature

Add flags to `ramalama rag` for incremental updates:

**Option 1: Overwrite flag**
```bash
# Replace entire collection
$ ramalama rag --overwrite ~/docs ~/.local/share/app/rag-db
```

**Option 2: Update/append flag**  
```bash
# Add or update documents (smart incremental)
$ ramalama rag --update ~/docs ~/.local/share/app/rag-db
```
- Check file modified times
- Only re-index changed/new files
- Remove deleted files from index

**Option 3: Force flag**
```bash
# Delete and recreate (explicit about destructive operation)
$ ramalama rag --force ~/docs ~/.local/share/app/rag-db
```

### Comparison with Other Tools

**LlamaIndex** (Python):
```python
# Supports incremental updates
index.refresh_ref_docs(documents)
```

**LangChain** (Python):
```python
# Supports adding to existing vectorstore
vectorstore.add_documents(new_docs)
```

**Most vector databases** (Qdrant, Milvus, Chroma):
- All support upsert (update or insert)
- Don't require deleting collection to add documents

### Technical Implementation

Qdrant (the default format) already supports:
- `collection.upsert()` - update or insert documents
- `collection.delete()` - remove specific documents  
- Point IDs can be based on file path hash

So this is just a CLI/API issue, not a limitation of the underlying tech.

### Workaround Impact

**henzai's current code:**
```python
# Bad: Must delete entire database to re-index same folder
if is_reindex:
    shutil.rmtree(self.db_path)  # Wasteful!
    
# Re-index everything (even unchanged documents)
ramalama rag /path/to/docs rag-db
```

**What we'd prefer:**
```python
# Good: Incremental update
ramalama rag --update /path/to/docs rag-db
# Only processes new/changed files
```

### Related Use Cases

1. **User adds documents to folder** - wants to index new ones without re-processing thousands of existing docs
2. **User edits a document** - wants to update just that one document in index
3. **User deletes documents** - wants to remove them from index without full rebuild
4. **Scheduled re-indexing** - cron job that only processes changes since last run

### Recommendation

**Ideal solution:** `ramalama rag --update` with smart incremental logic

**Acceptable solution:** `ramalama rag --force` to make deletion explicit

**Minimum solution:** `ramalama rag --overwrite` to avoid cryptic "already exists" error

---

## Issue 4: No RAG Retrieval Metadata (RFE)

**Status**: Not yet reported to ramalama  
**Ramalama Version**: 0.14.0 (and main branch as of 2025-11-17)

### Problem Description

When using `ramalama serve --rag`, the RAG proxy (`rag_framework`) retrieves relevant documents and augments prompts **automatically and transparently**. However, the API response provides **no metadata** about:

1. Whether documents were actually retrieved for a given query
2. Which documents were used (file names, chunks)
3. Relevance scores of retrieved documents
4. How many documents were retrieved

This makes it impossible for UI/clients to:
- Show users which documents were consulted
- Indicate when RAG was actually used vs. when it was skipped (no relevant docs)
- Provide transparency about information sources
- Debug retrieval quality

### Current Behavior

**Request to port 8080 (RAG proxy):**
```bash
curl -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "test",
    "messages": [{"role": "user", "content": "What keyboard shortcuts are available?"}]
  }'
```

**Response:**
```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "model": "test",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "Super+A opens the chat panel..."
    }
  }],
  "usage": {
    "prompt_tokens": 243,
    "completion_tokens": 262
  }
}
```

**What's missing**: No indication that RAG retrieved context from "README.md" and "USAGE.md"

### Impact on Users

**For henzai:**
- Currently show "📚 RAG Available" badge on ALL messages when RAG is enabled
- Cannot distinguish between:
  - Query where documents were retrieved and used
  - Query where no relevant documents existed (RAG skipped)
- Cannot show users which documents were consulted

**For general use:**
- Users don't know if their RAG database is actually being used
- Cannot verify retrieval quality
- Cannot cite sources in responses
- Harder to debug "why didn't RAG help with this query?"

### Suggested Fix

Add a `rag` field to the response that includes retrieval metadata:

```json
{
  "id": "chatcmpl-...",
  "choices": [{...}],
  "usage": {...},
  "rag": {
    "retrieved": true,
    "documents": [
      {
        "source": "README.md",
        "chunk_id": "chunk_42",
        "score": 0.87,
        "content_preview": "henzai is an AI-first desktop..."
      },
      {
        "source": "docs/USAGE.md",
        "chunk_id": "chunk_103",
        "score": 0.76,
        "content_preview": "Press Super+A to open..."
      }
    ],
    "query_embedding_time_ms": 12,
    "retrieval_time_ms": 45,
    "total_chunks_in_db": 1547
  }
}
```

**When no documents retrieved:**
```json
{
  "rag": {
    "retrieved": false,
    "reason": "no_relevant_documents",
    "query_embedding_time_ms": 12,
    "retrieval_time_ms": 23
  }
}
```

### Alternative: OpenAI-Compatible Extension

If modifying the standard response format is problematic, add an optional parameter:

```bash
curl -X POST http://127.0.0.1:8080/v1/chat/completions \
  -d '{"messages": [...], "rag_metadata": true}'
```

Or expose retrieval via a separate endpoint:
```bash
# Query what would be retrieved (without generating completion)
curl -X POST http://127.0.0.1:8080/v1/rag/retrieve \
  -d '{"query": "What keyboard shortcuts are available?", "top_k": 3}'
```

### Benefits

1. **Transparency**: Users see what information the AI is using
2. **Debugging**: Developers can verify retrieval quality
3. **Citations**: UIs can show "Sources: README.md, USAGE.md"
4. **Smart UI**: Only show RAG badge when actually used
5. **Analytics**: Track retrieval effectiveness over time

### Workarounds

**Current workaround in henzai:**
- Show "📚 RAG Available" badge on all messages (honest but less useful)
- Cannot distinguish actual usage from capability

**No good workaround exists** without modifying `rag_framework` source code.

---

## Issue 5: RAG Disables General Knowledge (CRITICAL UX)

**Status**: Not yet reported  
**Severity**: 🚨 CRITICAL - Makes RAG unusable for general-purpose chat  
**Ramalama Version**: 0.14.0

### Problem Description

When `ramalama serve --rag` is enabled, the model **loses access to its general knowledge** and can only answer questions based on the indexed documents.

**Example:**
```bash
# User indexed: README.md, SHORTCUTS.md (about henzai keyboard shortcuts)
# User enables RAG

User: "What keyboard shortcuts are available?"
AI: "Super+A opens the chat..." ✅ (from indexed docs)

User: "How do I solve a quadratic equation?"
AI: "I cannot find that information in the indexed documents" ❌
# Expected: Should use general knowledge since no relevant docs exist
```

### Expected Behavior

RAG should **augment** the model's capabilities, not **replace** them:

1. **Query arrives** → "How do I solve quadratic equations?"
2. **RAG retrieval** → No relevant documents found (henzai docs don't cover math)
3. **Fallback to general knowledge** → Answer using model's training data
4. **Response** → "To solve ax²+bx+c=0, use the quadratic formula..."

### Current Behavior

1. **Query arrives** → "How do I solve quadratic equations?"
2. **RAG retrieval** → No relevant documents found
3. **Response** → "I don't have information about that" (general knowledge disabled)

### Impact on Users

**RAG becomes unusable** for general-purpose assistants:
- ❌ Cannot use henzai for general questions (math, coding, writing, etc.)
- ❌ RAG documents become a **constraint** instead of an **enhancement**
- ❌ Users must manually toggle RAG on/off depending on question type
- ❌ Defeats the purpose of "AI assistant with access to your documents"

**What users expect:**
- ✅ AI can answer general questions (uses training data)
- ✅ AI can answer questions about indexed documents (uses RAG)
- ✅ RAG provides **additional** context, not **exclusive** context

### Root Cause

The `rag_framework` proxy is configured to treat RAG as **replacement** instead of **augmentation**:

```python
# Current behavior (ramalama rag_framework):
if rag_enabled:
    context = retrieve_from_rag(query)
    prompt = f"Answer based ONLY on this context: {context}\nQuestion: {query}"
    # ❌ Blocks general knowledge
```

**Should be:**
```python
# Better behavior:
if rag_enabled:
    context = retrieve_from_rag(query)
    if context:
        prompt = f"Use this context to enhance your answer: {context}\nQuestion: {query}"
        # ✅ Augments general knowledge
    else:
        prompt = query  # No context found, use general knowledge
```

### Suggested Fix

**Option 1: Make augmentation the default**
- Change `rag_framework` to add context as additional information
- Don't restrict model to ONLY using RAG context
- Let model decide when RAG context is relevant

**Option 2: Add `--rag-mode` flag**
```bash
# Augmentation mode (default): RAG enhances general knowledge
ramalama serve --rag db --rag-mode augment

# Strict mode: Only use RAG documents (current behavior)
ramalama serve --rag db --rag-mode strict

# Optional mode: Use RAG if available, fallback to general knowledge
ramalama serve --rag db --rag-mode optional
```

**Option 3: Let model decide via system prompt**
```bash
# User can control behavior via model's system prompt
ramalama serve --rag db \
  --system "You have access to indexed documents. Use them when relevant, but also use your general knowledge for other questions."
```

### Comparison with Other Tools

**LlamaIndex (Python):**
```python
# RAG augments, doesn't replace
query_engine = index.as_query_engine()
response = query_engine.query("What is quantum physics?")
# ✅ Uses general knowledge + any relevant indexed docs
```

**LangChain (Python):**
```python
# Explicitly supports fallback to general knowledge
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    return_source_documents=True,
    chain_type="stuff"  # Augments, doesn't replace
)
```

**ChatGPT with Retrieval:**
- ✅ Uses uploaded documents when relevant
- ✅ Falls back to general knowledge when documents don't have the answer
- ✅ This is the expected UX

### Workarounds

**Option A: Disable RAG for general questions**
- User must manually toggle RAG off when asking non-document questions
- ❌ Terrible UX, defeats the purpose

**Option B: Don't use `ramalama serve --rag`**
- Use direct port 8081 (bypasses RAG proxy)
- henzai can toggle between port 8080 (with RAG) and 8081 (without RAG) per query
- ✅ This is what we'll implement

**Option C: Detect query type and route**
- henzai detects if query is about indexed documents
- Routes to port 8080 (RAG) if yes, port 8081 (direct) if no
- ❌ Requires NLP classification, complex and error-prone

### Recommendation for henzai

**Short term workaround:**
1. Expose both ports to user in settings:
   - "Use RAG for all queries" → port 8080 (current behavior, document-only)
   - "Use RAG when relevant" → port 8081 (general knowledge, no RAG)
2. Add UI toggle per-conversation: "Enable RAG for this chat"
3. Document the limitation clearly

**Long term (after ramalama fixes it):**
- Use `ramalama serve --rag --rag-mode augment` when available
- RAG becomes truly transparent enhancement

### Why This Is Critical

This issue makes RAG **fundamentally broken** for general-purpose AI assistants. It transforms a helpful feature ("AI can use my documents") into a crippling limitation ("AI can ONLY use my documents").

Without fixing this, users will:
1. Enable RAG to ask about their documents
2. Try to ask a general question (math, code, writing)
3. Get "I don't know" responses
4. Disable RAG in frustration
5. Never use the feature again

---

## Issue 6a: Missing Whisper in RAG Container (RFE)

**Status**: Not yet reported to ramalama  
**Severity**: 🔴 High - Breaks indexing for directories with video/audio files  
**Ramalama Version**: 0.14.0

### Problem Description

The RAG container (`quay.io/ramalama/cuda-rag:latest`) attempts to process video and audio files but crashes because the `whisper` transcription library is not installed.

**Example error:**
```
Error: ImportError: whisper is not installed. Please install it via `pip install openai-whisper`
```

This happens when:
- User has MP4, MOV, AVI (video) or MP3, WAV (audio) files in their RAG directory
- `doc2rag` tool detects the files and tries to transcribe them
- Container lacks the required `whisper` dependency

### Impact on Users

**Current behavior:**
```bash
$ ls ~/Documents/rag/
├── important-doc.pdf
├── notes.docx
└── meeting-recording.mp4  # ← Causes entire indexing to fail

$ ramalama rag ~/Documents/rag ~/.local/share/app/rag-db
✗ Error: whisper is not installed
# Nothing gets indexed - not even the PDF and DOCX!
```

**What users expect:**
- Either transcribe the video (if whisper available)
- OR skip it gracefully and index the documents
- NOT crash entirely

### Workaround

Move video/audio files to a separate directory before indexing:
```bash
mkdir ~/Documents/rag/videos
mv ~/Documents/rag/*.mp4 ~/Documents/rag/videos/
```

### Proposed Fix

Add `whisper` to the RAG container image:

```dockerfile
# In quay.io/ramalama/cuda-rag:latest Dockerfile
RUN pip install openai-whisper
```

### Benefits

1. **Audio/video transcription works out-of-the-box**
   - Users can index meeting recordings
   - Lecture videos become searchable
   - Podcast/interview audio content gets indexed

2. **Better UX**
   - No more cryptic "whisper not installed" errors
   - Works with mixed-content directories (docs + videos)

3. **Feature parity**
   - `doc2rag` already tries to process videos
   - Container should have the tools to do what it attempts

### Trade-offs

**Container size increase:**
- `whisper` + dependencies ≈ 2-3 GB additional
- Current RAG container: ~4 GB
- With whisper: ~6-7 GB total

**Performance considerations:**
- Audio transcription is slow without GPU
- With GPU (CUDA): Fast and practical ✅
- The container is already CUDA-enabled, so this makes sense

### Alternative Approach

If container size is a concern, provide **two container variants**:

1. **Minimal**: `quay.io/ramalama/cuda-rag:latest` (current, no whisper)
2. **Full**: `quay.io/ramalama/cuda-rag-full:latest` (with whisper)

Users can choose based on their needs:
```bash
# Basic (documents only)
ramalama rag --container cuda-rag ~/docs db

# Full (documents + audio/video)
ramalama rag --container cuda-rag-full ~/docs db
```

### Use Cases

**Enabled by this RFE:**
- Index lecture recordings for study notes
- Search through meeting archives
- Make podcast content searchable
- Extract insights from video interviews
- Accessibility: Transcribe audio content for text search

---

## Issue 6b: No Graceful Degradation for Optional Dependencies (RFE)

**Status**: Not yet reported to ramalama  
**Severity**: 🟠 Medium - Poor error handling  
**Ramalama Version**: 0.14.0

### Problem Description

When `doc2rag` encounters a file that requires an optional dependency (like MP4 → whisper), it crashes instead of gracefully skipping the file.

**Current behavior:**
```
ModuleNotFoundError: No module named 'whisper'
→ Process exits with error code 1
→ Entire indexing job fails
```

**Expected behavior:**
```
Warning: Skipping meeting.mp4 (whisper not installed)
       Hint: Install with: pip install openai-whisper
→ Continue processing other files
→ Index succeeds with 9/10 files (1 skipped)
```

### Impact

**Brittleness:**
- Any optional dependency failure crashes the entire job
- Users lose confidence ("why did indexing fail?")
- Mixed-content directories are unsupported

**Poor error messages:**
- Python stack trace instead of helpful guidance
- Doesn't explain which file caused the issue
- Doesn't suggest how to fix it

### Implementation

Add graceful degradation to `doc2rag`:

```python
# At module level - check for optional dependencies
try:
    import whisper
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False
    logger.warning("whisper not available - audio/video transcription disabled")
    logger.info("Install with: pip install openai-whisper")

try:
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    logger.warning("OCR not available - image text extraction disabled")

# When processing files
def process_file(file_path):
    suffix = file_path.suffix.lower()
    
    if suffix in ['.mp4', '.mov', '.avi', '.mp3', '.wav']:
        if HAS_WHISPER:
            return transcribe_audio_video(file_path)
        else:
            logger.warning(f"Skipping {file_path.name} (whisper not installed)")
            return None  # Skip gracefully
    
    elif suffix in ['.png', '.jpg', '.jpeg']:
        if HAS_OCR:
            return extract_text_from_image(file_path)
        else:
            logger.warning(f"Skipping {file_path.name} (OCR not available)")
            return None  # Skip gracefully
    
    # ... handle other formats ...
```

### Benefits

1. **Robustness**: Mixed-content directories work
2. **Better UX**: Clear warnings instead of crashes
3. **Flexibility**: Supports minimal containers (without heavy dependencies)
4. **Helpful errors**: Users know exactly what's missing and how to add it

### Related to Issue 6a

These two issues are complementary:

- **Issue 6a**: Add whisper to container → enables full functionality
- **Issue 6b**: Graceful degradation → ensures robustness even without whisper

**Both should be implemented:**
- Default container has whisper (Issue 6a) → most users get full features
- Graceful skipping (Issue 6b) → handles edge cases, custom containers, other optional deps

### Other Optional Dependencies

This pattern applies to more than just whisper:

- **OCR** (`pytesseract`) - Image text extraction
- **Pandoc** - Some document format conversions
- **LibreOffice** - Complex document parsing

All should skip gracefully if unavailable, not crash.

---

## Issue #7: No Support for Incremental Indexing / Re-indexing

**Status**: ⚠️ **CRITICAL UX BUG - User-Facing**  
**Severity**: High  
**Affects**: `ramalama rag` command  
**Upstream Issue**: TBD

### Problem

When a user tries to re-index documents (e.g., after adding new files or fixing a previous indexing error), `ramalama rag` fails with:

```
Error: Collection rag already exists
```

**Exit code**: 22

### Root Cause

1. `ramalama rag` creates a Qdrant collection named "rag"
2. Collection persists inside the container's Qdrant database (mounted from host)
3. No CLI flag to:
   - Overwrite existing collection (`--overwrite`)
   - Update/append to existing collection (`--update`)
   - Delete existing collection (`--delete-first`)
4. User is **stuck** - can't re-index without manually deleting database files

### Impact on Users

**Without workaround**, users must:
1. Find where the database is stored (`~/.local/share/henzai/rag-db/`)
2. Manually `rm -rf` the database
3. Try indexing again
4. **Repeat for every re-index**

This is unacceptable UX for a GNOME extension - users expect "click to re-index" to work.

### Current henzai Workaround

**Implemented in `rag.py`** (lines 105-126):

```python
# Always delete existing database before indexing
# This is needed because:
# 1. ramalama rag doesn't support --overwrite or --update
# 2. Qdrant collection persists inside container even if host directory looks empty
# 3. User might be re-indexing same or different source
if db_exists:
    shutil.rmtree(self.db_path)
    logger.info("Removed old database for re-indexing")
```

**Why this is necessary:**
- Qdrant collection exists **inside container**, not visible to Python's `iterdir()`
- Can't detect collection state from host side
- Must always delete to avoid "Collection already exists" error

### Proposed ramalama Enhancement

Add CLI flags to `ramalama rag`:

```bash
# Option 1: Overwrite existing collection
ramalama rag --overwrite /path/to/docs /path/to/db

# Option 2: Update existing collection (append new docs)
ramalama rag --update /path/to/docs /path/to/db

# Option 3: Delete collection first
ramalama rag --delete-existing /path/to/docs /path/to/db

# Option 4: Auto-detect and prompt
ramalama rag --force /path/to/docs /path/to/db
```

**Recommended approach**: `--overwrite` (deletes and recreates collection)

### Benefits of Fix

1. **Better UX**: Users can re-index without manual cleanup
2. **Incremental updates**: Support adding new docs without full re-index
3. **Error recovery**: Failed indexing doesn't block future attempts
4. **Standard behavior**: Matches other vector DB tools (Chroma, Weaviate, etc.)

### Alternative: Document Versioning

Even better would be collection versioning:

```bash
ramalama rag --collection "my-docs-v2" /path/to/docs /path/to/db
```

Then applications could:
- Keep multiple versions of same docs
- Switch between collections at runtime
- Test new indexing without losing old data

---

## Issue 8: RAG Disables Reasoning/Thinking (CRITICAL)

**Status**: Not yet reported to ramalama  
**Severity**: 🚨 CRITICAL - Breaks reasoning models when RAG is enabled  
**Ramalama Version**: 0.14.0
**Models Affected**: DeepSeek-R1, QwQ, other reasoning-capable models

### Problem Description

When `ramalama serve --rag` is enabled, the API **does not return `reasoning_content` chunks** even when `"reasoning": true` is explicitly set in the API request.

**Expected behavior (no RAG):**
```bash
curl http://127.0.0.1:8080/v1/chat/completions \
  -d '{"model": "deepseek-r1", "messages": [...], "stream": true, "reasoning": true}'

# Response chunks include:
{"delta": {"reasoning_content": "<think>Let me analyze this..."}}
{"delta": {"reasoning_content": "First, I need to..."}}
{"delta": {"content": "The answer is..."}}
```

**Actual behavior (with RAG):**
```bash
# Same request, but with --rag flag enabled
curl http://127.0.0.1:8080/v1/chat/completions \
  -d '{"model": "deepseek-r1", "messages": [...], "stream": true, "reasoning": true}'

# Response chunks ONLY include content, no reasoning_content:
{"delta": {"content": "The answer is..."}}
# ❌ No thinking/reasoning shown!
```

### Impact on Users

**Reasoning models lose their key feature:**
- DeepSeek-R1's visible reasoning process (the main selling point) disappears
- Users can't see the model "thinking" through problems
- Breaks trust and transparency ("how did it reach that conclusion?")
- Makes reasoning models indistinguishable from regular models

**UI implications:**
- Applications showing thinking bubbles get nothing to display
- Users assume the model is "not thinking" when it actually is (just hidden)
- Debugging model behavior becomes impossible

### Root Cause

The RAG proxy (`rag_framework`) likely:
1. Strips `reasoning_content` from API responses
2. OR doesn't pass `reasoning: true` parameter to underlying llama-server
3. OR modifies the response format in a way that removes reasoning chunks

### Testing

**Test 1: Without RAG (works)**
```bash
# ramalama serve (no --rag flag)
curl http://127.0.0.1:8080/v1/chat/completions \
  -d '{"model": "ollama://library/deepseek-r1:latest", 
       "messages": [{"role":"user","content":"what is 2+2?"}],
       "stream": true,
       "reasoning": true}'

# ✅ Result: reasoning_content chunks present
```

**Test 2: With RAG (fails)**
```bash
# ramalama serve --rag /path/to/db
curl http://127.0.0.1:8080/v1/chat/completions \
  -d '{"model": "ollama://library/deepseek-r1:latest", 
       "messages": [{"role":"user","content":"what is 2+2?"}],
       "stream": true,
       "reasoning": true}'

# ❌ Result: NO reasoning_content chunks, only content
```

### Suggested Fix

**Option 1: Pass through reasoning parameter**
Ensure `rag_framework` forwards the `reasoning: true` parameter to llama-server and doesn't strip `reasoning_content` from responses.

**Option 2: Add RAG-aware reasoning handling**
If RAG modifies prompts in a way that breaks reasoning, adjust the prompt construction to preserve reasoning format.

**Option 3: Document incompatibility**
If RAG and reasoning are fundamentally incompatible (e.g., RAG prompt injection breaks reasoning format), document this clearly and provide workarounds.

### Workaround

**henzai's approach** (to be implemented):
1. Detect if model supports reasoning (`deepseek-r1`, `qwq`, etc.)
2. When RAG is enabled + reasoning model is active:
   - **Option A**: Disable RAG temporarily (use direct API port 8081)
   - **Option B**: Show warning: "Reasoning display unavailable when RAG is enabled"
   - **Option C**: Disable reasoning mode when RAG is enabled
3. Add UI toggle: "Enable RAG" vs "Show Reasoning" (can't have both)

### Related Issues

- **Issue #5**: RAG disables general knowledge (same root cause - RAG proxy modifies behavior too aggressively)
- Both issues suggest RAG should be **transparent** - augment without breaking core features

### Why This Matters

Reasoning models are specifically chosen for their ability to:
1. Show their thought process
2. Verify their logic step-by-step
3. Build trust through transparency

RAG breaking this defeats the purpose of using reasoning models in the first place.

---

**Last Updated**: 2025-11-18  
**Next Action**: 
1. ✅ Implement workaround in henzai (always delete db before indexing)
2. ✅ Document limitation in RAG.md
3. ✅ Document RAG + Reasoning incompatibility (Issue #8)
4. File RFE #6a (add whisper to container) on ramalama repo
5. File RFE #6b (graceful degradation) on ramalama repo
6. File RFE #7 (support re-indexing) on ramalama repo
7. File critical issue #5 (RAG disables general knowledge) on ramalama repo
8. File critical issue #8 (RAG disables reasoning) on ramalama repo
9. Implement workaround in henzai (detect reasoning model + RAG conflict)

