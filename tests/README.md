# henzai Test Suite

This directory contains automated tests for henzai's core functionality. These tests are designed to be run locally and are ready for CI integration.

## Test Categories

### RAG (Retrieval-Augmented Generation)

#### `test-rag-e2e.py` - Complete RAG Test Suite
Comprehensive end-to-end testing of RAG functionality.

**Tests:**
1. **Service Running** - Verifies henzai-daemon is active
2. **RAG Indexing** - Creates test documents and indexes them
3. **Augment Mode** - Tests document + general knowledge mode
4. **Strict Mode** - Tests document-only mode (should refuse out-of-context queries)
5. **Hybrid Mode** - Tests document-preferred mode with general knowledge fallback
6. **Document Relevance** - Verifies RAG returns relevant documents, not irrelevant ones
7. **RAG Disable** - Tests disabling RAG functionality

**Test Data:**
- Creates temporary test documents (henzai info, technical docs, recipes)
- Cleans up after test completion
- Uses markdown format (`.md` files)

**Expected Behavior:**
- **Strict mode**: Must say "I don't know" for out-of-context queries
- **Augment mode**: Can answer both document and general knowledge questions
- **Hybrid mode**: Prefers documents, falls back to general knowledge
- **Relevance**: Should return documents about henzai, not recipes

**Usage:**
```bash
./tests/test-rag-e2e.py
```

**Prerequisites:**
- henzai-daemon running
- Ramalama service active

---

#### `test-rag-reasoning.py` - RAG + Reasoning Integration
Tests that reasoning models work correctly with RAG enabled.

**Tests:**
1. **Reasoning through RAG** - Verifies `reasoning_content` passes through RAG proxy
2. **Strict mode + reasoning** - Ensures strict mode still enforces document-only responses
3. **Augment mode + reasoning** - Verifies reasoning works with general knowledge queries

**Critical Scenarios:**
- Reasoning models (e.g., deepseek-r1) generate `reasoning_content` field
- RAG proxy must pass through `reasoning_content` without stripping it
- RAG mode prompts must not interfere with reasoning generation

**Expected Behavior:**
- **With reasoning model**: Should see multiple `reasoning_content` chunks in streaming responses
- **Strict mode**: Should still refuse out-of-context queries even with reasoning
- **Augment mode**: Should generate reasoning for general knowledge queries

**Usage:**
```bash
./tests/test-rag-reasoning.py
```

**Prerequisites:**
- henzai-daemon running
- Ramalama running with `--rag` flag
- Reasoning model (e.g., `deepseek-r1:14b`) loaded

---

### Streaming & LLM

#### `test-streaming.py`
Tests basic streaming functionality through the LLM client.

#### `test-reasoning.py`
Tests reasoning model output parsing and handling.

#### `test-thinking-chunks.py`
Tests that thinking/reasoning content is properly chunked and streamed.

---

### D-Bus Integration

#### `test-dbus-streaming-live.py`
Tests D-Bus streaming integration with live service.

#### `henzai-daemon/tests/test_dbus_streaming.py`
Unit tests for D-Bus streaming methods.

#### `henzai-daemon/tests/test_llm_streaming.py`
Unit tests for LLM client streaming.

---

### Other Functionality

#### `test-health-check.py`
Tests Ramalama health endpoint detection and polling.

#### `test-model-switch.py`
Tests switching between different models.

#### `test-history.py`
Tests conversation history management.

#### `test-newchat.py`
Tests new chat session creation.

---

## Running Tests

### Individual Tests
```bash
# Run specific test
./tests/test-rag-e2e.py
./tests/test-rag-reasoning.py
```

### All Tests
```bash
# Run all tests in sequence
for test in tests/test-*.py; do
    echo "Running $test..."
    python3 "$test" || echo "FAILED: $test"
done
```

---

## CI Integration (TODO)

### Recommended CI Setup

#### GitHub Actions Example
```yaml
name: henzai Tests

on: [push, pull_request]

jobs:
  test-rag:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Install dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y python3-gi gir1.2-glib-2.0
        pip install -r requirements.txt
    
    - name: Start services
      run: |
        ./install.sh
        systemctl --user start henzai-daemon
    
    - name: Run RAG tests
      run: |
        ./tests/test-rag-e2e.py
        ./tests/test-rag-reasoning.py
    
    - name: Run other tests
      run: |
        ./tests/test-streaming.py
        ./tests/test-reasoning.py
```

---

## Test Requirements

### System Requirements
- Python 3.10+
- D-Bus
- Systemd user services
- Podman (for Ramalama containers)

### Python Dependencies
```python
# henzai-daemon/requirements.txt
dbus-python
pygobject
openai  # For API compatibility
```

### Service Requirements
- `henzai-daemon.service` running
- `ramalama.service` running
- For RAG tests: RAG container image available

---

## Writing New Tests

### Test Template
```python
#!/usr/bin/env python3
"""
Test Name: Brief description

Tests:
1. Test case 1
2. Test case 2
"""

import sys

def log(message, status="INFO"):
    symbol = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌"}.get(status, "•")
    print(f"{symbol} {message}")

def test_something():
    """Test description"""
    log("Testing something...", "INFO")
    
    # Test logic here
    
    if success:
        log("Test passed", "PASS")
        return True
    else:
        log("Test failed", "FAIL")
        return False

def main():
    results = []
    
    # Run tests
    results.append(("Test Name", test_something()))
    
    # Summary
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nRESULTS: {passed}/{total} passed")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
```

### Best Practices
1. **Always clean up** - Remove test data after completion
2. **Use descriptive names** - Test names should explain what they test
3. **Document expected behavior** - Add docstrings with expected outcomes
4. **Return exit codes** - 0 for success, non-zero for failure
5. **Log everything** - Use the log() helper for clear output
6. **Handle timeouts** - D-Bus and API calls should have timeouts
7. **Test edge cases** - Not just happy paths

---

## Known Issues & Limitations

### RAG Testing
- **Indexing time**: First-time indexing can take 30-60 seconds
- **Container download**: RAG container is ~4.4 GB, may take time on first run
- **Model responses**: LLM responses are non-deterministic, use keyword matching

### Reasoning Testing
- **Model-specific**: Only works with reasoning models (deepseek-r1, qwq)
- **Response length**: Reasoning models generate longer responses (slower)
- **Format variations**: Different models use different reasoning formats

### General
- **Service state**: Tests assume clean service state
- **Network access**: Some tests require internet for model downloads
- **GPU access**: RAG tests may require GPU for embeddings

---

## Test Coverage

### Current Coverage
- ✅ RAG indexing
- ✅ RAG modes (augment, strict, hybrid)
- ✅ RAG + reasoning integration
- ✅ Streaming functionality
- ✅ D-Bus interface
- ✅ Model switching
- ✅ Health checks

### TODO (Future Tests)
- ⏳ UI integration tests (requires nested GNOME Shell)
- ⏳ Multi-user RAG isolation
- ⏳ Concurrent query handling
- ⏳ Memory/resource usage
- ⏳ Error recovery scenarios
- ⏳ Prompt template management

---

## Debugging Failed Tests

### Check Service Logs
```bash
# Daemon logs
journalctl --user -u henzai-daemon -f

# Ramalama logs
journalctl --user -u ramalama -f
```

### Check Service Status
```bash
systemctl --user status henzai-daemon
systemctl --user status ramalama
```

### Verify RAG State
```bash
busctl --user call org.gnome.henzai /org/gnome/henzai org.gnome.henzai GetRAGStatus ss "" "true"
```

### Check RAG Container
```bash
# List running containers
podman ps

# Check RAG_MODE environment
podman exec <rag-container-id> env | grep RAG_MODE

# Check model server flags
podman ps --no-trunc | grep reasoning
```

### Manual API Test
```bash
# Test API directly
curl http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"test"}],"stream":false}'
```

---

## Contact & Contributing

For issues or questions about tests:
1. Check logs (see Debugging section)
2. Review `AGENTS.md` for known issues
3. Create issue with test output and logs
