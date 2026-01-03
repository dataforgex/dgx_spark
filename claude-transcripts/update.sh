#!/bin/bash
# Update Claude Code transcripts to HTML archive

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$HOME/claude-archive"

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Generate/update archive
claude-code-transcripts all --output "$OUTPUT_DIR" --include-agents

echo ""
echo "Archive updated: $OUTPUT_DIR"
echo "Open with: xdg-open $OUTPUT_DIR/index.html"
