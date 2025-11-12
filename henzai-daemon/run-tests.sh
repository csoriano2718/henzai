#!/bin/bash
# Test runner for henzai daemon

set -e

cd "$(dirname "$0")"

echo "======================================"
echo "henzai Daemon - Test Suite"
echo "======================================"
echo ""

# Install test dependencies if needed
if ! python -c "import pytest" 2>/dev/null; then
    echo "Installing test dependencies..."
    pip install --user -q -r requirements-test.txt
fi

# Run tests
echo "Running tests..."
python -m pytest tests/ -v --tb=short "$@"

echo ""
echo "Test run complete!"

