# henzai System Tools Reference

This document describes all available system action tools that the AI can execute.

---

## Tool Execution Flow

1. User sends a message to the AI
2. LLM determines if an action is needed
3. LLM returns a tool call in format: `<tool_call>{JSON}</tool_call>`
4. Daemon executes the tool
5. Tool result is sent back to LLM
6. LLM generates a natural language response
7. Response is returned to user

---

## Available Tools

### 1. launch_app

Launch a GNOME application.

**Parameters**:
- `app_name` (string): Application name or desktop file ID

**Examples**:

```json
{"name": "launch_app", "parameters": {"app_name": "firefox"}}
{"name": "launch_app", "parameters": {"app_name": "org.gnome.Nautilus"}}
{"name": "launch_app", "parameters": {"app_name": "terminal"}}
```

**Supported Application Names**:
- Common names: `firefox`, `chrome`, `terminal`, `files`, `calculator`
- Desktop IDs: `org.gnome.Nautilus`, `org.mozilla.Firefox`, etc.
- Partial matches: Searches installed apps if exact match not found

**User Examples**:
- "open firefox"
- "launch the file manager"
- "start terminal"
- "open calculator"

**Return Value**:
- Success: `"Launched <app_name>"`
- Failure: `"Could not find application: <app_name>"`

---

### 2. adjust_setting

Change a GNOME system setting using gsettings.

**Parameters**:
- `schema` (string): GSettings schema path
- `key` (string): Setting key name
- `value` (string): New value

**Common Settings**:

#### Dark Mode
```json
{
  "name": "adjust_setting",
  "parameters": {
    "schema": "org.gnome.desktop.interface",
    "key": "color-scheme",
    "value": "prefer-dark"
  }
}
```

#### Light Mode
```json
{
  "name": "adjust_setting",
  "parameters": {
    "schema": "org.gnome.desktop.interface",
    "key": "color-scheme",
    "value": "prefer-light"
  }
}
```

#### GTK Theme
```json
{
  "name": "adjust_setting",
  "parameters": {
    "schema": "org.gnome.desktop.interface",
    "key": "gtk-theme",
    "value": "Adwaita"
  }
}
```

#### Font Size
```json
{
  "name": "adjust_setting",
  "parameters": {
    "schema": "org.gnome.desktop.interface",
    "key": "text-scaling-factor",
    "value": "1.2"
  }
}
```

**User Examples**:
- "enable dark mode"
- "switch to light theme"
- "change the theme to Adwaita"
- "increase text size"

**Return Value**:
- Success: `"Set <schema> <key> to <value>"`
- Failure: Error message with details

**Common Schemas**:
- `org.gnome.desktop.interface` - Interface settings
- `org.gnome.desktop.wm.preferences` - Window manager
- `org.gnome.desktop.peripherals.mouse` - Mouse settings
- `org.gnome.desktop.peripherals.keyboard` - Keyboard settings
- `org.gnome.desktop.background` - Desktop background

---

### 3. execute_command

Execute a shell command.

**Parameters**:
- `command` (string): Shell command to execute

**Security**:
Dangerous commands are blocked, including:
- `rm -rf /`
- `mkfs`
- `dd if=`
- Commands targeting `/dev/`
- `chmod 777`
- `chown root`

**Examples**:

```json
{"name": "execute_command", "parameters": {"command": "date"}}
{"name": "execute_command", "parameters": {"command": "df -h"}}
{"name": "execute_command", "parameters": {"command": "ps aux | grep firefox"}}
```

**User Examples**:
- "what's the current date?"
- "show disk usage"
- "list running processes"
- "check my IP address"

**Return Value**:
- Success: Command output (stdout)
- Failure: Error message or stderr

**Timeout**: 10 seconds

---

### 4. get_system_info

Get information about the system.

**Parameters**: None

**Returns**:
- Operating system name and version
- Desktop session type
- Number of installed applications
- System uptime

**Example**:

```json
{"name": "get_system_info", "parameters": {}}
```

**User Examples**:
- "what system am I running?"
- "show system information"
- "how long has the system been running?"

**Sample Output**:
```
OS: Fedora Linux 42 (Workstation Edition)
Desktop: gnome
Installed applications: 347
System uptime: 12 hours
```

---

## Helper Functions

The following Python helper functions are available in `tools.py`:

### enable_dark_mode()

Shortcut to enable GNOME dark mode.

```python
from henzai.tools import enable_dark_mode
enable_dark_mode()
```

### disable_dark_mode()

Shortcut to disable GNOME dark mode.

```python
from henzai.tools import disable_dark_mode
disable_dark_mode()
```

### set_volume(level: int)

Set system volume (0-100).

```python
from henzai.tools import set_volume
set_volume(75)
```

---

## Adding New Tools

To add a new tool:

1. **Add implementation to `tools.py`**:

```python
def my_new_tool(param1: str, param2: int) -> str:
    """
    Tool description.
    
    Args:
        param1: Description
        param2: Description
        
    Returns:
        Result string
    """
    # Implementation
    return "Success"
```

2. **Register in `ToolExecutor.execute()`**:

```python
tool_map = {
    'my_new_tool': self.my_new_tool,
    # ... other tools
}
```

3. **Add to system prompt in `llm.py`**:

```python
SYSTEM_PROMPT = """...

5. my_new_tool
   - Description: What it does
   - Parameters:
     * param1 (string): Description
     * param2 (integer): Description
"""
```

4. **Update this documentation**

5. **Test the tool**:

```bash
# Via D-Bus
busctl --user call org.gnome.henzai /org/gnome/henzai org.gnome.henzai \
  SendMessage s "Use my new tool"
```

---

## Tool Best Practices

### For Tool Developers

1. **Error Handling**: Always catch exceptions and return meaningful errors
2. **Validation**: Validate all parameters before execution
3. **Timeouts**: Set appropriate timeouts for long-running operations
4. **Security**: Never trust user input, sanitize everything
5. **Idempotency**: Tools should be safe to call multiple times

### For LLM Prompts

1. **Be Specific**: Describe exactly what the tool does
2. **List Parameters**: Include type and description for each
3. **Provide Examples**: Show JSON format for tool calls
4. **Document Limits**: Note any restrictions or limitations
5. **Explain Return**: Describe what success/failure looks like

---

## Troubleshooting

### Tool Not Found

Check that the tool is registered in `ToolExecutor.execute()` method.

### Tool Execution Fails

```bash
# Check daemon logs
journalctl --user -u henzai-daemon -f

# Look for error messages from tools.py
```

### Permission Denied

Some operations require specific permissions:
- File operations: Check file permissions
- System settings: Ensure gsettings schema exists
- Commands: Check if binary is in PATH

---

## Future Tools

Planned tools for future releases:

1. **Screenshot Tools**:
   - `take_screenshot(path, region)`
   - `analyze_screenshot(question)`

2. **File Operations**:
   - `find_file(name, path)`
   - `open_file(path)`
   - `search_content(query, path)`

3. **Window Management**:
   - `list_windows()`
   - `focus_window(title)`
   - `close_window(title)`

4. **Notification Management**:
   - `list_notifications()`
   - `dismiss_notification(id)`
   - `send_notification(title, body)`

5. **Calendar/Tasks**:
   - `list_events(date)`
   - `create_event(title, time)`
   - `add_task(description)`










