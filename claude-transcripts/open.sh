#!/bin/bash
# Open Claude Code transcripts archive in browser

OUTPUT_DIR="$HOME/claude-archive"

if [ -f "$OUTPUT_DIR/index.html" ]; then
    xdg-open "$OUTPUT_DIR/index.html"
else
    echo "Archive not found. Run ./update.sh first."
    exit 1
fi
