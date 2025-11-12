# henzai Testing Guide

## Overview

The henzai daemon uses pytest for comprehensive testing of the streaming functionality. Tests focus on business logic rather than implementation details.

## Running Tests

### Quick Start

```bash
cd henzai-daemon
./run-tests.sh
```

### With Coverage

```bash
python -m pytest tests/ --cov=henzai --cov-report=term-missing
```

### Specific Test File

```bash
python -m pytest tests/test_llm_streaming.py -v
```

### With Detailed Output

```bash
python -m pytest tests/ -vv --tb=long
```

## Test Structure

```
tests/
├── __init__.py
├── test_llm_streaming.py      # LLM streaming functionality (15 tests)
└── test_dbus_streaming.py     # D-Bus service logic (14 tests)
```

## Test Coverage

### LLM Streaming Tests (`test_llm_streaming.py`)

**Coverage**: ~55% of llm.py (focused on streaming methods)

Tests cover:
- ✅ Streaming API call with SSE parsing
- ✅ Chunk callbacks and accumulation
- ✅ Empty content handling
- ✅ Invalid JSON handling in stream
- ✅ API errors (500, connection, timeout)
- ✅ Stop generation with active request
- ✅ Error handling in stop generation
- ✅ Request tracking (_current_request)
- ✅ Multiline responses
- ✅ Context inclusion in streaming

**Key Test Patterns:**

```python
@patch('henzai.llm.requests.post')
def test_streaming_api_call_success(mock_post, llm_client):
    # Mock SSE stream
    sse_data = [
        b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n',
        b'data: [DONE]\n',
    ]
    mock_response.iter_lines.return_value = sse_data
    
    # Test streaming with callback
    chunks = []
    result = llm_client._call_ramalama_api_streaming(
        messages, 
        lambda c: chunks.append(c)
    )
    
    assert result == "Hello"
    assert chunks == ["Hello"]
```

### D-Bus Service Tests (`test_dbus_streaming.py`)

**Coverage**: ~65% of dbus_service.py (focused on streaming logic)

Tests cover:
- ✅ Service initialization with stop flag
- ✅ LLM call with correct parameters
- ✅ Status transitions (ready → thinking → ready)
- ✅ Context passing to LLM
- ✅ Error handling and status updates
- ✅ Tool call integration
- ✅ Stop generation flag behavior
- ✅ Memory storage of responses
- ✅ Empty response handling
- ✅ Error recovery

**Note**: Tests focus on business logic rather than D-Bus signal emission, as dasbus signals are difficult to mock properly.

**Key Test Patterns:**

```python
def test_send_message_streaming_calls_llm(dbus_service, mock_llm):
    mock_llm.generate_response_streaming.return_value = "Response"
    
    result = dbus_service.SendMessageStreaming("Test message")
    
    assert result == "OK"
    assert mock_llm.generate_response_streaming.called
    call_args = mock_llm.generate_response_streaming.call_args
    assert call_args[0][0] == "Test message"  # message
    assert callable(call_args[1]['chunk_callback'])  # callback
```

## Writing New Tests

### Fixtures

- `llm_client`: Mocked LLM client instance
- `mock_llm`: Mock for dependency injection
- `mock_memory`: Mock memory store
- `dbus_service`: Configured D-Bus service instance

### Mocking Strategies

**For HTTP Requests:**
```python
@patch('henzai.llm.requests.post')
def test_something(mock_post, llm_client):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response
```

**For Streaming Responses:**
```python
def mock_generate_streaming(message, context, chunk_callback):
    chunk_callback("chunk1")
    chunk_callback("chunk2")
    return "chunk1chunk2"

mock_llm.generate_response_streaming.side_effect = mock_generate_streaming
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run tests
  run: |
    cd henzai-daemon
    pip install -r requirements-test.txt
    python -m pytest tests/ --cov=henzai --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./henzai-daemon/coverage.xml
```

## Test Dependencies

See `requirements-test.txt`:
- pytest>=7.4.0
- pytest-asyncio>=0.21.0
- pytest-mock>=3.11.1
- pytest-cov>=4.1.0
- responses>=0.23.0

## Limitations

### What's NOT Tested

1. **D-Bus Signal Emission**: dasbus signals are tested for logic only, not actual emission
2. **Ramalama Process**: No actual Ramalama server is started
3. **Database Operations**: memory.py is not yet covered
4. **Tool Execution**: tools.py has minimal coverage
5. **Main Entry Point**: main.py is not tested

### Why These Limitations?

- **D-Bus signals**: Require actual D-Bus daemon, complex to mock
- **External processes**: Ramalama would slow tests significantly
- **Database**: Requires setup/teardown, planned for future
- **Integration**: Full E2E tests should be separate

## Future Improvements

1. **Integration Tests**: Test with real Ramalama instance
2. **Database Tests**: Add memory.py coverage
3. **Tool Tests**: Expand tools.py testing
4. **Performance Tests**: Benchmark streaming speed
5. **Load Tests**: Test concurrent streams

## Debugging Tests

### Run Single Test

```bash
python -m pytest tests/test_llm_streaming.py::TestLLMStreaming::test_streaming_api_call_success -v
```

### With Print Statements

```bash
python -m pytest tests/ -s  # Shows print() output
```

### With PDB on Failure

```bash
python -m pytest tests/ --pdb
```

## Test Results Summary

```
29 tests total
=============================
✅ All tests passing
📊 33% overall coverage
📊 55% llm.py coverage (streaming methods)
📊 65% dbus_service.py coverage (streaming logic)
⏱️  Test suite runs in ~0.3 seconds
```

## Success Criteria

Before merging streaming features:
- ✅ All tests pass
- ✅ >50% coverage on new streaming code
- ✅ Error cases handled
- ✅ Stop generation works
- ✅ Context preservation verified

---

**Note**: These tests follow TDD principles - written alongside the streaming implementation to ensure correctness before deployment.

