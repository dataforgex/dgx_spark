#!/bin/bash

# vLLM Server - Qwen3-Coder-30B AWQ Optimized
# Changes from original:
# - AWQ 4-bit quantization (~4x less memory)
# - Higher GPU memory utilization (0.85 vs 0.55)
# - Optimized for single-model deployment

# ==============================================================================
# Configuration Variables
# ==============================================================================

CONTAINER_NAME="vllm-qwen3-coder-30b-awq"

# AWQ quantized model - ~4x smaller than full precision
MODEL_NAME="cpatonn/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit"
PORT=8104  # New port for optimized version

# Cache directory
HF_CACHE_DIR="${HOME}/.cache/huggingface"
mkdir -p "${HF_CACHE_DIR}"

# Context and concurrency
MAX_MODEL_LEN=32768              # 32K context
MAX_NUM_SEQS=256                 # Concurrent sequences

# OPTIMIZATION: Higher memory utilization (was 0.55)
GPU_MEMORY_UTILIZATION=0.85      # Use 85% of GPU - more KV cache

# Performance flags
ENABLE_PREFIX_CACHING=true
ENABLE_CHUNKED_PREFILL=true
DTYPE="auto"

# Qwen-specific
ENABLE_AUTO_TOOL_CHOICE=true
TOOL_CALL_PARSER="qwen3_coder"

# Quantization: auto-detect from model config
# (Model uses compressed-tensors format)
QUANTIZATION=""

# ==============================================================================
# Check if container exists
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

if [ "$ENABLE_AUTO_TOOL_CHOICE" = true ]; then
  DOCKER_CMD="$DOCKER_CMD --enable-auto-tool-choice --tool-call-parser ${TOOL_CALL_PARSER}"
fi

# ==============================================================================
# Run the server
# ==============================================================================

echo "=================================================="
echo "Starting vLLM Server - Qwen3-Coder-30B AWQ"
echo "=================================================="
echo "Container Name: ${CONTAINER_NAME}"
echo "Model: ${MODEL_NAME}"
echo "Port: ${PORT}"
echo "Quantization: ${QUANTIZATION}"
echo "Max Context: ${MAX_MODEL_LEN}"
echo "GPU Memory: ${GPU_MEMORY_UTILIZATION}"
echo "Cache: ${HF_CACHE_DIR}"
echo "=================================================="
echo ""
echo "OPTIMIZATIONS vs original:"
echo "  - AWQ 4-bit quantization (~4x less memory)"
echo "  - GPU memory: 85% (was 55%)"
echo "  - More KV cache for longer contexts"
echo ""

eval $DOCKER_CMD

if [ $? -eq 0 ]; then
    echo "Container started successfully!"
    echo ""
    echo "API: http://localhost:${PORT}/v1"
    echo ""
    echo "Commands:"
    echo "  Logs:   docker logs -f ${CONTAINER_NAME}"
    echo "  Stop:   docker stop ${CONTAINER_NAME}"
    echo "  Remove: docker rm ${CONTAINER_NAME}"
    echo ""
    echo "Model loading may take a few minutes..."
    echo ""
    docker logs -f ${CONTAINER_NAME}
else
    echo "Failed to start container"
    exit 1
fi
