# henzAI Roadmap

## Current Focus: RAG Implementation ✅
- [x] Basic RAG integration with Ramalama
- [x] Multiple RAG modes (augment, strict, hybrid)
- [x] UI for folder selection and mode configuration
- [x] Progress tracking during indexing
- [x] Automatic re-indexing support

## Near-term (Next Release)

### Critical Fixes
- [ ] **Fix RAG + Reasoning Incompatibility (Ramalama upstream)**
  - **Issue**: RAG proxy strips `reasoning_content` from API responses
  - **Impact**: Reasoning models (DeepSeek-R1, QwQ) lose their thinking display when RAG is enabled
  - **Solution**: Fix in Ramalama's `rag_framework` container
  - **Status**: Documented in `docs/reference/RAMALAMA_RFE.md` Issue #8
  - **PR**: To be submitted to containers/ramalama
  - **Files to modify**:
    - `container-images/scripts/rag_framework` - preserve `reasoning_content` in proxy
    - Forward `reasoning: true` parameter to llama-server
    - Test with DeepSeek-R1 to confirm thinking chunks appear
  - **Workaround**: Users must choose between RAG and Reasoning display (documented)

### Enhancements
- [ ] Improve RAG progress tracking (capture more container output)
- [ ] Add RAG retrieval metadata in API responses (Ramalama RFE #4)
- [ ] Support incremental RAG indexing (Ramalama RFE #3)
- [ ] Add audio/video transcription support (Ramalama RFE #6a)

## Mid-term

### User Experience
- [ ] RAG source citation in responses (show which documents were used)
- [ ] UI indicator when RAG was actually used vs available
- [ ] Smart RAG toggle per-conversation
- [ ] Document preview in RAG settings

### Advanced RAG Features
- [ ] Multiple document collections (switch between different RAG databases)
- [ ] Document versioning (track changes, re-index only modified files)
- [ ] Query-specific RAG filters (search by document type, date, etc.)
- [ ] Hybrid search (combine vector + keyword search)

### Tools & Actions
- [ ] Expand system action tools (file operations, web search, etc.)
- [ ] Tool use with RAG (let AI decide when to use documents vs tools)
- [ ] Multi-step reasoning with tool chains

## Long-term

### Platform Integration
- [ ] Integration with GNOME Files (right-click → "Ask henzAI about this")
- [ ] System-wide context awareness (current app, open files, etc.)
- [ ] Calendar and email integration
- [ ] Notification intelligence

### Model Management
- [ ] Auto-download models from Ollama/HuggingFace
- [ ] Model performance benchmarking
- [ ] Model recommendation based on task
- [ ] Multi-model workflows (use different models for different tasks)

### Privacy & Security
- [ ] Local-only mode (fully air-gapped)
- [ ] Encrypted document storage
- [ ] Audit log for AI actions
- [ ] Sandboxed tool execution

## Upstream Dependencies (Ramalama)

These features require changes in Ramalama itself:

### Critical
1. **RAG + Reasoning compatibility** (Issue #8)
   - Fix rag_framework to preserve reasoning_content
   - Estimated effort: Small (1-2 days)
   - User impact: HIGH (reasoning models are popular)

### High Priority
2. **RAG metadata in responses** (Issue #4)
   - Return which documents were retrieved
   - Return relevance scores
   - Estimated effort: Medium (3-5 days)

3. **Incremental RAG indexing** (Issue #7)
   - Support re-indexing without full deletion
   - Add `--update` or `--overwrite` flags
   - Estimated effort: Medium (3-5 days)

### Medium Priority
4. **Whisper in RAG container** (Issue #6a)
   - Add audio/video transcription support
   - Estimated effort: Small (container update)

5. **Graceful degradation** (Issue #6b)
   - Skip unsupported files instead of failing
   - Better error messages
   - Estimated effort: Small (1-2 days)

### Low Priority
6. **RAG mode as CLI flag** (Issue #5)
   - Add `--rag-mode augment|strict|hybrid` flag
   - Currently using env var workaround
   - Estimated effort: Small (1 day)

## Community & Documentation

- [ ] Video demo of RAG features
- [ ] Blog post about RAG integration
- [ ] Tutorial: Building your own knowledge base with henzAI
- [ ] Contribution guide for new developers
- [ ] Automated testing for all RAG modes

---

**Last Updated**: 2025-11-18  
**Maintainer**: Carlos Soriano (@csoriano2718)  
**Contributing**: See CONTRIBUTING.md for how to help with roadmap items
