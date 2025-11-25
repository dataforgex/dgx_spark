#!/bin/bash

GODOT_PATH="$HOME/Downloads/Godot_v4.5.1-stable_linux.arm64"
GAME_PATH="$(dirname "$(realpath "$0")")"

if [ ! -f "$GODOT_PATH" ]; then
    echo "Godot not found at $GODOT_PATH"
    echo "Downloading Godot 4.5.1 for ARM64..."
    wget -q -O /tmp/godot.zip https://github.com/godotengine/godot/releases/download/4.5.1-stable/Godot_v4.5.1-stable_linux.arm64.zip
    unzip -o /tmp/godot.zip -d "$HOME/Downloads/"
    chmod +x "$GODOT_PATH"
    rm /tmp/godot.zip
fi

echo "Starting FPS Game..."
"$GODOT_PATH" --path "$GAME_PATH" 2>/dev/null
