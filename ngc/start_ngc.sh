#!/bin/bash

# NGC Container Startup Script
# This script starts the NGC container with the specified configuration

# Configuration - Edit these variables as needed
CONTAINER_NAME="${CONTAINER_NAME:-qwen3-32b-nim}"
IMG_NAME="${IMG_NAME:-nvcr.io/nim/qwen/qwen3-32b-dgx-spark:1.1.0-variant}"
LOCAL_NIM_CACHE="${LOCAL_NIM_CACHE:-$HOME/.cache/nim}"
SHM_SIZE="${SHM_SIZE:-108GB}"
PORT="${PORT:-8103}"

# Check if NGC_API_KEY is set, if not try to read from NGC config
if [ -z "$NGC_API_KEY" ]; then
    NGC_CONFIG="$HOME/.ngc/config"
    if [ -f "$NGC_CONFIG" ]; then
        NGC_API_KEY=$(grep "^apikey" "$NGC_CONFIG" | cut -d'=' -f2 | tr -d ' ')
        if [ -z "$NGC_API_KEY" ]; then
            echo "Error: Could not read API key from $NGC_CONFIG"
            exit 1
        fi
        echo "Using NGC API key from $NGC_CONFIG"
    else
        echo "Error: NGC_API_KEY environment variable is not set and $NGC_CONFIG not found"
        echo "Please set it with: export NGC_API_KEY=your_api_key"
        exit 1
    fi
fi

# Create cache directory if it doesn't exist
mkdir -p "$LOCAL_NIM_CACHE"

# Display configuration
echo "Starting NGC Container with configuration:"
echo "  Container Name: $CONTAINER_NAME"
echo "  Image: $IMG_NAME"
echo "  Cache Directory: $LOCAL_NIM_CACHE"
echo "  Shared Memory: $SHM_SIZE"
echo "  Port: $PORT"
echo ""

# Determine if we're in an interactive terminal
if [ -t 0 ]; then
    INTERACTIVE_FLAGS="-it"
else
    INTERACTIVE_FLAGS="-t"
fi

# Start the container
docker run $INTERACTIVE_FLAGS --rm \
  --name="$CONTAINER_NAME" \
  --runtime=nvidia \
  --gpus all \
  --shm-size="$SHM_SIZE" \
  -e NGC_API_KEY="$NGC_API_KEY" \
  -v "$LOCAL_NIM_CACHE:/opt/nim/.cache" \
  -u "$(id -u)" \
  -p "$PORT:8000" \
  "$IMG_NAME"
