#!/bin/bash

# Start Qwen3-VL-30B server using NVIDIA PyTorch Container (GPU Support)
# This avoids vLLM/Triton compatibility issues on GB10/ARM64 by using native Transformers
# inside an NVIDIA-optimized PyTorch container.

IMAGE="nvcr.io/nvidia/pytorch:24.10-py3"
CONTAINER_NAME="qwen3-vl-server"
PORT=8102
MODEL_CACHE="$HOME/.cache/huggingface"

# Ensure model cache exists
mkdir -p "$MODEL_CACHE"

# Check if container is already running
if docker ps | grep -q "$CONTAINER_NAME"; then
    echo "Container $CONTAINER_NAME is already running."
    echo "To stop it: docker stop $CONTAINER_NAME && docker rm $CONTAINER_NAME"
    exit 1
fi

# Remove stopped container if it exists
if docker ps -a | grep -q "$CONTAINER_NAME"; then
    echo "Removing old container..."
    docker rm "$CONTAINER_NAME"
fi

echo "Starting GPU Server with NVIDIA PyTorch container..."
echo "Image: $IMAGE"
echo "Port: $PORT"
echo "Model Cache: $MODEL_CACHE"
echo ""
echo "NOTE: This will first install dependencies (transformers, etc.) inside the container,"
echo "      then load the model. This may take a few minutes."
echo ""

docker run -d \
  --name "$CONTAINER_NAME" \
  --gpus all \
  --ipc=host \
  -p "$PORT:$PORT" \
  -v "$(pwd):/workspace" \
  -v "$MODEL_CACHE:/root/.cache/huggingface" \
  -e USE_FLASH_ATTN=0 \
  "$IMAGE" \
  bash -c "pip install transformers accelerate qwen-vl-utils fastapi uvicorn[standard] && \
           cd /workspace && python3 serve_transformers.py --host 0.0.0.0 --port $PORT"

echo "Container started!"
echo "To follow logs and see when it's ready:"
echo "  docker logs -f $CONTAINER_NAME"
