# Integration Tests

End-to-end and integration tests for henzai.

## Test Scripts

### D-Bus Tests
- `test-streaming.py` - Test streaming responses
- `test-model-switch.py` - Test model switching
- `test-newchat.py` - Test new chat functionality
- `test-history.py` - Test chat history/sessions
- `test-models.py` - Test model listing
- `test-reasoning.py` - Test reasoning mode

### Ramalama API Tests
- `test-api-thinking.sh` - Test Ramalama thinking parameter
- `test-deepseek-direct.sh` - Direct DeepSeek API test
- `test-complex-question.sh` - Complex reasoning test

### Reasoning Model Tests
- `test-deepseek-reasoning.sh` - DeepSeek-R1 reasoning test
- `test-deepseek-14b-reasoning.sh` - DeepSeek-R1 14B reasoning test
- `test-deepseek-14b-system.sh` - DeepSeek-R1 14B system prompt test
- `test-qwq-reasoning.sh` - QwQ-32B reasoning test
- `test-thinking-mode.sh` - Generic thinking mode test
- `test-streaming-reasoning.sh` - Streaming with reasoning test

## Running Tests

```bash
# Run Python D-Bus tests
cd /path/to/henzai
./tests/test-streaming.py

# Run shell API tests
./tests/test-deepseek-reasoning.sh

# Run all Python tests
cd henzai-daemon
./run-tests.sh
```

## Prerequisites

- henzai daemon running (`systemctl --user status henzai`)
- Ramalama service running (`systemctl --user status ramalama`)
- For reasoning tests: Reasoning-capable model loaded (DeepSeek-R1, QwQ-32B)

## Test Categories

### Unit Tests
Located in `henzai-daemon/tests/` - test individual components.

### Integration Tests
Located in `tests/` (this folder) - test D-Bus communication and E2E flows.

### UI Tests
Use `dev/dev-test.sh` for manual UI testing in nested shell.
