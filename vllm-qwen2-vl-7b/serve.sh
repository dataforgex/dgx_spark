#!/bin/bash

# vLLM Server v2 - Qwen2-VL-7B-Instruct (Vision Language Model)
# Features:
# - Vision understanding (images, documents, screenshots)
# - Persistent model cache (no re-downloading)
# - Named container for easy management
# - Optimized for multi-model deployment

# ==============================================================================
# Configuration Variables - Modify these as needed
# ==============================================================================

# Container configuration
CONTAINER_NAME="vllm-qwen2-vl-7b"

# Model configuration
MODEL_NAME="Qwen/Qwen2-VL-7B-Instruct"
PORT=8101  # Different port from Qwen3-Coder (8100)

# Cache directory for persistent model storage (avoids re-downloading)
HF_CACHE_DIR="${HOME}/.cache/huggingface"
mkdir -p "${HF_CACHE_DIR}"

# Context window and concurrency settings
MAX_MODEL_LEN=32768              # Maximum context length (32K tokens)
MAX_NUM_SEQS=64                  # Lower concurrency for vision model
GPU_MEMORY_UTILIZATION=0.25      # Use 25% of GPU memory (multi-model serving: 55% Qwen3-Coder + 25% VL = 80% total)

# Performance optimization flags
ENABLE_PREFIX_CACHING=true       # Enable automatic prefix caching
ENABLE_CHUNKED_PREFILL=true      # Reduce latency for long prompts
DTYPE="auto"                     # Automatic dtype selection

# Tool calling settings
ENABLE_AUTO_TOOL_CHOICE=true     # Enable automatic tool choice
TOOL_CALL_PARSER="hermes"        # Tool call parser (hermes works well with Qwen)

# Vision-specific settings
# Qwen2-VL supports image inputs through the chat API
# Max image size will be handled automatically

# Optional: Multi-GPU settings (uncomment if using multiple GPUs)
# TENSOR_PARALLEL_SIZE=2         # Number of GPUs for tensor parallelism
# PIPELINE_PARALLEL_SIZE=1       # Number of GPUs for pipeline parallelism

# ==============================================================================
# Check if container already exists
# ==============================================================================

if [ "$(docker ps -aq -f name=^${CONTAINER_NAME}$)" ]; then
    echo "Container '${CONTAINER_NAME}' already exists."
    if [ "$(docker ps -q -f name=^${CONTAINER_NAME}$)" ]; then
        echo "Container is already running!"
        echo ""
        echo "To view logs: docker logs -f ${CONTAINER_NAME}"
        echo "To stop: docker stop ${CONTAINER_NAME}"
        exit 0
    else
        echo "Removing stopped container..."
        docker rm ${CONTAINER_NAME}
    fi
fi

# ==============================================================================
# Build Docker Command
# ==============================================================================

DOCKER_CMD="docker run -d \
  --name ${CONTAINER_NAME} \
  --gpus all \
  --ipc=host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -p ${PORT}:8000 \
  -v ${HF_CACHE_DIR}:/root/.cache/huggingface \
  --restart unless-stopped \
  nvcr.io/nvidia/vllm:25.09-py3 \
  vllm serve \"${MODEL_NAME}\" \
  --max-model-len ${MAX_MODEL_LEN} \
  --max-num-seqs ${MAX_NUM_SEQS} \
  --gpu-memory-utilization ${GPU_MEMORY_UTILIZATION} \
  --dtype ${DTYPE}"

# Add optional features
if [ "$ENABLE_PREFIX_CACHING" = true ]; then
  DOCKER_CMD="$DOCKER_CMD --enable-prefix-caching"
fi

if [ "$ENABLE_CHUNKED_PREFILL" = true ]; then
  DOCKER_CMD="$DOCKER_CMD --enable-chunked-prefill"
fi

# Add tool calling settings
if [ "$ENABLE_AUTO_TOOL_CHOICE" = true ]; then
  DOCKER_CMD="$DOCKER_CMD --enable-auto-tool-choice --tool-call-parser ${TOOL_CALL_PARSER}"
fi

# Add multi-GPU settings if defined
if [ -n "$TENSOR_PARALLEL_SIZE" ]; then
  DOCKER_CMD="$DOCKER_CMD --tensor-parallel-size ${TENSOR_PARALLEL_SIZE}"
fi

if [ -n "$PIPELINE_PARALLEL_SIZE" ]; then
  DOCKER_CMD="$DOCKER_CMD --pipeline-parallel-size ${PIPELINE_PARALLEL_SIZE}"
fi

# ==============================================================================
# Run the server
# ==============================================================================

echo "=================================================="
echo "Starting vLLM Server - Qwen2-VL-7B (Vision)"
echo "=================================================="
echo "Container Name: ${CONTAINER_NAME}"
echo "Model: ${MODEL_NAME}"
echo "Port: ${PORT}"
echo "Max Context Length: ${MAX_MODEL_LEN}"
echo "Max Concurrent Sequences: ${MAX_NUM_SEQS}"
echo "GPU Memory Utilization: ${GPU_MEMORY_UTILIZATION}"
echo "Cache Directory: ${HF_CACHE_DIR}"
echo "=================================================="
echo ""
echo "⚠️  IMPORTANT: This is a vision model!"
echo "    - Supports image inputs via base64 or URLs"
echo "    - Use OpenAI-compatible vision API format"
echo "    - Can read: images, PDF screenshots, Excel screenshots"
echo ""

# Execute the command
eval $DOCKER_CMD

if [ $? -eq 0 ]; then
    echo "✓ Container started successfully!"
    echo ""
    echo "API will be available at: http://localhost:${PORT}"
    echo "OpenAI-compatible endpoint: http://localhost:${PORT}/v1"
    echo ""
    echo "Useful commands:"
    echo "  View logs:        docker logs -f ${CONTAINER_NAME}"
    echo "  Stop server:      docker stop ${CONTAINER_NAME}"
    echo "  Remove container: docker rm ${CONTAINER_NAME}"
    echo ""
    echo "The server is starting in the background..."
    echo "Model loading may take several minutes on first run (downloading ~14GB)."
    echo ""
    echo "Multi-model setup:"
    echo "  Qwen3-Coder-30B (40%):  http://localhost:8100  (text/code)"
    echo "  Qwen2-VL-7B (30%):      http://localhost:8101  (vision)"
    echo "  Total GPU usage:        70% (30% safety margin)"
    echo ""

    # Show initial logs
    echo "Initial logs (press Ctrl+C to exit log view):"
    echo "=================================================="
    docker logs -f ${CONTAINER_NAME}
else
    echo "✗ Failed to start container"
    exit 1
fi
