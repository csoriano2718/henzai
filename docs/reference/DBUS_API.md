# henzai D-Bus API Reference

This document describes the D-Bus interface for henzai daemon communication.

---

## Service Information

- **Service Name**: `org.gnome.henzai`
- **Object Path**: `/org/gnome/henzai`
- **Interface**: `org.gnome.henzai`
- **Bus**: Session bus

---

## Methods

### SendMessage

Send a message to the AI assistant and receive a response.

**Signature**: `SendMessage(message: string) → response: string`

**Parameters**:
- `message` (string): User's input message

**Returns**:
- `response` (string): AI assistant's response

**Example (busctl)**:
```bash
busctl --user call org.gnome.henzai /org/gnome/henzai org.gnome.henzai SendMessage s "Hello, can you help me?"
```

**Example (JavaScript)**:
```javascript
const [response] = await proxy.SendMessageAsync("open firefox");
console.log(response);
```

**Example (Python)**:
```python
from dasbus.connection import SessionMessageBus

bus = SessionMessageBus()
proxy = bus.get_proxy("org.gnome.henzai", "/org/gnome/henzai")
response = proxy.SendMessage("enable dark mode")
print(response)
```

---

### GetStatus

Get the current status of the daemon.

**Signature**: `GetStatus() → status: string`

**Returns**:
- `status` (string): Current daemon status
  - `"ready"` - Ready to process messages
  - `"thinking"` - Currently processing a message
  - `"error"` - Error state
  - `"initializing"` - Starting up

**Example (busctl)**:
```bash
busctl --user call org.gnome.henzai /org/gnome/henzai org.gnome.henzai GetStatus
```

---

### ClearHistory

Clear all conversation history from the database.

**Signature**: `ClearHistory() → void`

**Example (busctl)**:
```bash
busctl --user call org.gnome.henzai /org/gnome/henzai org.gnome.henzai ClearHistory
```

---

## Signals

Currently no signals are emitted. Future versions may add:
- `ThinkingStatusChanged(is_thinking: boolean)` - Status change notifications
- `ErrorOccurred(error: string)` - Error notifications

---

## Error Handling

Methods may raise D-Bus errors with the following error names:

- `org.gnome.henzai.Error.LLM` - LLM processing error
- `org.gnome.henzai.Error.Tool` - Tool execution error
- `org.gnome.henzai.Error.Memory` - Database/memory error

---

## Tool Call Format

When the LLM needs to execute an action, it returns tool calls in the response using this format:

```
<tool_call>{"name": "tool_name", "parameters": {"param": "value"}}</tool_call>
```

The daemon automatically detects and executes these tool calls before returning the final response to the user.

**Available Tools**:
- `launch_app` - Launch applications
- `adjust_setting` - Change GNOME settings
- `execute_command` - Execute shell commands
- `get_system_info` - Get system information

See `TOOLS.md` for detailed tool documentation.

---

## Testing the Interface

### Using d-feet (GUI)

1. Install d-feet: `sudo dnf install d-feet`
2. Launch d-feet
3. Select "Session Bus"
4. Find `org.gnome.henzai`
5. Browse methods and test them interactively

### Using busctl (CLI)

```bash
# List all methods
busctl --user introspect org.gnome.henzai /org/gnome/henzai

# Monitor all messages
busctl --user monitor org.gnome.henzai

# Call a method
busctl --user call org.gnome.henzai /org/gnome/henzai org.gnome.henzai GetStatus
```

---

## Implementation Notes

### Thread Safety

The daemon uses GLib's main loop for D-Bus message handling. All methods are processed sequentially in the main thread, ensuring thread safety.

### Timeout

Methods have a default 60-second timeout. Long-running operations (complex LLM queries) may timeout - consider increasing client-side timeout if needed.

### Authentication

No authentication is required as this is a session bus service (user-specific). Only the logged-in user can access the service.

---

## Future API Extensions

Planned additions for future versions:

1. **Streaming responses**: 
   - `SendMessageStream(message: string) → stream<chunk: string>`
   
2. **Context management**:
   - `SetContext(context: json) → void`
   - `GetContext() → context: json`

3. **Tool registration**:
   - `RegisterTool(definition: json) → void`
   - Allow third-party tools

4. **Session management**:
   - `CreateSession(name: string) → session_id: string`
   - `SwitchSession(session_id: string) → void`
   - Multiple conversation sessions

---

## Troubleshooting

### Service not found

```bash
# Check if daemon is running
systemctl --user status henzai-daemon

# Check D-Bus registration
busctl --user list | grep henzai
```

### Method call fails

```bash
# Check daemon logs
journalctl --user -u henzai-daemon -n 50

# Test with busctl
busctl --user call org.gnome.henzai /org/gnome/henzai org.gnome.henzai GetStatus
```

### Permission denied

Ensure the daemon is running under your user session:
```bash
systemctl --user restart henzai-daemon
```










