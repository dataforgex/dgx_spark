#!/bin/bash
# Claude Code 2.1.9 Installer (Linux x86_64)
# Downloads from GitHub release mirror

set -e

GITHUB_RELEASE="https://github.com/dataforgex/dgx_spark/releases/download/claude-code-2.1.9"
EXPECTED_CHECKSUM="8e3da4e5c904191eb97013706f33a4199562dd06360d950676a62c87e9fbd0d0"
DOWNLOAD_DIR="$HOME/.claude/downloads"
VERSION="2.1.9"

# Check architecture
if [ "$(uname -m)" != "x86_64" ]; then
    echo "This installer only supports Linux x86_64" >&2
    echo "Your architecture: $(uname -m)" >&2
    exit 1
fi

# Check for curl or wget
if command -v curl >/dev/null 2>&1; then
    DOWNLOAD_CMD="curl -fsSL -o"
elif command -v wget >/dev/null 2>&1; then
    DOWNLOAD_CMD="wget -q -O"
else
    echo "Either curl or wget is required" >&2
    exit 1
fi

mkdir -p "$DOWNLOAD_DIR"
BINARY_PATH="$DOWNLOAD_DIR/claude-$VERSION-linux-x64"

echo "Downloading Claude Code $VERSION..."
$DOWNLOAD_CMD "$BINARY_PATH" "$GITHUB_RELEASE/claude-2.1.9-linux-x64"

echo "Verifying checksum..."
ACTUAL_CHECKSUM=$(sha256sum "$BINARY_PATH" | cut -d' ' -f1)

if [ "$ACTUAL_CHECKSUM" != "$EXPECTED_CHECKSUM" ]; then
    echo "Checksum verification failed!" >&2
    rm -f "$BINARY_PATH"
    exit 1
fi

echo "Checksum OK"
chmod +x "$BINARY_PATH"

echo "Installing Claude Code..."
"$BINARY_PATH" install

rm -f "$BINARY_PATH"

echo ""
echo "Installation complete!"
echo ""
