#!/bin/bash
# Reload extension in main session (forces file reload)

set -e

cd "$(dirname "$0")/.."

echo "Disabling extension..."
gnome-extensions disable henzai@csoriano 2>/dev/null || true

echo "Copying extension files..."
EXTENSION_DIR=~/.local/share/gnome-shell/extensions/henzai@csoriano
rm -rf "$EXTENSION_DIR"
mkdir -p "$EXTENSION_DIR"
cp -r henzai-extension/* "$EXTENSION_DIR/"

# Compile schema
if [ -d "$EXTENSION_DIR/schemas" ]; then
    glib-compile-schemas "$EXTENSION_DIR/schemas"
fi

# Increment version to force reload
CURRENT_VERSION=$(grep -oP '"version":\s*\K\d+' "$EXTENSION_DIR/metadata.json")
NEW_VERSION=$((CURRENT_VERSION + 1))
sed -i "s/\"version\": $CURRENT_VERSION/\"version\": $NEW_VERSION/" "$EXTENSION_DIR/metadata.json"

echo "Re-enabling extension (version $NEW_VERSION)..."
gnome-extensions enable henzai@csoriano

echo ""
echo "Extension reloaded! Now test and check:"
echo "  cat /tmp/henzai-key-debug.log"
echo "  cat /tmp/henzai-paste-debug.log"

