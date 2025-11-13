# henzai Demo Guide

Instructions for recording demo videos/screenshots for the website.

## Setup

Before recording, verify:
- `systemctl --user status henzai-daemon` (should be running)
- `systemctl --user status ramalama` (should be running)
- `gnome-extensions list --enabled | grep henzai` (should show enabled)
- Have models pulled: `ramalama list`

Recommended models:
- `ollama://library/deepseek-r1:14b` (for reasoning demos)
- `ollama://library/llama3.2:3b` (for fast responses)
- `ollama://library/qwen2.5:3b` (alternative)

Recording tools:
- OBS Studio: `sudo dnf install obs-studio`
- SimpleScreenRecorder: `sudo dnf install simplescreenrecorder`
- GNOME built-in: `Ctrl+Shift+Alt+R` (30s limit)

---

## Demo 1: Streaming Responses

**What to show:**
1. Press `Super+A` to open henzai
2. Type: "Explain Zeno's dichotomy paradox"
3. Press Enter
4. Watch text stream in real-time word by word
5. Notice markdown formatting (bold, italic, code blocks)

**Focus on:**
- Smooth streaming without lag
- Markdown rendering
- No stuttering

---

## Demo 2: Reasoning Mode

**What to show:**
1. Make sure DeepSeek-R1 is the active model
2. Press `Super+A`
3. Ask: "If I have 3 apples and give away 2, then find 5 more but lose half, how many apples do I have? Show your work."
4. Watch "Thinking..." box appear
5. Click to expand and see reasoning process
6. Notice timer counting up
7. Wait for it to change to "Thought for X.Xs"

**Focus on:**
- Brain icon next to model name
- Thinking box appearing during reasoning
- Expand/collapse interaction
- Real-time timer
- Final "Thought for" message

---

## Demo 3: Model Switching

**What to show:**
1. Press `Super+A`
2. Notice model name at bottom (e.g., "deepseek-r1:14b")
3. Click on the model name
4. Popup shows available models
5. Click a different model (e.g., "llama3.2:3b")
6. Model name updates immediately
7. Brain icon disappears (non-reasoning model)
8. Ask a question to new model
9. Switch back to show it's seamless

**Focus on:**
- Model selector popup
- Current model highlighted
- Instant switching
- Brain icon appearing/disappearing

---

## Demo 4: Generation Control

**Part A - Stop Button:**
1. Press `Super+A`
2. Ask: "Write a 1000 word essay about Linux"
3. While streaming, click ⏹️ Stop button
4. Generation stops immediately
5. No text appears after stopping

**Part B - Rapid Fire (No Answer Leakage):**
1. Ask: "Count to 100"
2. Immediately ask: "What is 2+2?" (before first finishes)
3. Then ask: "What color is the sky?"
4. Notice previous generations stop cleanly
5. No mixed answers, each query independent

**Focus on:**
- Stop button replacing send button
- Immediate stop on click
- Rapid queries cancelling previous ones
- No answer mixing

---

## Demo 5: Collapsible User Queries

**What to show:**
1. Ask a short question: "What is Python?"
   - Shows with arrow → (not expandable)
2. Ask a long multi-line question:
   ```
   I have a complex problem:
   1. My code doesn't work
   2. I get errors
   3. Can you help?
   
   Here's the error...
   ```
3. Notice query collapsed to single line with chevron ▼
4. Click to expand - full text appears
5. Click to collapse again

**Focus on:**
- Short queries with arrow
- Long queries with chevron
- Expand/collapse smooth animation
- Single line vs full text

---

## Demo 6: Markdown Rendering

**What to show:**
Ask: "Show me an example of numbered lists, code blocks, bold and italic text, and headers. Format using markdown."

Expected response should demonstrate:
- **Bold** and *italic*
- # Headers and ## Subheaders
- `inline code`
- Code blocks with syntax
- Numbered and bullet lists

**Alternative questions:**
- "Write a Python function with explanation"
- "Create a TODO list with priorities"

**Focus on:**
- Different markdown elements rendering
- Code blocks with monospace
- Proper list formatting
- Headers with sizing

---

## Demo 7: New Chat

**Part A - Context Carrying:**
1. Press `Super+A`
2. Ask: "My favorite color is blue"
3. AI responds
4. Ask: "What's my favorite color?"
5. AI remembers and says "blue"

**Part B - Context Reset:**
1. Click ➕ New Chat button
2. Conversation clears
3. Welcome message appears
4. Ask: "What's my favorite color?"
5. AI doesn't know (context reset)

**Focus on:**
- AI remembering context initially
- New Chat button clearing everything
- Welcome message appearing
- Context completely reset

---

## Demo 8: Settings Panel

**What to show:**
1. Press `Super+A`
2. Click ⚙️ settings button
3. Settings window opens
4. Show model selection dropdown
5. Select a different model (e.g., switch to llama3.2:3b)
6. Panel updates immediately (model name changes)
7. Show panel position options (Left/Center/Right)
8. Change position - panel moves immediately
9. Show reasoning toggle (currently grayed out)
10. Hover to see tooltip: "Always enabled for reasoning models"

**Focus on:**
- Settings button and window
- Model dropdown with available models
- Immediate visual feedback
- Panel position live updates
- Clean, organized interface
- Reasoning toggle explanation (temporary limitation)

---

## Recording Tips

- **Resolution**: 1920x1080 or 1280x720
- **FPS**: 30 or 60 fps
- **Format**: MP4 (H.264)
- **Duration**: 20-30 seconds per demo
- **Focus**: Zoom into henzai panel

## Post-Recording

Convert to web-friendly format:
```bash
ffmpeg -i demo.mp4 -c:v libx264 -crf 23 -preset medium demo-web.mp4
```

Place files in `/docs/` and update `index.html`

File naming: `demo-01-streaming.mp4`, `demo-02-reasoning.mp4`, etc.


