# henzai - Technical Quick Reference

**Version**: v177 | **For**: AI Agents  
**Primary Rules**: See `../AGENTS.md` in project root

---

## Quick Commands
```bash
# Backend development
systemctl --user restart henzai-daemon.service
journalctl --user -u henzai-daemon.service -f

# UI development  
./dev/dev-ui.sh                    # Fast: UI only (no daemon)
./dev/dev-test.sh                  # Complete: UI + daemon (FULL TESTING)
./dev/cleanup-nested.sh            # Kill orphaned nested shells

# Testing
python3 tests/test-streaming.py    # Verify streaming works
python3 tests/test-newchat.py      # Verify new chat works
python3 tests/test-models.py       # Verify model selection works
python3 tests/test-history.py      # Verify chat history works
```

## Architecture
```
Extension (GJS) ←→ D-Bus ←→ Daemon (Python) ←→ Ramalama API (http://127.0.0.1:8080)
     │                            │
     └─ UI in nested shell       └─ systemd user service
```

**Critical**: Use `127.0.0.1` not `localhost` (IPv6 issues with pasta/Podman)

## Current Features

### Streaming Responses
- **How**: SSE from Ramalama → D-Bus signals → Real-time UI updates
- **Signal**: `ResponseChunk(chunk)` emitted per text piece
- **Frontend**: `chatPanel.js` appends chunks to St.Label
- **Backend**: `llm.py` parses SSE, filters `null` content

### Reasoning Mode
- **Detection**: Auto-enabled for deepseek-r1, qwq models
- **UI**: Purple collapsible "thinking" box
- **Signal**: `ThinkingChunk(chunk)` for reasoning stream
- **Toggle**: Brain icon in UI, `SetReasoningEnabled()` method

### Real-time Synchronization
- **Model Changes**: `ModelChanged(model_id)` signal updates UI instantly
- **Reasoning Toggle**: `ReasoningChanged(enabled)` signal syncs brain icon
- **History Clear**: `HistoryCleared()` signal clears UI messages
- **Panel Position**: GSettings `changed::panel-position` updates layout

### Stop Generation
- **UI**: Red "Stop" button during generation
- **Logic**: Calls `StopGeneration()` D-Bus method
- **Backend**: Sets `_stop_generation` flag, closes HTTP request

### New Chat
- **UI**: ➕ button in header
- **Action**: Clears UI + calls `NewConversation()` D-Bus method
- **Backend**: Saves current session, starts fresh

### Model Selection
- **UI**: Settings dropdown with available models
- **Refresh**: Button to reload model list from Ramalama
- **Backend**: Queries `/v1/models` API
- **D-Bus Methods**: `ListModels()`, `SetModel(id)`, `GetCurrentModel()`

### Chat History/Sessions
- **UI**: 📂 History button → Dropdown menu
- **Features**: List saved chats, load previous sessions, auto-save
- **DB**: SQLite with `sessions` and `conversations` tables
- **D-Bus Methods**: `ListSessions(limit)`, `LoadSession(id)`, `DeleteSession(id)`

### Custom Scrollable Input
- Dynamic height (1 line → max 4-5 lines → scrollable)
- Floating scrollbar with fade-out
- Manual keyboard handling (Clutter.Text)
- Text selection, cursor, clipboard support

## Critical Files

### Backend (Python)
- `henzai-daemon/henzai/dbus_service.py` - D-Bus interface, methods, signals
- `henzai-daemon/henzai/llm.py` - Ramalama API client, SSE parsing, model listing
- `henzai-daemon/henzai/memory.py` - Session & conversation storage (SQLite)
- `henzai-daemon/henzai/tools.py` - Tool execution (launch apps, settings)

### Frontend (GJS)
- `henzai-extension/extension.js` - Entry point, panel button
- `henzai-extension/ui/chatPanel.js` - Main chat UI, message handling
- `henzai-extension/ui/scrollableTextInput.js` - Custom input widget
- `henzai-extension/dbus/client.js` - D-Bus proxy wrapper
- `henzai-extension/prefs.js` - Settings UI with model selection dropdown
- `henzai-extension/stylesheet.css` - All styling

### Dev Scripts
- `dev/dev-ui.sh` - Fast: Nested shell only (UI testing, no backend)
- `dev/dev-test.sh` - Complete: Nested shell + daemon (FULL E2E TESTING)
- `dev/cleanup-nested.sh` - Kill orphaned processes

## D-Bus Interface

### Methods
```python
SendMessage(message: str) → response: str          # Blocking, deprecated
SendMessageStreaming(message: str) → status: str   # Async, use this
StopGeneration() → success: bool                    # Cancel current generation
NewConversation() → status: str                     # Save current, start fresh
GetStatus() → status_json: str                      # {"daemon_status": "ready", "ramalama_status": "ready", "ready": true}
ClearHistory()                                      # Legacy clear method
ListModels() → models_json: str                     # Get available Ramalama models
SetModel(model_id: str) → status: str               # Switch to different model
GetCurrentModel() → model_id: str                   # Get active model
ListSessions(limit: int) → sessions_json: str       # List saved chats
LoadSession(session_id: int) → context_json: str    # Load previous chat
DeleteSession(session_id: int) → status: str        # Delete saved chat
SetReasoningEnabled(enabled: bool) → status: str    # Toggle reasoning mode
GetReasoningEnabled() → enabled: bool               # Get reasoning state
SupportsReasoning() → supported: bool               # Check if current model supports reasoning
```

### Signals
```python
ResponseChunk(chunk: str)      # Emitted during streaming generation
ThinkingChunk(chunk: str)      # Emitted during reasoning (if supported)
StreamingComplete()            # Emitted when streaming finishes
ModelChanged(model_id: str)    # Emitted when model is switched
ReasoningChanged(enabled: bool) # Emitted when reasoning mode changes
HistoryCleared()               # Emitted when history is cleared
```

## Known Issues & Gotchas

### Wayland Session Management (CRITICAL)
- **NEVER** run `pkill gnome-shell` or `gnome-shell --replace` in main session
- Kills entire Wayland session = forced logout (no recovery)
- **ALWAYS** use nested shell for UI testing
- Backend-only changes: Safe to test in main session with `systemctl --user restart`

### Ramalama
- **Health check**: `/health` endpoint returns `{"status":"ok"}` when ready
- **IPv6 issue**: Use `http://127.0.0.1:8080` not `http://localhost:8080`
- **Context exhaustion**: Restart with `systemctl --user restart ramalama.service`
- **First SSE chunk**: Has `"content": null` - must filter before concatenating

### Performance
- **`track_hover: true`** (St.Button default) causes expensive repaints → UI freezes
- Set `track_hover: false` on all non-interactive widgets
- Only use `track_hover: true` on buttons that actually need hover states

## File Locations
- Extension: `~/.local/share/gnome-shell/extensions/henzai@csoriano/`
- Daemon: `~/.local/bin/henzai-daemon`
- Database: `~/.local/share/henzai/memory.db`
- Logs: `journalctl --user -u henzai-daemon.service`

## External Documentation
- [GNOME Shell Extensions Guide](https://gjs.guide/extensions/)
- [llama.cpp server docs](https://github.com/ggerganov/llama.cpp/blob/master/examples/server/README.md)
- [Ramalama](https://github.com/containers/ramalama)
