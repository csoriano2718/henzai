# AGENTS.md - AI Assistant Guidelines for henzai

**Last Updated**: 2025-11-11  
**Purpose**: Enforce quality, prevent repeated mistakes, maintain architectural integrity

> **Note**: This file follows the `AGENTS.md` standard convention for AI-assisted development.  
> It is automatically loaded by Cursor and other AI coding assistants to provide context and rules.

---

## 🚨 CONSTITUTIONAL RULES (NEVER VIOLATE)

### 1. API/Feature Existence Verification
**NEVER remove functionality or declare "API/feature doesn't exist" without PRIMARY SOURCE proof.**

**What counts as proof:**
- ✅ Official documentation link
- ✅ Source code inspection
- ✅ HTTP 404 response from actual endpoint
- ❌ Connection errors (these indicate networking/config issues, not non-existence)
- ❌ Timeout errors
- ❌ Permission errors

**If you encounter connection/network errors:**
1. Test from a known-good location (e.g., inside container: `podman exec`)
2. Check official documentation or source code
3. Try different network configurations (IPv4 vs IPv6, localhost vs 127.0.0.1)
4. Diagnose the actual networking issue
5. ONLY THEN conclude if something truly doesn't exist

**Example violation:**
- Seeing connection reset on `/health` endpoint → Assuming it doesn't exist → Building workaround architecture
- **Correct approach:** Test from inside container → Check llama.cpp docs → Diagnose IPv6 issue → Fix properly

**Why this matters:**
- False assumptions lead to broken architecture
- Removing functionality based on wrong diagnosis creates user-facing bugs
- Recovery requires architectural rework, not just bug fixes

---

## 📋 PROJECT-SPECIFIC RULES

### File Organization (from AI_ASSISTANT_CHECKLIST.md)

**Before creating ANY file:**
```bash
# STEP 1: CHECK IF IT EXISTS
ls *TOPIC*.md
ls henzai-daemon/henzai/*topic*.py
ls henzai-extension/*topic*.js

# STEP 2: 
# - If found → UPDATE it
# - If not found → ASK user first
```

**Code consolidation principles:**
- **Python Daemon**: Keep related code together
  - `llm.py` - ALL LLM/model code
  - `tools.py` - ALL system actions
  - `memory.py` - ALL storage
  - `dbus_service.py` - D-Bus interface only
  
- **GNOME Extension**: Keep UI cohesive
  - `ui/chatPanel.js` - ALL chat UI
  - `dbus/client.js` - D-Bus client wrapper only
  - `extension.js` - Entry point only

**Default behavior**: Update existing files, don't create new ones.

---

## 🔍 DEBUGGING & VERIFICATION

### Multi-Layer Testing (from README_AI.md)

**Critical Lesson**: Unit tests passing ≠ feature working

**Always verify at each layer:**
1. **API directly** (`curl http://127.0.0.1:8080/endpoint`)
2. **LLM client isolated** (Python REPL test)
3. **D-Bus service method** (`busctl call ...`)
4. **D-Bus signal emission** (`dbus-monitor`)
5. **Full E2E with UI** (nested shell test)

**Common pitfalls:**
- Assuming localhost = 127.0.0.1 (it's not! IPv6 vs IPv4)
- Testing only happy path
- Not checking service logs: `journalctl --user -u henzai-daemon -f`
- Not verifying in nested shell before main session

---

## 🚧 GNOME SHELL DEVELOPMENT GOTCHAS

### Wayland Session Management (CRITICAL)
- **NEVER** run `pkill gnome-shell` or `gnome-shell --replace` in main session
- Kills entire Wayland session = forced logout (no recovery)
- **ALWAYS** use nested shell for UI testing:
  ```bash
  ./dev/dev-ui.sh      # Fast: UI only
  ./dev/dev-test.sh    # Complete: UI + daemon
  ```

### Extension Development
- `track_hover: true` (default) causes expensive repaints → UI freezes
- Set `track_hover: false` on all non-interactive widgets
- Only use `track_hover: true` on buttons that actually need hover states
- Use `127.0.0.1` instead of `localhost` for Ramalama API (IPv6 issues with pasta/Podman)

---

## 🎯 COMMON MISTAKE PATTERNS

### From vibe-learn history:

**1. Premature Implementation**
- **Pattern**: Implementing workarounds before verifying root cause
- **Example**: Removing health check because connection fails
- **Solution**: Always verify the endpoint/feature actually doesn't exist first

**2. Misalignment**
- **Pattern**: Testing to prove code works instead of reproducing user's experience
- **Example**: Testing in development environment, not in user's actual setup
- **Solution**: Always reproduce the exact user scenario before fixing

**3. Complex Solution Bias**
- **Pattern**: Assuming complex solutions without checking simple ones
- **Example**: Assuming St.ScrollView has complex API without checking GNOME examples
- **Solution**: Check official GNOME Shell extensions first (apps-menu, etc.)

---

## 📐 ARCHITECTURAL PRINCIPLES

### D-Bus Interface Changes
**ANY change to D-Bus methods/signals requires updates in THREE places:**
1. `henzai-daemon/henzai/dbus_service.py` (Python service)
2. `henzai-extension/dbus/client.js` (JavaScript client)
3. `docs/reference/DBUS_API.md` (Documentation)

**Checklist before committing D-Bus changes:**
- [ ] Python service updated
- [ ] JavaScript client updated
- [ ] Documentation updated
- [ ] Tested with `busctl` manually
- [ ] Tested E2E in nested shell

### Ramalama/LLM Integration
- **Always use** `http://127.0.0.1:8080` not `http://localhost:8080` (IPv6 issue)
- **Health check**: `/health` endpoint returns `{"status":"ok"}` when ready
- **First SSE chunk** has `"content": null` - filter before concatenating
- **Context exhaustion**: Restart with `systemctl --user restart ramalama.service`

---

## 🔄 SESSION START CHECKLIST

**Every session, run these commands (3 min):**

```bash
# 1. What exists?
ls *.md
ls henzai-daemon/henzai/*.py
ls henzai-extension/*.js

# 2. Read the brief
head -50 README.md

# 3. Check current status
cat docs/current/STATUS.md

# 4. Review development scripts
cat dev/README.md

# 5. Review any recent changes
git log --oneline -10
```

**Key references to check:**
- `dev/README.md` - Testing scripts (dev-ui.sh, dev-test.sh)
- `AGENTS.md` - This file (lessons learned, gotchas)
- `docs/current/STATUS.md` - Current project status

---

## ✅ QUALITY CHECKLIST

### Before Proposing Solution:
- [ ] Did I verify the problem exists? (reproduce it)
- [ ] Did I check documentation/source code?
- [ ] Did I test at each integration layer?
- [ ] Did I consider simpler solutions first?
- [ ] Am I removing functionality? (If yes, VERIFY it's truly not needed)

### Before Committing Code:
- [ ] Did I update all three D-Bus interface files? (if applicable)
- [ ] Did I test in nested shell?
- [ ] Did I check daemon logs?
- [ ] Did I update relevant documentation?
- [ ] Did I avoid creating unnecessary new files?

### After User Reports Issue:
- [ ] Did I reproduce their exact scenario?
- [ ] Did I test my fix in their context (not just mine)?
- [ ] Did I verify the fix doesn't break existing functionality?

---

## 🎓 LESSONS LEARNED

### 2025-11-11: Clutter.Text Invisible Text & Clutter.Color API

**What happened:**
- Text in the input field was invisible after system restart
- Tried multiple approaches to set color:
  1. `new Clutter.Color({...})` → "Clutter.Color is not a constructor"
  2. `Clutter.Color.from_string()` → "Clutter.Color is undefined"
  3. `this._clutterText.set_color({ red: 26, ... })` → "Object is not a subclass of GObject_Boxed"
  4. Creating St.ThemeNode manually → "No property theme on StThemeNode"
- Each attempt **crashed GNOME Shell** and killed the Wayland session
- Investigation revealed the text was **ALWAYS invisible** - even in the original commit!

**Root cause:**
- `Clutter.Text` has **NO default color** (get_color() returns empty object `{}`)
- Text is invisible unless color is explicitly set
- CSS `color:` property does NOT apply to raw Clutter actors (only St widgets)
- `Clutter.Color` constructor **does not exist** in modern GJS/GNOME Shell 47+
- Colors must come from theme using `get_theme_node().get_foreground_color()`

**The working fix:**
```javascript
// In _buildUI(), after adding child to widget:
this.connect('style-changed', () => {
    const themeNode = this.get_theme_node();
    const color = themeNode.get_foreground_color();
    this._clutterText.set_color(color);
});
```

**Why this works:**
- `style-changed` signal fires when the St.Widget's theme is applied
- `get_theme_node()` is safe to call on St.Widget (not on Clutter actors)
- Returns a proper Clutter color object that `set_color()` accepts
- Automatically inherits color from CSS `.henzai-input { color: #1a1a1a; }`

**What should have happened:**
1. Check how GNOME Shell's own `St.Entry` handles Clutter.Text colors
2. Look for `style-changed` or `realize` signal patterns in GNOME code
3. Test color setting approaches in a standalone GJS script BEFORE embedding in extension
4. Never assume API constructors exist - always test with `typeof` first

**Cost:**
- Multiple Wayland session crashes (forcing user logouts)
- Went through 10+ failed iterations
- Wasted time on wrong API approaches

**Prevention:**
- **ALWAYS** test Clutter/GObject API calls in standalone scripts first
- **NEVER** guess at GObject constructor syntax - check GJS documentation
- `Clutter.Text` ALWAYS needs explicit color from theme
- Use `style-changed` signal to apply theme colors to raw Clutter children
- When dealing with colors: get them from theme, don't create manually

---

### 2025-11-12: The Opacity Scale Mismatch (330+ Versions)

**What happened:**
- User reported ScrollableTextInput was invisible (but functionally working)
- Spent 330+ versions debugging, assuming it was a `Clutter.Text` color issue
- Tried multiple color-setting approaches (style-changed, realize signals, manual colors)
- Created 5 test inputs to find pattern → only Input #4 (stored in `this._inputEntry`) was invisible
- Eventually traced to `_checkReadiness()` setting `this._inputEntry.opacity = 0.7`
- **Discovered**: GNOME Shell/Clutter uses **0-255 scale** for opacity, NOT 0.0-1.0!

**Root cause:**
- Set `opacity = 0.7` expecting 70% opacity (0.0-1.0 scale like CSS/Qt/SwiftUI)
- Clutter.Actor.opacity uses **0-255 scale** → 0.7 = nearly transparent (0.3% opacity!)
- Widget was invisible because `0.7 / 255 ≈ 0.003` instead of `0.7 = 70%`

**The fix:**
```javascript
// WRONG (0.7 out of 255 ≈ 0.3% opacity):
this._inputEntry.opacity = 0.7;  // Nearly invisible!
this._inputEntry.opacity = 1.0;  // Still nearly invisible!

// CORRECT (0-255 scale):
this._inputEntry.opacity = 179;  // 70% opacity (0.7 * 255)
this._inputEntry.opacity = 255;  // 100% opacity (fully visible)
```

**What should have happened:**
1. User reports "widget invisible"
2. Check what's different → only `this._inputEntry` affected
3. Find code that modifies it → `_checkReadiness()` sets opacity
4. **→ CHECK CLUTTER DOCUMENTATION**: "What range does `Clutter.Actor.opacity` accept?"
5. Docs: `opacity (0-255) - The opacity of the actor`
6. Fix: Change 0.7 → 179, 1.0 → 255
7. **Total time: ~15 minutes instead of hours**

**Cost:**
- 330+ extension versions installed
- Multiple hours of debugging
- Chased wrong hypothesis (Clutter.Text color) for too long
- High cognitive load and user frustration

**Prevention:**
- **ALWAYS check API documentation** when working with unfamiliar frameworks
- **Don't assume API conventions** (most use 0.0-1.0, but Clutter uses 0-255)
- **When behavior contradicts expectations → CHECK DOCS FIRST**
- **List ALL possible causes** for invisible widgets: color, opacity, size, clipping, visibility
- **Create multiple test instances EARLY** to isolate which specific instance is affected
- **Documentation is not a fallback** - it's a first tool when working with unfamiliar APIs

**Key lesson:**
> When a visual property (opacity, color, size) behaves in a way that seems to defy logic, your first assumption should be that you are feeding it the wrong **type** or **scale** of data. Check the API documentation for the expected range/format.

**API Gotcha:**
- **Clutter.Actor.opacity**: 0-255 (uint8)
- **CSS opacity**: 0.0-1.0 (float)
- **Qt setOpacity()**: 0.0-1.0 (float)
- **SwiftUI .opacity()**: 0.0-1.0 (double)
- **Android alpha**: 0.0-1.0 (float)

---

### 2025-11-11: The /health Endpoint Incident

**What happened:**
- Connection errors to `/health` endpoint
- Assumed endpoint doesn't exist in llama-server
- Built workaround: "trust systemd status = ready"
- Removed actual health detection capability
- User questioned: "doesn't ramalama have health checks?"
- Discovered: endpoint exists, IPv6 networking was the issue

**Root cause:**
- Treated connection error as proof of non-existence
- Built architecture around false assumption
- Didn't check documentation or test properly

**What should have happened:**
1. See connection errors
2. Test from inside container (`podman exec`)
3. Discover endpoint works there
4. Diagnose networking issue (IPv6 vs IPv4)
5. Fix by using `127.0.0.1` instead of `localhost`

**Cost:**
- Nearly shipped broken status detection
- Users would see "ready" while model still loading
- Wasted time on wrong architectural changes

**Prevention:**
- **CONSTITUTIONAL RULE #1** added to prevent this pattern
- Must verify with primary source before declaring something doesn't exist
- Connection errors indicate networking issues, not missing features

---

### 2025-11-12: The 330+ Version Loop (ScrollableTextInput Invisible Text)

**What happened:**
- User reported input text was invisible (but functionally working)
- Spent 330+ versions trying different approaches:
  1. Replaced `ScrollableTextInput` with `St.Entry` - still invisible
  2. Tried setting `Clutter.Color` programmatically - API doesn't exist (crashes)
  3. Tried inline CSS styles (`color:`, `background-color:`) - ignored
  4. Tried theme color extraction - returned empty objects
  5. Discovered "inline widget creation" pattern where `St.Label` worked
  6. Assumed the issue was widget reference storage timing
- Eventually realized: **Check the actual ScrollableTextInput implementation!**

**Root cause:**
- `ScrollableTextInput._buildUI()` creates a `Clutter.Text` but **never sets its color**
- The exact same issue as the 2025-11-11 lesson, but we forgot to check our own code first
- Spent hours debugging the wrong layer (chatPanel.js) when the bug was in scrollableTextInput.js

**The fix (identical to 2025-11-11 lesson):**
```javascript
// In scrollableTextInput.js _buildUI():
this.add_child(this._clutterText);

// CRITICAL: Clutter.Text has NO default color!
this.connect('style-changed', () => {
    const themeNode = this.get_theme_node();
    const color = themeNode.get_foreground_color();
    this._clutterText.set_color(color);
});
```

**What should have happened:**
1. User reports invisible text
2. Check `AGENTS.md` → Lessons Learned → 2025-11-11 (Clutter.Text color issue)
3. Inspect `scrollableTextInput.js` for color handling
4. Find missing color logic
5. Apply the documented fix
6. **Total time: 5 minutes instead of 330+ versions**

**Cost:**
- 330+ extension versions installed
- Multiple hours of debugging
- Tested wrong hypotheses (inline creation, variable storage, CSS precedence)
- User frustration ("we're going in circles")

**Prevention:**
- **ALWAYS check AGENTS.md Lessons Learned FIRST when debugging UI issues**
- **Inspect the actual widget implementation** before debugging higher layers
- Don't assume "it worked before" without checking git history
- When user says "invisible Clutter.Text", immediately check for color handling
- Document fixes properly so they can be reused (we had the fix documented!)

**Key insight:**  
We had the EXACT solution documented in AGENTS.md from 2025-11-11, but didn't:
1. Read the Lessons Learned section at session start
2. Check our own widget implementation first
3. Recognize the pattern (Clutter.Text invisible = missing color)

This is why the "SESSION START CHECKLIST" exists - **use it!**

---

### 2025-11-13: Forgetting Existing Dev Scripts

**What happened:**
- User wanted to test UI in nested shell
- I tried to create new scripts and figure out how to run nested shell
- Spent 30+ minutes debugging D-Bus sessions, daemon connections, window size
- Kept forgetting that `dev/dev-test.sh` already existed and worked perfectly

**Root cause:**
- Didn't run SESSION START CHECKLIST at session start
- Didn't check `dev/README.md` which documents all testing scripts
- Tried to "remember" or "figure out" instead of checking documentation
- Wasted time reinventing what was already documented and working

**What should have happened:**
1. Session starts
2. Run SESSION START CHECKLIST → includes `cat dev/README.md`
3. See: `./dev/dev-test.sh` for full E2E testing with nested shell
4. Run that script
5. **Total time: 2 minutes instead of 30+ minutes**

**Cost:**
- 30+ minutes of wasted time
- User frustration ("isn't this already scripted or documented?")
- Multiple failed attempts at recreating working scripts
- High cognitive load debugging things that were already solved

**Prevention:**
- **ALWAYS run SESSION START CHECKLIST** at the beginning of every session
- **Don't try to "remember"** - check documentation first
- **Read `dev/README.md`** before attempting any testing/development tasks
- The documentation exists for a reason - use it!

**Key lesson:**
> If you're trying to figure out "how do I test this" or "how do I run this", you're doing it wrong. Check the documentation first. The scripts probably already exist.

---

## 🚀 DEVELOPMENT WORKFLOW

### Fast Iteration Loop
```bash
# Backend changes only
sudo ./install.sh
systemctl --user restart henzai-daemon
journalctl --user -u henzai-daemon -f

# UI changes
./dev/dev-ui.sh
# Make changes
# Reload: Alt+F2, type 'r', Enter

# Full E2E test
./dev/dev-test.sh
```

### Testing Pyramid
1. **Unit tests** (Python): `cd henzai-daemon && pytest`
2. **Integration tests**: `python3 tests/test-*.py`
3. **Manual UI tests**: Nested shell
4. **Main session test**: Only after everything passes

---

## 📚 REFERENCE

### Key Files to Know
- `AGENTS.md` (this file) - Agent behavioral rules
- `README_AI.md` (ai/) - Technical reference, quick commands
- `AI_ASSISTANT_CHECKLIST.md` (ai/) - File organization rules
- `docs/reference/DBUS_API.md` - D-Bus interface spec
- `docs/current/STATUS.md` - Current project status

### External Documentation
- [GNOME Shell Extensions](https://gjs.guide/extensions/)
- [llama.cpp server](https://github.com/ggerganov/llama.cpp/blob/master/examples/server/README.md)
- [Ramalama](https://github.com/containers/ramalama)

---

**Status**: MANDATORY - Enforce every session  
**Enforcement**: User will call out violations immediately  
**Updates**: Add new patterns/lessons as they emerge

