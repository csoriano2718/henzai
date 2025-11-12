# Contributing to henzai

First off, thank you for considering contributing to henzai! It's people like you that make henzai such a great tool.

## Code of Conduct

This project and everyone participating in it is governed by respect, professionalism, and kindness. By participating, you are expected to uphold this standard.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples**
- **Describe the behavior you observed and what you expected**
- **Include screenshots if applicable**
- **Include your environment** (OS version, GNOME Shell version, Python version)
- **Include logs** from `journalctl --user -u henzai-daemon` and GNOME Shell logs

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub/GitLab issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide a detailed description of the suggested enhancement**
- **Explain why this enhancement would be useful**
- **List examples of how it would be used**

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following the code style guidelines below
3. **Test your changes** thoroughly
4. **Update documentation** if needed
5. **Write clear commit messages** following conventional commits format
6. **Submit a pull request** with a clear description of what you've changed

## Development Setup

### Prerequisites

- Fedora Linux (or compatible distribution)
- GNOME Shell 47+
- Python 3.10+
- Ramalama

### Setting Up Your Environment

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/henzai.git
cd henzai

# Install in development mode
pip3 install --user -e ./henzai-daemon

# Run tests
cd henzai-daemon
./run-tests.sh

# Test in nested GNOME Shell
cd ..
./dev-test.sh
```

## Code Style Guidelines

### Python (Daemon)

- Follow **PEP 8** style guide
- Use **type hints** for function signatures
- Write **docstrings** for all public functions and classes
- Keep functions **focused and small**
- Use **descriptive variable names**
- Add **logging** for important operations

Example:

```python
def process_message(message: str, context: List[Dict[str, str]] = None) -> str:
    """
    Process a user message and generate a response.
    
    Args:
        message: The user's input message
        context: Optional conversation context
        
    Returns:
        The generated response text
    """
    logger.info(f"Processing message: {message[:50]}...")
    # Implementation
```

### JavaScript (Extension)

- Follow **GNOME JavaScript** style guide
- Use **camelCase** for variables and functions
- Use **PascalCase** for classes
- Add **JSDoc comments** for public methods
- Use **const** over **let** where possible
- Prefer **arrow functions** for callbacks

Example:

```javascript
/**
 * Send a message to the daemon and handle streaming response.
 * @param {string} text - The message text to send
 * @returns {Promise<void>}
 */
async _sendMessage(text) {
    console.log(`henzai: Sending message: ${text.substring(0, 50)}...`);
    // Implementation
}
```

### Git Commit Messages

Follow **Conventional Commits** format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that don't affect code meaning (formatting, etc.)
- **refactor**: Code change that neither fixes a bug nor adds a feature
- **perf**: Performance improvements
- **test**: Adding or updating tests
- **chore**: Changes to build process or auxiliary tools

Examples:

```
feat(ui): add reasoning mode visualization

Implement expandable reasoning section that shows the AI's
thought process for reasoning-capable models like DeepSeek-R1.

Closes #42
```

```
fix(daemon): prevent memory leak in streaming responses

Clear the current_request reference after streaming completes
to allow garbage collection.
```

## Testing

### Running Tests

```bash
# Python tests
cd henzai-daemon
pytest

# With coverage
pytest --cov=henzai --cov-report=html

# D-Bus integration tests
python3 test-streaming.py
python3 test-model-switch.py
```

### Writing Tests

- Write tests for all new features
- Ensure existing tests pass
- Aim for >80% code coverage
- Use descriptive test names

Example:

```python
def test_streaming_response_with_reasoning():
    """Test that streaming responses correctly handle reasoning content."""
    # Arrange
    llm = LLMClient(reasoning_enabled=True)
    
    # Act
    chunks = list(llm.call_streaming("Test query"))
    
    # Assert
    assert len(chunks) > 0
    assert any('<think>' in chunk for chunk in chunks)
```

## Documentation

- Update **README.md** if you change functionality
- Update **inline comments** for complex code
- Add **JSDoc/docstrings** for all public APIs
- Update **docs/** for architectural changes

## Questions?

Feel free to:
- Open an issue with the question label
- Reach out on the GNOME Discourse
- Email: csoriano1618@gmail.com

## Thank You!

Your contributions to open source make projects like henzai possible. We appreciate your effort and look forward to your contributions! 🎉

