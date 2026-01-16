#!/bin/bash
# Offline installer for Claude Code 2.1.9 (Linux x86_64)
# Copy this script and claude-2.1.9-linux-x64 to the target machine

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BINARY="$SCRIPT_DIR/claude-2.1.9-linux-x64"
EXPECTED_CHECKSUM="8e3da4e5c904191eb97013706f33a4199562dd06360d950676a62c87e9fbd0d0"

if [ ! -f "$BINARY" ]; then
    echo "Error: Binary not found at $BINARY" >&2
    echo "Make sure claude-2.1.9-linux-x64 is in the same directory as this script" >&2
    exit 1
fi

# Verify checksum
echo "Verifying checksum..."
ACTUAL_CHECKSUM=$(sha256sum "$BINARY" | cut -d' ' -f1)

if [ "$ACTUAL_CHECKSUM" != "$EXPECTED_CHECKSUM" ]; then
    echo "Checksum verification failed!" >&2
    echo "Expected: $EXPECTED_CHECKSUM" >&2
    echo "Actual:   $ACTUAL_CHECKSUM" >&2
    exit 1
fi

echo "Checksum OK"

# Make sure it's executable
chmod +x "$BINARY"

# Run the installer
echo "Installing Claude Code..."
"$BINARY" install

echo ""
echo "Installation complete!"
echo ""
