# henzai Architecture

This document describes the system architecture and design decisions.

---

## System Overview

henzai is a two-component system that brings AI assistance to the GNOME desktop:

```
┌─────────────────────────────────────────┐
│         GNOME Shell (JavaScript)        │
│  ┌───────────────────────────────────┐  │
│  │    henzai Extension (GJS/GTK)     │  │
│  │  - Chat Panel UI                  │  │
│  │  - Top Bar Indicator              │  │
│  │  - Keyboard Shortcuts             │  │
│  └────────────┬──────────────────────┘  │
└───────────────┼─────────────────────────┘
                │ D-Bus (Session Bus)
                │
┌───────────────┼─────────────────────────┐
│               ▼                         │
│  ┌───────────────────────────────────┐  │
│  │   henzai Daemon (Python)          │  │
│  │                                   │  │
│  │  ┌─────────────────────────────┐  │  │
│  │  │   D-Bus Service             │  │  │
│  │  │   - Message routing          │  │  │
│  │  │   - Request handling         │  │  │
│  │  └─────────────┬───────────────┘  │  │
│  │                │                   │  │
│  │  ┌─────────────┼───────────────┐  │  │
│  │  │   LLM Client│               │  │  │
│  │  │   - Ramalama interface      │  │  │
│  │  │   - Prompt management        │  │  │
│  │  │   - Tool call parsing        │  │  │
│  │  └─────────────┬───────────────┘  │  │
│  │                │                   │  │
│  │  ┌─────────────┼───────────────┐  │  │
│  │  │   Tool      │  Memory       │  │  │
│  │  │   Executor  │  Store        │  │  │
│  │  │             │  (SQLite)     │  │  │
│  │  └─────────────┴───────────────┘  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
           │              │
           │              └─────────────┐
           ▼                            ▼
    ┌─────────────┐              ┌─────────────┐
    │  System     │              │  Database   │
    │  - Apps     │              │  ~/.local/  │
    │  - Settings │              │  share/     │
    │  - Commands │              │  henzai/    │
    └─────────────┘              └─────────────┘
```

---

## Component Details

### GNOME Shell Extension (Frontend)

**Language**: JavaScript (GJS)  
**Location**: `henzai-extension/`

**Responsibilities**:
1. User interface (chat panel, indicator)
2. Input capture and display
3. D-Bus communication with daemon
4. GNOME Shell integration

**Key Files**:
- `extension.js` - Main extension entry point
- `ui/chatPanel.js` - Chat interface
- `dbus/client.js` - D-Bus client wrapper
- `prefs.js` - Settings UI
- `stylesheet.css` - UI styling

**Lifecycle**:
1. Loaded when GNOME Shell starts (if enabled)
2. `enable()` called to initialize
3. Runs until Shell restart or extension disable
4. `disable()` called for cleanup

---

### Python Daemon (Backend)

**Language**: Python 3.12+  
**Location**: `henzai-daemon/`

**Responsibilities**:
1. D-Bus service hosting
2. LLM inference via Ramalama
3. System action execution
4. Conversation memory management

**Key Modules**:

#### `main.py`
- Entry point
- Service initialization
- Main loop management

#### `dbus_service.py`
- D-Bus interface definition
- Method implementations
- Request routing

#### `llm.py`
- Ramalama subprocess management
- Prompt construction
- Response parsing
- Tool call detection

#### `tools.py`
- System action implementations
- Application launching (Gio.DesktopAppInfo)
- Settings management (gsettings)
- Command execution (subprocess)

#### `memory.py`
- SQLite database interface
- Conversation storage
- Settings persistence
- Action history logging

---

## Communication Protocol

### D-Bus Interface

**Service**: `org.gnome.henzai`  
**Path**: `/org/gnome/henzai`  
**Bus**: Session (user-specific)

**Methods**:

1. **SendMessage(message: string) → response: string**
   - Main interaction method
   - Synchronous (blocks until response ready)
   - Timeout: 60 seconds default

2. **GetStatus() → status: string**
   - Returns daemon state
   - Fast, non-blocking

3. **ClearHistory()**
   - Clears conversation database
   - Fire-and-forget

**Why D-Bus?**
- Native IPC mechanism in GNOME
- Language-agnostic (JS ↔ Python)
- Session bus provides security (user isolation)
- Well-documented and stable
- Service activation support (auto-start)

---

## Data Flow

### User Message Processing

```
1. User types message in chat panel
   │
2. Extension calls SendMessage() via D-Bus
   │
3. Daemon receives message
   │
4. Store user message in SQLite
   │
5. Retrieve conversation context from DB
   │
6. Build prompt with system instructions + context + message
   │
7. Send prompt to Ramalama
   │
8. Parse LLM response for tool calls
   │
9. If tool calls found:
   │   ├─ Execute each tool
   │   ├─ Collect results
   │   └─ Send results back to LLM for final response
   │
10. Store response in SQLite
   │
11. Return response via D-Bus
   │
12. Extension displays response in UI
```

### Tool Execution Flow

```
LLM Response: "I'll launch Firefox for you. <tool_call>{"name": "launch_app", "parameters": {"app_name": "firefox"}}</tool_call>"
   │
Parse with regex: r'<tool_call>(.*?)</tool_call>'
   │
Extract JSON: {"name": "launch_app", "parameters": {"app_name": "firefox"}}
   │
Call ToolExecutor.execute("launch_app", {"app_name": "firefox"})
   │
Execute: Gio.DesktopAppInfo.new("firefox.desktop").launch()
   │
Result: "Launched Firefox"
   │
Build context: "I executed: ✓ launch_app: Launched Firefox"
   │
Send to LLM for natural response
   │
Final response: "I've launched Firefox for you."
```

---

## Data Storage

### SQLite Database

**Location**: `~/.local/share/henzai/memory.db`

**Schema**:

```sql
-- Conversation history
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_message TEXT NOT NULL,
    assistant_response TEXT NOT NULL,
    context_json TEXT
);

-- Settings/preferences
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Action history (for future learning)
CREATE TABLE action_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    action_type TEXT NOT NULL,
    parameters TEXT,
    outcome TEXT,
    success BOOLEAN
);
```

**Purpose**:
- Persistent conversation memory
- User preferences
- Action logging for future ML
- Session continuity

---

## LLM Integration

### Ramalama

**Interface**: Subprocess call  
**Models**: Any Ramalama-supported model (llama3.2, etc.)

**Call Pattern**:

```python
subprocess.run([
    'ramalama', 
    'run', 
    model_name,
    '--prompt', 
    full_prompt
], capture_output=True, text=True, timeout=60)
```

**Advantages**:
- Simple integration (no complex API)
- Model agnostic
- Local execution (privacy)
- No rate limits or costs

**Disadvantages**:
- No streaming (for MVP)
- Process overhead per call
- Limited to Ramalama capabilities

**Future**: Add Claude API support as alternative backend

---

## System Permissions

### Required Permissions

1. **D-Bus Session Bus**: Extension and daemon both need access
2. **GSettings**: For system setting changes
3. **Application Launching**: Via Gio.DesktopAppInfo
4. **File System**: 
   - Read: `/etc/os-release`, `/proc/*`
   - Write: `~/.local/share/henzai/`

### Security Model

**Sandboxing**: None (user-level permissions)  
**Rationale**: System assistant needs broad permissions to be useful

**Safety Measures**:
- Dangerous command blocking (rm -rf, mkfs, etc.)
- Command timeout (10 seconds)
- User session isolation (D-Bus session bus)
- No root privilege escalation

**Future**: Add user confirmation for sensitive operations

---

## Error Handling

### Extension (UI)

- Connection errors: Show "Daemon offline" message
- Timeout errors: Show "Request timed out"
- Display all errors in chat for user visibility

### Daemon (Backend)

- Log all errors to journal
- Return user-friendly error messages
- Never crash (catch all exceptions)
- Auto-reconnect on D-Bus issues

### Logging

**Extension**: Console output (accessible via Looking Glass: Alt+F2, 'lg')  
**Daemon**: Systemd journal

```bash
# View daemon logs
journalctl --user -u henzai-daemon -f

# View GNOME Shell logs (includes extension)
journalctl -f /usr/bin/gnome-shell
```

---

## Performance Considerations

### Latency

**Target**: < 2 seconds for simple queries

**Breakdown**:
- D-Bus call: < 10ms
- Database query: < 10ms
- LLM inference: 1-5 seconds (depends on model/hardware)
- Tool execution: varies (app launch ~500ms, settings ~100ms)

**Bottleneck**: LLM inference time

**Optimization Strategies**:
- Use smaller/faster models for simple tasks
- Cache common responses (future)
- Parallel tool execution (future)

### Memory

**Extension**: ~2-5 MB (minimal UI)  
**Daemon**: ~50-200 MB (depends on LLM model size in memory)  
**Database**: ~1 MB per 1000 conversations

---

## Extension Points

### For Future Development

1. **Custom Tools**: Add new tool modules to `tools.py`
2. **Alternative LLMs**: Swap `llm.py` implementation
3. **UI Themes**: Modify `stylesheet.css`
4. **Additional Interfaces**: New D-Bus methods
5. **Plugins**: Load external Python modules for tools

---

## Design Decisions

### Why Two Separate Components?

**Problem**: GNOME Shell extensions run in Shell's JavaScript process

**Implications**:
- Can't easily run Python ML code
- Memory/CPU intensive operations affect Shell performance
- Crashes can take down entire Shell
- Limited library ecosystem

**Solution**: Separate daemon process

**Benefits**:
- Isolate heavy computation
- Restart daemon without restarting Shell
- Use Python's rich ecosystem
- Better error isolation

### Why SQLite Over Flat Files?

- Structured queries (find conversations by date, content, etc.)
- Concurrent access safety
- Efficient indexing for future semantic search
- Transaction support
- Familiar tooling for inspection/backup

### Why D-Bus Over REST/WebSockets?

- Native to GNOME ecosystem
- Lower overhead than HTTP
- Built-in security (session bus)
- Service activation (auto-start)
- No port conflicts
- Type-safe interfaces

---

## Testing Strategy

### Unit Tests

**Python Daemon**:
```bash
cd henzai-daemon
pytest tests/
```

**Coverage**:
- Tool execution
- Memory operations
- LLM prompt building
- D-Bus method logic

### Integration Tests

**D-Bus Communication**:
- Extension ↔ Daemon messaging
- Error propagation
- Timeout handling

### Manual Testing

**UI/UX**:
- Chat panel behavior
- Keyboard shortcuts
- Visual styling
- Error display

**System Actions**:
- Launch various apps
- Adjust different settings
- Execute safe commands
- Verify results

---

## Deployment

### Installation Process

1. Install Python package (daemon)
2. Install systemd service
3. Enable and start service
4. Copy extension files
5. Compile GSettings schema
6. Enable extension
7. Restart GNOME Shell

### Updates

**Daemon**: 
```bash
cd henzai-daemon
pip install --user -e . --upgrade
systemctl --user restart henzai-daemon
```

**Extension**:
- Copy new files
- Restart GNOME Shell (or log out/in)

---

## Future Architecture Changes

### Phase 2: Streaming Responses

Add SignalR or similar for streaming LLM output to UI in real-time.

### Phase 3: Multi-Agent System

```
                  ┌─────────────┐
                  │ Coordinator │
                  │   Agent     │
                  └──────┬──────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼────┐     ┌────▼────┐    ┌─────▼─────┐
   │  Email  │     │  Code   │    │  Visual   │
   │  Agent  │     │  Agent  │    │  Agent    │
   └─────────┘     └─────────┘    └───────────┘
```

### Phase 4: Vector Memory

Replace/augment SQLite with Chroma for semantic search:
- "What did I ask about yesterday?"
- Context-aware suggestions
- Long-term learning

---

This architecture provides a solid foundation for the MVP while remaining flexible for future enhancements.










