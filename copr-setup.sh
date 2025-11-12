#!/bin/bash
# Script to configure COPR package and trigger first build

set -e

PROJECT="csoriano/henzai"
PACKAGE="henzai"
GIT_URL="https://github.com/csoriano2718/henzai.git"

echo "Setting up COPR package for $PROJECT..."
echo ""

# Check if copr-cli is installed
if ! command -v copr-cli &> /dev/null; then
    echo "ERROR: copr-cli not found. Install with: sudo dnf install copr-cli"
    exit 1
fi

# Check if copr-cli is configured
if [ ! -f ~/.config/copr ]; then
    echo "ERROR: copr-cli not configured."
    echo "Please configure it at: https://copr.fedorainfracloud.org/api/"
    exit 1
fi

echo "Step 1: Adding package to COPR project..."
echo "----------------------------------------"

# Add package if it doesn't exist
copr-cli add-package-scm $PROJECT \
    --name $PACKAGE \
    --clone-url $GIT_URL \
    --method make_srpm \
    --spec henzai.spec \
    --type git \
    --commit main \
    --subdir "" \
    || echo "Package might already exist, continuing..."

echo ""
echo "Step 2: Building package for Fedora 42 and 43..."
echo "-------------------------------------------------"

# Trigger build from SCM (the package is already configured)
copr-cli build-package $PROJECT --nowait --name $PACKAGE

echo ""
echo "✅ Build triggered successfully!"
echo ""
echo "Monitor the build at:"
echo "  https://copr.fedorainfracloud.org/coprs/$PROJECT/builds/"
echo ""
echo "Once complete, users can install with:"
echo "  sudo dnf copr enable $PROJECT"
echo "  sudo dnf install $PACKAGE"
echo ""

