#!/bin/bash

# vLLM Server - Qwen3-Coder-30B AWQ
# Optimized for DGX Spark (GB10 Blackwell)
#
# Settings: 64K context, 8 concurrent, ~45 GB memory
# Performance: 0.069s TTFT, 52 TPS

# ==============================================================================
# Configuration Variables
# ==============================================================================

CONTAINER_NAME="vllm-qwen3-coder-30b-awq"

# AWQ quantized model
MODEL_NAME="cpatonn/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit"
PORT=8104

# Cache directory
HF_CACHE_DIR="${HOME}/.cache/huggingface"
mkdir -p "${HF_CACHE_DIR}"

# Context and concurrency - optimized for DGX Spark
MAX_MODEL_LEN=65536              # 64K context
MAX_NUM_SEQS=8                   # 8 concurrent sequences

# GPU memory utilization - sized for 8 concurrent 64K sequences
# Note: 0.9 would pre-allocate 90% regardless of need
# With 8 seqs @ 64K, we need ~40-45GB total (model + KV cache)
GPU_MEMORY_UTILIZATION=0.4

# FP8 KV Cache - NOT YET SUPPORTED on GB10/Blackwell
# vLLM V1 engine doesn't support fp8 kv cache, V0 uses incompatible Hopper kernels
# TODO: Re-enable when vLLM adds Blackwell FP8 KV cache support
KV_CACHE_DTYPE="auto"

# Performance flags
ENABLE_PREFIX_CACHING=true
ENABLE_CHUNKED_PREFILL=true
DTYPE="auto"
SWAP_SPACE=16                    # 16GB swap for context overflow

# Qwen-specific
ENABLE_AUTO_TOOL_CHOICE=true
TOOL_CALL_PARSER="qwen3_coder"

# ==============================================================================
# DGX Spark UMA Optimization: Clear system page cache
# Recommended by NVIDIA for unified memory systems
# ==============================================================================

echo "Clearing system page cache (recommended for DGX Spark UMA)..."
if [ -w /proc/sys/vm/drop_caches ]; then
    sync
    echo 3 > /proc/sys/vm/drop_caches
    echo "Page cache cleared."
else
    echo "Note: Run 'sudo sh -c \"sync; echo 3 > /proc/sys/vm/drop_caches\"' for optimal performance"
fi

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
  --kv-cache-dtype ${KV_CACHE_DTYPE} \
  --dtype ${DTYPE} \
  --swap-space ${SWAP_SPACE}"

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
echo "Container: ${CONTAINER_NAME}"
echo "Model: ${MODEL_NAME}"
echo "Port: ${PORT}"
echo "Context: ${MAX_MODEL_LEN} tokens"
echo "Concurrent: ${MAX_NUM_SEQS} sequences"
echo "GPU Memory: ${GPU_MEMORY_UTILIZATION}"
echo "Swap Space: ${SWAP_SPACE} GB"
echo "Expected RAM: ~45 GB"
echo "=================================================="
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
