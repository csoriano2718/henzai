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

Tests create realistic private company documents to properly test RAG behavior:

### Document 1: `meeting-2025-11-15.md` (Fictional Company Meeting)
- **Purpose**: Tests retrieval of private, non-public information
- **Content**: Engineering team meeting with specific attendees (Sarah Chen, Marcus Rivera, Priya Sharma, James Wilson)
- **Private data points**:
  - Project Nebula launch date: December 3, 2025
  - Budget approval: $12,000 for monitoring tools
  - Performance metrics: 340ms API improvement, 45% database load reduction
  - Container discussion: Podman vs Docker evaluation
- **Why this works**: Completely fictional names and dates ensure no public knowledge interference

### Document 2: `product-specs.md` (Fictional Product Documentation)
- **Purpose**: Tests combination of private specifics with public technical terms
- **Content**: CloudSync Pro v3.0 specifications with internal metrics
- **Private data points**:
  - MRR: $847,000 (specific company metric)
  - Customer count: 12,450 accounts
  - API rate limits: 1,000/10,000/custom tiers
  - Pricing: $0/$29/$500+ per month
- **Public technical terms** (for hybrid/augment mode testing):
  - WebSocket protocol (general knowledge available)
  - AES-256-GCM encryption (public cryptography standard)
  - PostgreSQL 16 (public database software)
- **Why this works**: Mix of private metrics with public tech terms tests mode boundaries

### Document 3: `team-directory.md` (Fictional Employee Directory)
- **Purpose**: Tests retrieval of specific person/role information
- **Content**: Employee directory with fictional people and extensions
- **Private data points**:
  - Employee names and roles (Marcus Rivera - Backend Lead, etc.)
  - Internal extensions: 4521, 4523, 4525, 4527, 4530
  - Office locations: Austin HQ, Portland satellite
  - Specializations and join dates
- **Why this works**: Tests specific person lookups that should only come from documents

### Test Query Design

**Strict Mode Queries**:
- ✅ "When is the Project Nebula launch date?" → Should answer "December 3, 2025"
- ✅ "Who attended the November 15 meeting?" → Should list attendees
- ❌ "What is the speed of light?" → Should refuse (not in documents)

**Hybrid Mode Queries**:
- ✅ "What is Sarah Chen's role?" → Should use documents ("Engineering Manager")
- ✅ "What is WebSocket and how does CloudSync Pro use it?" → Can combine docs + general knowledge
- ✅ "What programming language is used for Linux kernel development?" → Can answer from general knowledge

**Augment Mode Queries**:
- ✅ "What is the MRR for CloudSync Pro?" → Should use documents ("$847,000")
- ✅ "What is AES-256 encryption and is it secure?" → Can freely combine
- ✅ "What is the difference between Docker and Podman?" → Can answer (note: both mentioned in meeting)

### Design Rationale

1. **Realistic Private Data**: Uses fictional company meeting notes instead of generic tech docs
2. **Specific Testable Values**: Dates, dollar amounts, names are easy to verify in responses
3. **Public/Private Mix**: Product specs mix private metrics with public tech terms for hybrid testing
4. **No Public Knowledge Overlap**: Fictional names/dates ensure tests aren't accidentally passing due to public data
5. **Environment Independent**: Tests work on any system without external dependencies

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
