# RAG (Retrieval-Augmented Generation) in henzai

**Status**: ✅ Implemented  
**Version**: 0.1.0  
**Last Updated**: 2025-11-17

---

## Overview

henzai supports RAG through Ramalama's native RAG feature. Users can index their local documents (markdown, PDF, DOCX, etc.) and have the AI answer questions based on that content.

**Architecture**: henzai is a wrapper for Ramalama's RAG functionality - we use `ramalama rag` for indexing and `ramalama serve --rag` for RAG-augmented inference.

---

## User Workflow

### 1. Index Documents

**Via Settings UI:**
1. Open Extensions → henzai → Settings
2. Click "Browse..." to select folder containing documents
3. Click "Index Now"
4. Wait for indexing to complete (~5-30 seconds depending on document count)

**Supported file formats:**
- Markdown (`.md`)
- PDF (`.pdf`)
- Microsoft Word (`.docx`)
- PowerPoint (`.pptx`)
- HTML (`.html`)
- CSV (`.csv`)
- Excel (`.xlsx`)
- AsciiDoc
- ❌ **NOT supported**: Plain text (`.txt`)

**First-time indexing:**
- Downloads RAG tools container (~4 GB, one-time)
- Progress shown in status message

### 2. Enable RAG

**Via Settings UI:**
1. Toggle "Enable RAG" ON
2. Daemon restarts ramalama service with `--rag` flag
3. Status updates to "RAG enabled successfully"

**What happens:**
- Ramalama starts TWO containers:
  - Port 8080: RAG proxy (`rag_framework serve`)
  - Port 8081: Direct LLM (`llama-server`)
- All queries to port 8080 are automatically augmented with context from indexed documents

### 3. Query with RAG

Just use henzai normally - RAG is transparent:
- Press Super+A to open henzai
- Ask questions about your indexed documents
- AI automatically retrieves relevant context and includes it in responses
- Look for the **📚 RAG Available** badge on assistant messages

**About the badge:**
- **📚 RAG Available** means RAG is enabled for that conversation
- The RAG proxy (`rag_framework`) decides dynamically if documents are relevant
- Not all queries will use documents - simple questions like "What is 2+2?" won't retrieve context
- Currently, we cannot detect if documents were *actually* used (see Limitations below)

---

## Technical Details

### Architecture: Two-Port System

When RAG is enabled:

```
User Query
    ↓
Port 8080 (RAG Proxy - rag_framework)
    ↓ [Retrieve context from Qdrant]
    ↓ [Augment prompt with context]
    ↓
Port 8081 (LLM - llama-server)
    ↓ [Generate response]
    ↓
Response with document context
```

When RAG is disabled:
```
User Query
    ↓
Port 8080 (Direct LLM - llama-server)
    ↓ [Generate response]
    ↓
Response without document context
```

### D-Bus Methods

**SetRAGConfig** - Index documents
```
busctl --user call org.gnome.henzai /org/gnome/henzai \
  org.gnome.henzai SetRAGConfig ssb \
  "/path/to/docs" "qdrant" false

Returns: boolean (true if indexing started)
Emits signals: RAGIndexingStarted, RAGIndexingProgress, RAGIndexingComplete/Failed
```

**SetRagEnabled** - Enable/disable RAG mode
```
busctl --user call org.gnome.henzai /org/gnome/henzai \
  org.gnome.henzai SetRagEnabled b true

Returns: JSON with success status
Side effect: Restarts ramalama.service with/without --rag flag
```

**GetRAGStatus** - Get indexing status
```
busctl --user call org.gnome.henzai /org/gnome/henzai \
  org.gnome.henzai GetRAGStatus sb \
  "/path/to/docs" false

Returns: JSON with indexed status, file count, last_indexed timestamp
```

**GetStatus** - Overall system status (includes RAG info)
```
busctl --user call org.gnome.henzai /org/gnome/henzai \
  org.gnome.henzai GetStatus

Returns: JSON including:
  - rag_enabled: boolean
  - rag_port: 8080 (if enabled, else null)
  - llm_port: 8081 (if RAG enabled, else 8080)
```

### Storage

**RAG Database**: `~/.local/share/henzai/rag-db/`
- Format: Qdrant vector database
- Contains: Embedded document chunks + metadata
- Created by: `ramalama rag` command
- Used by: `rag_framework serve` container

**Metadata**: `~/.local/share/henzai/rag-db/henzai-metadata.json`
- Source path
- Format (qdrant)
- File count
- Indexed timestamp
- OCR enabled flag

---

## Known Issues & Limitations

### Re-indexing Behavior

**Problem**: `ramalama rag` doesn't support incremental updates.

**Current workaround**: 
- When re-indexing the **same folder**, henzai deletes the entire database and re-indexes all documents
- This is wasteful but necessary due to Ramalama limitation

**If you try to index a different folder**:
- Error: "Collection rag already exists"
- **Solution**: Delete old database first: `rm -rf ~/.local/share/henzai/rag-db`

**See**: `docs/reference/RAMALAMA_RFE.md` - Issue #3

### Supported File Formats

**Not supported by Ramalama**:
- Plain text files (`.txt`) - Despite being text, the RAG container (`docling`) doesn't recognize them
- **Workaround**: Rename `.txt` → `.md` before indexing

### Video/Audio Files Cause Indexing Failure

**Problem**: If your folder contains video files (`.mp4`, `.mov`, etc.) or audio files (`.mp3`, `.wav`), indexing will fail with:

```
Error: ImportError: whisper is not installed
```

**Why this happens**:
- `ramalama rag` processes ALL files in the directory (ignores henzai's format filter)
- `doc2rag` tool tries to transcribe audio/video using OpenAI's `whisper` library
- `whisper` is **not installed** in the RAG container (`cuda-rag:latest`)
- Instead of skipping, it crashes

**Workaround**:
Move video/audio files to a separate directory before indexing:
```bash
mkdir -p ~/Documents/rag/videos
mv ~/Documents/rag/*.mp4 ~/Documents/rag/videos/
mv ~/Documents/rag/*.mp3 ~/Documents/rag/videos/
```

**Tracking**: See `docs/reference/RAMALAMA_RFE.md` - Issue #6a and #6b

**Future fix**: 
- RFE #6a: Add `whisper` to RAG container (enables audio/video transcription)
- RFE #6b: Gracefully skip unsupported files instead of crashing

### First-time Setup

**Large download**: First use requires downloading ~4 GB RAG container (`quay.io/ramalama/cuda-rag:latest`)
- UI shows progress: "Downloading RAG tools (~4 GB, first time only)..."
- Subsequent indexing is fast (no download)

---

## Testing

### Manual Test

```bash
# 1. Create test documents
mkdir -p /tmp/test-docs
echo "# Test Doc
henzai is a GNOME Shell extension for local AI." > /tmp/test-docs/doc.md

# 2. Index
busctl --user call org.gnome.henzai /org/gnome/henzai \
  org.gnome.henzai SetRAGConfig ssb \
  "/tmp/test-docs" "qdrant" false

# 3. Enable RAG
busctl --user call org.gnome.henzai /org/gnome/henzai \
  org.gnome.henzai SetRagEnabled b true

# 4. Check status
busctl --user call org.gnome.henzai /org/gnome/henzai \
  org.gnome.henzai GetStatus | grep rag

# Should show: "rag_enabled": true, "rag_port": 8080, "llm_port": 8081
```

### Automated Test

```bash
# Run E2E test
cd henzai
./tests/test-rag-e2e.sh
```

---

## Troubleshooting

### "Indexing failed with exit code 1"

**Likely cause**: Unsupported file format (e.g., `.txt`)

**Check logs**:
```bash
journalctl --user -u henzai-daemon -n 50 | grep -i "rag\|index"
```

**Look for**: `Error: File format not allowed: filename.txt`

**Solution**: Only use supported formats (`.md`, `.pdf`, `.docx`, etc.)

### "Collection rag already exists"

**Cause**: Trying to index different folder when database already exists

**Solution**: 
```bash
# Delete old database
rm -rf ~/.local/share/henzai/rag-db

# Or use settings UI to re-index same folder (auto-deletes)
```

### RAG not working (no context in responses)

**Check RAG is actually enabled**:
```bash
busctl --user call org.gnome.henzai /org/gnome/henzai \
  org.gnome.henzai GetStatus | grep rag_enabled
```

**Check both containers are running**:
```bash
podman ps | grep ramalama
# Should show TWO processes when RAG enabled
```

**Check port 8080 is RAG proxy**:
```bash
curl http://127.0.0.1:8080/health
# Should return: {"status": "ok", "rag": "ok"}
```

---

## Limitations

### 🚨 1. RAG Disables General Knowledge (CRITICAL)

**Issue**: When RAG is enabled, the model **loses access to its general knowledge** and can only answer based on indexed documents.

**Example:**
```
User: "What keyboard shortcuts does henzai have?"
AI: "Super+A opens the chat..." ✅ (from indexed henzai docs)

User: "How do I solve a quadratic equation?"
AI: "I cannot find that information in the documents" ❌ (no math in henzai docs)
```

**Impact:**
- ❌ Cannot ask general questions (math, coding, trivia, etc.) when RAG is enabled
- ❌ RAG becomes a **constraint** instead of an **enhancement**
- ❌ Users must toggle RAG off for general queries, on for document queries

**Why this happens:**
- `ramalama serve --rag` uses a proxy that restricts responses to RAG context only
- The proxy tells the model: "Answer ONLY based on this context"
- This blocks the model's general training knowledge

**Workaround (coming soon):**
- Option A: Manual toggle - disable RAG for general questions
- Option B: Smart routing - henzai automatically uses port 8081 (direct LLM) for general queries
- Option C: Per-conversation RAG toggle - enable only for document-related chats

**Tracking**: See `RAMALAMA_RFE.md` Issue #5 for detailed analysis and proposed fixes

**What should happen:**
- RAG should **augment** general knowledge, not **replace** it
- Model should use documents when relevant, general knowledge otherwise
- This is how ChatGPT, LlamaIndex, and LangChain RAG works

### 2. No Retrieval Metadata

**Issue**: The RAG proxy (`rag_framework`) doesn't expose which documents were retrieved or if retrieval happened at all.

**Impact:**
- UI shows "📚 RAG Available" badge on all messages when RAG is enabled
- Cannot distinguish queries that used documents from those that didn't
- Cannot show which source files were consulted
- Cannot display relevance scores or citations

**Workaround**: Badge text says "Available" (not "Used") to be honest about uncertainty

**Tracking**: See `RAMALAMA_RFE.md` Issue #4 for detailed RFE

### 3. No Incremental Updates

**Issue**: Cannot add/update documents without deleting entire database

**Impact:**
- Re-indexing large document sets is slow
- Editing one document requires re-processing all documents

**Workaround**: henzai auto-deletes and re-creates database when source path is the same

**Tracking**: See `RAMALAMA_RFE.md` Issue #3

### 4. Port Parsing Error (Cosmetic)

**Issue**: `ramalama serve --rag --port 8080` shows error "parsing container port: invalid syntax"

**Impact:** None - error is cosmetic, ports work correctly (8080 for RAG, 8081 for LLM)

**Workaround**: Ignore the error

**Tracking**: See `RAMALAMA_RFE.md` Issue #2

---

## Future Improvements

Tracked in `docs/reference/RAMALAMA_RFE.md`:

1. **Retrieval metadata** - Show which documents were used, relevance scores, citations
2. **Incremental updates** - Add/update documents without full re-index
3. **Multiple document sets** - Support multiple RAG databases
4. **Automatic re-indexing** - Watch folder for changes
5. **Better format support** - Support `.txt` files natively

---

## See Also

- `docs/reference/RAMALAMA_RFE.md` - Ramalama issues and RFEs
- `docs/reference/DBUS_API.md` - Full D-Bus API reference
- [Ramalama RAG documentation](https://github.com/containers/ramalama)

