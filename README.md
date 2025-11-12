# henzai

<div align="center">

<img src="data/logo.svg" alt="henzai logo" width="200"/>

**Local AI integrated into GNOME Shell**

Local LLM integration via Ramalama with streaming responses and reasoning mode.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![GNOME Shell](https://img.shields.io/badge/GNOME%20Shell-45+-blue.svg)](https://www.gnome.org/)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)

</div>

---

## 🎬 Quick Demo

**henzai integrates seamlessly into your GNOME desktop:**

1. Press `Super+H` to open the AI panel
2. Type your question and press Enter
3. Watch real-time streaming responses with markdown formatting
4. For reasoning models (DeepSeek-R1), see the thinking process visualized
5. Switch models or start new chats from the toolbar

**Key Highlights:**
- ⚡ **Instant Access**: Always one keystroke away (`Super+H`)
- 🔒 **Private**: All processing happens locally via Ramalama
- 🧠 **Reasoning Visualization**: See how the AI thinks step-by-step
- 💬 **Markdown Support**: Code blocks, lists, formatting preserved
- 🔄 **Conversational**: Multi-turn conversations with context awareness

---

## ✨ Features

- 🤖 **Local LLM Integration**: Powered by Ramalama for privacy-focused AI
- ⚡ **Streaming Responses**: Real-time text generation with markdown support
- 🧠 **Reasoning Mode**: Visual thinking process for reasoning-capable models (DeepSeek-R1, QwQ-32B)
- 🎨 **Model Switching**: Easy switching between available models via clickable model name
- 📝 **Markdown Rendering**: Support for code blocks, lists, headings, bold, italic
- ⚙️ **Settings Panel**: Configure models and reasoning mode
- ⌨️ **Keyboard Shortcuts**: Quick access with `Super+H`
- 🔄 **New Chat**: Start fresh conversations anytime
- ⏹️ **Generation Control**: Stop mid-response without answer leakage

---

## 📦 Requirements

- **GNOME Shell 45+**
- **Python 3.8+**
- **Ramalama** ([Installation guide](https://github.com/containers/ramalama))
- **Podman** (for Ramalama)

---

## 🚀 Installation

### Option 1: RPM Package (Fedora 42/43) - Recommended

[![Copr build status](https://copr.fedorainfracloud.org/coprs/csoriano/henzai/package/henzai/status_image/last_build.png)](https://copr.fedorainfracloud.org/coprs/csoriano/henzai/package/henzai/)

```bash
# Enable the COPR repository and install
sudo dnf copr enable csoriano/henzai && sudo dnf install henzai

# Restart your computer (or log out and back in)
# This will automatically start all services and load the extension

# After restart, press Super+H to use henzai!
```

The RPM package automatically:
- ✅ Installs henzai daemon and GNOME Shell extension
- ✅ Installs Ramalama as a dependency
- ✅ Installs systemd user services
- ✅ Installs D-Bus service activation
- ✅ Installs all Python dependencies
- ✅ **Enables services to auto-start on login**
- ✅ **Enables the GNOME Shell extension**

**Just restart your computer and everything works!** Services auto-start on every login.

---

### Option 2: Manual Installation

### Quick Install

```bash
# Clone the repository
git clone https://github.com/csoriano2718/henzai.git
cd henzai

# Run the installation script
./install.sh
```

The installer will:
1. Install Python dependencies
2. Set up systemd services (ramalama, henzai-daemon)
3. Install D-Bus service activation (for auto-starting the daemon)
4. Install the GNOME Shell extension
5. Download and configure the default model (DeepSeek-R1 14B)
6. Start all services automatically

**After installation**: Log out and log back in to activate the extension.

### Verify Installation

henzai requires backend services to function. After logging back in, verify they're running:

```bash
# Check services are running (should auto-start after login)
systemctl --user status ramalama
systemctl --user status henzai-daemon

# Check extension is enabled
gnome-extensions list --enabled | grep henzai
```

**Troubleshooting**:
- If services aren't running after login, manually start them:
  ```bash
  systemctl --user start ramalama
  systemctl --user start henzai-daemon
  ```
- The extension will show an error if it can't connect to the daemon. After the first login post-install, the D-Bus activation should auto-start the daemon when you open the panel (Super+H).

---

## 🚀 Usage

### Basic Usage

1. **Open henzai**: Press `Super+H` (or your configured keybinding)
2. **Ask a question**: Type your query in the input field
3. **Send**: Press `Enter` or click the ⬆️ button
4. **View response**: Watch the AI respond in real-time with markdown formatting

### Keyboard Shortcuts

- `Super+H`: Toggle henzai panel
- `Enter`: Send message
- `Ctrl+Enter`: Insert newline
- `Escape`: Close panel

### Toolbar Actions

- **Model Name**: Click to switch between available models
- **⚙️ Settings**: Configure models and reasoning mode
- **➕ New Chat**: Start a fresh conversation
- **⬆️ Send**: Send your message
- **⏹️ Stop**: Cancel generation (replaces send button when active)

### Reasoning Mode

For supported models (DeepSeek-R1, QwQ-32B), you'll see a "Thinking..." box:
- **Collapsed**: Shows thinking duration
- **Expanded**: Click to view the AI's reasoning process
- **Real-time**: Updates as the AI thinks

---

## 🛠️ Development

### Project Structure

```
henzai/
├── henzai-extension/        # GNOME Shell extension
│   ├── extension.js         # Main extension entry point
│   ├── ui/                  # UI components
│   │   ├── chatPanel.js    # Main chat interface
│   │   └── scrollableEntry.js  # Custom scrollable input widget
│   ├── dbus/               # D-Bus client
│   ├── schemas/            # GSettings schema
│   ├── prefs.js            # Preferences UI
│   └── stylesheet.css      # Styles
├── henzai-daemon/          # Python daemon
│   ├── henzai/
│   │   ├── main.py        # Daemon entry point
│   │   ├── llm.py         # LLM client (Ramalama integration)
│   │   ├── memory.py      # Conversation memory
│   │   ├── dbus_service.py # D-Bus service
│   │   └── tools.py       # Tool execution (future)
│   ├── systemd/           # Service files
│   └── tests/             # Unit tests
├── dev/                    # Development scripts
│   ├── deploy-and-restart.sh  # Deploy and restart nested shell
│   └── dev-test.sh        # Legacy test script
├── tests/                  # Integration tests
├── docs/                   # Documentation
└── install.sh             # Installation script
```

### Development Setup

```bash
# Install in development mode
pip3 install --user -e ./henzai-daemon

# Run the development test environment (nested GNOME Shell)
./dev/deploy-and-restart.sh
```

### Testing

```bash
# Run Python tests
cd henzai-daemon
./run-tests.sh

# Test D-Bus interface
./tests/test-streaming.py

# Test model switching
./tests/test-model-switch.py

# Test reasoning mode
./tests/test-reasoning.py
```

### Architecture

henzai uses a two-component architecture:

1. **GNOME Shell Extension** (JavaScript/GJS):
   - User interface and interaction
   - D-Bus client for daemon communication
   - Real-time streaming display

2. **Python Daemon** (systemd service):
   - LLM inference via Ramalama API
   - Conversation memory (in-memory, resets on new chat)
   - D-Bus service for IPC
   - Systemd integration

**Communication**: D-Bus is used for all communication between the extension and daemon, including streaming responses via signals.

---

## 🗺️ Roadmap

### Current Status: MVP Complete ✅

henzai is now feature-complete for its initial release. The core functionality is stable and ready for daily use.

### Completed Features
- ✅ Local LLM integration via Ramalama
- ✅ Streaming responses with markdown rendering
- ✅ Reasoning mode visualization (DeepSeek-R1, QwQ-32B)
- ✅ Model switching
- ✅ Settings panel
- ✅ Keyboard shortcuts
- ✅ RPM packaging for Fedora
- ✅ Auto-start services
- ✅ D-Bus activation
- ✅ Collapsible user queries
- ✅ Generation cancellation
- ✅ Race condition handling

### Future Enhancements (Post-MVP)

**v0.2 - Advanced Model Parameters**
- 🌡️ **Temperature Control**: Adjust creativity vs. precision (0.0-2.0)
- 📏 **Max Response Length**: Limit token generation
- 💾 **Context Window**: Configure conversation memory

**v0.3 - RAG (Retrieval-Augmented Generation)**
- 📁 **Simple Folder Path**: Just paste a path to your documents
- 🤖 **Auto-indexing**: Ramalama handles the rest
- 💼 **Use Cases**: Project docs, personal notes, code repos

**v0.4 - Tool Integration**
- 🔧 **Shell Commands**: Execute with user confirmation
- 📂 **File Operations**: Read, write, list files
- 🌐 **Web Search**: Real-time information retrieval
- 💻 **System Queries**: System information access

**Beyond v0.4**
- 🎤 **Voice Input**: Speech-to-text integration
- 📎 **File Attachments**: Share code/documents with AI
- 🔌 **Cloud LLM Support**: Optional OpenAI/Anthropic
- 🔄 **Multi-turn Reasoning**: Enhanced reasoning workflows
- 💬 **Chat History**: Persistent conversation storage

**Note**: This is a stable MVP. New features will be added based on community feedback and use cases.

---

## 🤝 Contributing

Any contributions are more than welcome! 

**Note**: This project is developed by AI (vibe-coded), so contributions would probably be easier doing the same, as the code isn't optimized for human reading/writing patterns.

Whether it's:
- 🐛 Bug reports and fixes
- 💡 Feature suggestions
- 📖 Documentation improvements
- 🌍 Translations
- 🎨 UI/UX enhancements

Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

For major changes, please open an issue first to discuss what you'd like to change.

---

## 🙏 Acknowledgments

henzai builds upon the excellent work of the open-source community:

### Ramalama
- **Project**: [Ramalama](https://github.com/containers/ramalama)
- **Developers**: The Ramalama team and contributors
- **Role**: Local LLM inference engine that powers henzai's AI capabilities

### GNOME Icon Library
- **Project**: [GNOME Icon Library](https://gitlab.gnome.org/World/design/icon-library)
- **Developer**: Bilal Elmoussaoui
- **Designers**: Allan Day, Jakub Steiner
- **Role**: Icon assets used in henzai's interface

Special thanks to these projects for making local, privacy-focused AI accessible to everyone.

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0** - see the [LICENSE](LICENSE) file for details.

**Note**: This is an **AI-developed project** (vibe-coded), not just AI-assisted. The code may not follow traditional human optimization patterns but is functional and evolving.

**Assisted-by**: Generated (vibe-coded) by Cursor AI with Claude Sonnet 4.5

---

<div align="center">

**Made with 🤖 by AI • GPL-3.0 License**

[⬆ Back to top](#henzai)

</div>
