#!/bin/bash

# vLLM Server - Ministral-3-14B-Instruct (Vision Language Model)
# Features:
# - Vision understanding (images, documents, screenshots)
# - Function calling / tool use support
# - Persistent model cache (no re-downloading)
# - Named container for easy management
# - FP8 weights for efficient inference

# ==============================================================================
# Configuration Variables - Modify these as needed
# ==============================================================================

# Container configuration
CONTAINER_NAME="vllm-ministral3-14b"

# Model configuration
MODEL_NAME="mistralai/Ministral-3-14B-Instruct-2512"
PORT=8103  # Different port from other models (8100=Qwen3-Coder, 8101=Qwen2-VL, 8102=Qwen3-VL)

# Cache directory for persistent model storage (avoids re-downloading)
HF_CACHE_DIR="${HOME}/.cache/huggingface"
mkdir -p "${HF_CACHE_DIR}"

# Context window and concurrency settings
MAX_MODEL_LEN=32768              # Maximum context length (model supports up to 256K)
MAX_NUM_SEQS=64                  # Lower concurrency for vision model
GPU_MEMORY_UTILIZATION=0.30     # Use 30% of GPU memory (fits in ~24GB VRAM with FP8)

# Performance optimization flags
ENABLE_PREFIX_CACHING=true       # Enable automatic prefix caching
ENABLE_CHUNKED_PREFILL=true      # Reduce latency for long prompts

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
  nvcr.io/nvidia/vllm:25.11-py3 \
  vllm serve \"${MODEL_NAME}\" \
  --tokenizer_mode mistral \
  --config_format mistral \
  --load_format mistral \
  --enable-auto-tool-choice \
  --tool-call-parser mistral \
  --max-model-len ${MAX_MODEL_LEN} \
  --max-num-seqs ${MAX_NUM_SEQS} \
  --gpu-memory-utilization ${GPU_MEMORY_UTILIZATION} \
  --allowed-origins '[\"*\"]'"

# Add optional features
if [ "$ENABLE_PREFIX_CACHING" = true ]; then
  DOCKER_CMD="$DOCKER_CMD --enable-prefix-caching"
fi

if [ "$ENABLE_CHUNKED_PREFILL" = true ]; then
  DOCKER_CMD="$DOCKER_CMD --enable-chunked-prefill"
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
echo "Starting vLLM Server - Ministral-3-14B (Vision)"
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
echo "Features:"
echo "    - Vision model (image understanding)"
echo "    - Function calling / tool use support"
echo "    - FP8 weights for efficient inference"
echo "    - Mistral tokenizer mode enabled"
echo ""

# Execute the command
eval $DOCKER_CMD

if [ $? -eq 0 ]; then
    echo "Container started successfully!"
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
    echo "Model loading may take several minutes on first run."
    echo ""

    # Show initial logs
    echo "Initial logs (press Ctrl+C to exit log view):"
    echo "=================================================="
    docker logs -f ${CONTAINER_NAME}
else
    echo "Failed to start container"
    exit 1
fi
