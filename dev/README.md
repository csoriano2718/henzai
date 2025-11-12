# Development Scripts

Scripts for developing and testing henzai.

## Scripts

### `dev-ui.sh`
Launch nested GNOME Shell for UI-only development (no backend).
- Fast UI iteration
- No daemon required
- Uses main session's Ramalama

### `dev-test.sh`
Launch nested GNOME Shell with isolated daemon for full E2E testing.
- Complete testing environment
- Isolated D-Bus session
- Own daemon instance

### `dev-full.sh`
Build, install, and reload extension in main session.
- **Wayland**: Requires logout/login
- **X11**: Automatic reload

### `nested-with-daemon.sh`
Internal script for launching nested shell with daemon (used by `dev-test.sh`).

### `cleanup-nested.sh`
Clean up stuck nested shell processes and D-Bus sessions.

## Usage

```bash
# Quick UI testing
./dev/dev-ui.sh

# Full E2E testing
./dev/dev-test.sh

# Deploy to main session
./dev/dev-full.sh
```
