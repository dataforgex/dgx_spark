#!/bin/bash

# Configuration
MODEL_NAME="qwen3-vl:32b"
CONTAINER_NAME="ollama-server"
PORT=11435

# Create volume for persistent models
docker volume create ollama_models

# Stop existing container if running
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

echo "🚀 Starting Ollama on port $PORT..."
echo "Model to pull: $MODEL_NAME"

# Run Ollama container
docker run -d \
    --name $CONTAINER_NAME \
    --gpus all \
    -p $PORT:11434 \
    -e OLLAMA_ORIGINS="*" \
    -v ollama_models:/root/.ollama \
    ollama/ollama:latest

echo "⏳ Waiting for Ollama to start..."
sleep 5

echo "⬇️  Pulling model $MODEL_NAME..."
docker exec $CONTAINER_NAME ollama pull $MODEL_NAME

echo "✅ Done! Model is ready."
echo "API Endpoint: http://localhost:$PORT"
