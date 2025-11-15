#!/bin/bash

# vLLM Server v2 - Optimized for frequent restarts
# Features:
# - Persistent model cache (no re-downloading)
# - Named container for easy management
# - Detached mode with log viewing
# - Fast restart capability

# ==============================================================================
# Configuration Variables - Modify these as needed
# ==============================================================================

# Container configuration
CONTAINER_NAME="vllm-qwen3-coder-30b"  # Named container for easy management

# Model configuration
MODEL_NAME="Qwen/Qwen3-Coder-30B-A3B-Instruct"
PORT=8100  # Unique port for this model (avoid conflicts with other models)

# Cache directory for persistent model storage (avoids re-downloading)
HF_CACHE_DIR="${HOME}/.cache/huggingface"
mkdir -p "${HF_CACHE_DIR}"

# Context window and concurrency settings
MAX_MODEL_LEN=32768              # Maximum context length (32K tokens)
MAX_NUM_SEQS=256                 # Maximum concurrent sequences
GPU_MEMORY_UTILIZATION=0.85      # Use 85% of GPU memory (adjust based on available memory)

# Performance optimization flags
ENABLE_PREFIX_CACHING=true       # Enable automatic prefix caching
ENABLE_CHUNKED_PREFILL=true      # Reduce latency for long prompts
DTYPE="auto"                     # Automatic dtype selection

# Qwen-specific settings
ENABLE_AUTO_TOOL_CHOICE=true     # Enable automatic tool selection
TOOL_CALL_PARSER="qwen3_coder"   # Use Qwen3 Coder parser

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
        echo "To stop: ./stop.sh"
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
  DOCKER_CMD="$DOCKER_CMD --enable-auto-tool-choice"
fi

if [ -n "$TOOL_CALL_PARSER" ]; then
  DOCKER_CMD="$DOCKER_CMD --tool-call-parser ${TOOL_CALL_PARSER}"
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
echo "Starting vLLM Server (v2 - Persistent Cache)"
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
    echo "  Stop server:      ./stop.sh"
    echo "  Restart server:   ./restart.sh"
    echo "  Server status:    ./status.sh"
    echo ""
    echo "The server is starting in the background..."
    echo "Model loading may take a few minutes on first run."
    echo ""

    # Show initial logs
    echo "Initial logs (press Ctrl+C to exit log view):"
    echo "=================================================="
    docker logs -f ${CONTAINER_NAME}
else
    echo "✗ Failed to start container"
    exit 1
fi
