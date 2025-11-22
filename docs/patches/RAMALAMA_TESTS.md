# Ramalama RAG Mode Tests

## Overview

Comprehensive tests for RAG modes have been added to the Ramalama repository following their pytest patterns and conventions.

## Test File Location

`test/e2e/test_rag_modes.py` in the Ramalama repository

## Tests Included

### 1. `test_rag_strict_mode`

**Purpose**: Verify strict mode only answers from documents

**What it tests**:
- Queries about document content should succeed
- Queries about general knowledge should refuse or say "I don't know"
- No hallucinations or general knowledge leakage

**Example**:
```python
# Document query → Should answer
"What RAG modes does Ramalama support?"

# General knowledge → Should refuse
"What is the capital of France?"
```

### 2. `test_rag_hybrid_mode`

**Purpose**: Verify hybrid mode prefers documents but allows general knowledge fallback

**What it tests**:
- Document queries use document content
- General knowledge queries still work
- Proper balance between docs and general knowledge

**Example**:
```python
# Document query → Uses documents
"What inference backend does Ramalama use?"

# General knowledge → Uses general knowledge
"What is Python?"
```

### 3. `test_rag_augment_mode`

**Purpose**: Verify augment mode (default) freely combines docs with general knowledge

**What it tests**:
- Document queries work
- General knowledge queries work
- No restrictions on knowledge source

**Example**:
```python
# Document query → Uses documents
"Who created Ramalama?"

# General knowledge → Answers freely
"What is artificial intelligence?"
```

### 4. `test_rag_mode_env_variable_propagation`

**Purpose**: Verify RAG_MODE environment variable is passed correctly

**What it tests**:
- `--env RAG_MODE=strict` appears in the container command
- Environment variable propagation works through Ramalama's command factory

## Running the Tests

### In Ramalama Repository

```bash
# Run all RAG mode tests
cd ramalama
pytest test/e2e/test_rag_modes.py -v

# Run specific test
pytest test/e2e/test_rag_modes.py::test_rag_strict_mode -v

# Skip container tests (if needed)
pytest test/e2e/test_rag_modes.py --no-container
```

### Test Markers

The tests use Ramalama's standard markers:
- `@pytest.mark.e2e` - End-to-end test
- `@skip_if_no_container` - Skip if container mode disabled
- `@skip_if_docker` - Skip if using Docker (Podman-specific features)
- `@skip_if_darwin` - Skip on macOS

## Test Pattern

All tests follow Ramalama's established patterns:

1. **Workspace Context**: Uses `RamalamaExecWorkspace()` fixture
2. **Random Container Names**: Avoids conflicts with `random.choices()`
3. **Random Ports**: Prevents port conflicts with `random.randint(64000, 65000)`
4. **Proper Cleanup**: Always stops containers in `finally` blocks
5. **Model Fixture**: Uses `test_model` fixture for consistent test model

## Integration with Henzai

While these tests are in Ramalama's repository, they validate the RAG mode functionality that henzai relies on:

- **henzai** uses `ramalama serve --env RAG_MODE=<mode>`
- **Tests** verify this environment variable is properly handled
- **Coverage** ensures all three modes (strict, hybrid, augment) work as expected

## Additional Henzai-Specific Tests

For henzai-specific RAG functionality, see:
- `tests/test-rag-e2e.py` - End-to-end RAG tests via D-Bus
- `tests/test-rag-reasoning.py` - RAG + Reasoning integration tests

These test henzai's D-Bus layer and UI integration, while the Ramalama tests validate the underlying RAG mode behavior.

## Test Data

Tests create minimal markdown documents for validation:

```markdown
# Document 1: ramalama-info.md
Ramalama is a tool for running AI models using containers.
It supports multiple model formats including GGUF and OCI.
The project was created by the Containers organization.
It uses llama.cpp as the inference backend.

# Document 2: rag-features.md
Ramalama supports three RAG modes:
- strict: Only answers from documents
- hybrid: Prefers documents, falls back to general knowledge
- augment: Combines documents with general knowledge

RAG uses Qdrant for vector storage and embeddings.
```

These are intentionally minimal to:
1. Keep test execution fast
2. Make test failures easy to diagnose
3. Provide clear expected behavior

## CI Integration

These tests will run as part of Ramalama's existing CI pipeline:
- Automatically on PRs
- On merge to main
- Part of the existing `pytest test/e2e/` suite

## Status

✅ **Committed to PR #2180** - Tests are included in the RAG modes PR
✅ **Following Ramalama Patterns** - Uses existing fixtures and markers
✅ **Comprehensive Coverage** - All three modes tested
✅ **Environment Variable Validation** - Ensures proper propagation

## Future Enhancements

Potential additions (not required for current PR):

1. **Performance tests**: Measure RAG query latency
2. **Document relevance tests**: Verify retrieval quality
3. **Streaming tests**: Test RAG with streaming responses
4. **Multi-model tests**: Test RAG with different model types

These can be added later as the RAG feature matures in Ramalama.
