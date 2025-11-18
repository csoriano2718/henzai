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

Get the current status of the daemon and Ramalama service.

**Signature**: `GetStatus() → status_json: string`

**Returns**:
- `status_json` (string): JSON object with system status:
  - `daemon_status` (string): Daemon state - `"ready"`, `"thinking"`, `"error"`, `"initializing"`
  - `ramalama_status` (string): Ramalama state - `"ready"`, `"loading"`, `"not_started"`, `"not_installed"`, `"error"`
  - `ramalama_message` (string): Human-readable status message
  - `ready` (boolean): True only when both daemon and Ramalama are ready

**Example (busctl)**:
```bash
busctl --user call org.gnome.henzai /org/gnome/henzai org.gnome.henzai GetStatus
# s '{"daemon_status":"ready","ramalama_status":"ready","ramalama_message":"Model loaded and ready","ready":true}'
```

**Status Values**:
- **ramalama_status**:
  - `"ready"` - Model loaded, API responding, ready for queries
  - `"loading"` - Service active or activating, model loading into memory
  - `"not_started"` - Service exists but not running
  - `"not_installed"` - Ramalama not installed
  - `"error"` - Service failed or API error

**UI Integration**:
- Poll this method at 1-second intervals while system is not ready
- Disable input/send UI elements when `ready === false`
- Show `ramalama_message` to user while loading
- Stop polling when `ready === true`

---

### ClearHistory

Clear all conversation history from the database.

**Signature**: `ClearHistory() → void`

**Example (busctl)**:
```bash
busctl --user call org.gnome.henzai /org/gnome/henzai org.gnome.henzai ClearHistory
```

---

### SetRAGConfig

Configure and index RAG (Retrieval-Augmented Generation) documents.

**Signature**: `SetRAGConfig(folder_path: string, format: string, enable_ocr: boolean) → success: boolean`

**Parameters**:
- `folder_path` (string): Path to documents folder
- `format` (string): Vector database format (`qdrant`, `json`, `markdown`, `milvus`)
- `enable_ocr` (boolean): Enable OCR for PDFs with images

**Returns**:
- `success` (boolean): True if indexing started successfully

**Example (busctl)**:
```bash
busctl --user call org.gnome.henzai /org/gnome/henzai org.gnome.henzai SetRAGConfig sss "/home/user/Documents" "qdrant" false
```

**Notes**:
- Indexing happens in background
- Progress updates via `RAGIndexing*` signals
- Supported formats: PDF, DOCX, PPTX, XLSX, HTML, Markdown, AsciiDoc, TXT

---

### SetRagEnabled

Enable or disable RAG mode with optional mode selection.

**Signature**: `SetRagEnabled(enabled: boolean, mode: string) → result_json: string`

**Parameters**:
- `enabled` (boolean): True to enable RAG, False to disable
- `mode` (string): RAG mode - `"augment"` (docs + knowledge), `"strict"` (docs only), or `"hybrid"` (docs preferred). Default: `"augment"`

**Returns**:
- `result_json` (string): JSON string with success status and message

**Example JSON Response**:
```json
{
    "success": true,
    "message": "RAG enabled successfully (mode: augment)"
}
```

**Example (busctl)**:
```bash
# Enable RAG with augment mode (default)
busctl --user call org.gnome.henzai /org/gnome/henzai org.gnome.henzai SetRagEnabled bs true "augment"

# Enable RAG with strict mode (docs only)
busctl --user call org.gnome.henzai /org/gnome/henzai org.gnome.henzai SetRagEnabled bs true "strict"

# Disable RAG
busctl --user call org.gnome.henzai /org/gnome/henzai org.gnome.henzai SetRagEnabled bs false "augment"
```

**RAG Modes**:
- **augment** (default): AI uses both indexed documents AND general knowledge. Documents provide context, but AI can supplement with general knowledge when needed.
- **strict**: AI answers ONLY from indexed documents. If answer not in docs, responds with "I don't know". Good for compliance/legal use cases.
- **hybrid**: AI prioritizes indexed documents but may supplement with general knowledge. Indicates when using general knowledge.

**Notes**:
- Requires RAG database to exist (index documents first with SetRAGConfig)
- Restarts ramalama service with new configuration
- Mode change takes effect immediately (service restart)

---

### DisableRAG

Disable RAG and clear the index.

**Signature**: `DisableRAG() → success: boolean`

**Returns**:
- `success` (boolean): True if disabled successfully

**Example (busctl)**:
```bash
busctl --user call org.gnome.henzai /org/gnome/henzai org.gnome.henzai DisableRAG
```

---

### GetRAGStatus

Get current RAG status.

**Signature**: `GetRAGStatus(source_path: string, rag_enabled: boolean) → status_json: string`

**Parameters**:
- `source_path` (string): Configured source path
- `rag_enabled` (boolean): Whether RAG is enabled in settings

**Returns**:
- `status_json` (string): JSON string with RAG status

**Status JSON Structure**:
```json
{
    "enabled": true,
    "indexed": true,
    "file_count": 150,
    "last_indexed": "2025-11-14T10:30:00Z",
    "format": "qdrant",
    "db_path": "/home/user/.local/share/henzai/rag-db",
    "source_path": "/home/user/Documents",
    "ocr_enabled": false,
    "error": null
}
```

**Example (busctl)**:
```bash
busctl --user call org.gnome.henzai /org/gnome/henzai org.gnome.henzai GetRAGStatus sb "/home/user/Documents" true
```

---

### ReindexRAG

Trigger RAG reindexing with current configuration.

**Signature**: `ReindexRAG() → success: boolean`

**Returns**:
- `success` (boolean): True if reindexing started

**Example (busctl)**:
```bash
busctl --user call org.gnome.henzai /org/gnome/henzai org.gnome.henzai ReindexRAG
```

**Notes**:
- Uses existing configuration from previous indexing
- Fails if no existing configuration found

---

## Signals

### RAGIndexingStarted

Emitted when RAG indexing starts.

**Signature**: `RAGIndexingStarted(message: string)`

**Parameters**:
- `message` (string): Status message (e.g., "Indexing documents from /path")

---

### RAGIndexingProgress

Emitted during RAG indexing to report progress.

**Signature**: `RAGIndexingProgress(message: string, percent: int32)`

**Parameters**:
- `message` (string): Progress message
- `percent` (int32): Completion percentage (0-100)

---

### RAGIndexingComplete

Emitted when RAG indexing completes successfully.

**Signature**: `RAGIndexingComplete(message: string, file_count: int32)`

**Parameters**:
- `message` (string): Completion message
- `file_count` (int32): Number of files indexed

---

### RAGIndexingFailed

Emitted when RAG indexing fails.

**Signature**: `RAGIndexingFailed(error: string)`

**Parameters**:
- `error` (string): Error message

---

## Legacy Signals

Currently no other signals are emitted. Future versions may add:
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










