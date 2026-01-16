#!/bin/bash

# vLLM Server - Chandra OCR (Document Intelligence Model)
# Features:
# - OCR with full layout preservation (tables, forms, handwriting)
# - Math equation extraction as LaTeX
# - Multi-column document support
# - 40+ language support
# - Output: Markdown, HTML, JSON with bounding boxes

# ==============================================================================
# Configuration Variables - Modify these as needed
# ==============================================================================

# Container configuration
CONTAINER_NAME="vllm-chandra-ocr"

# Model configuration
MODEL_NAME="datalab-to/chandra"
PORT=8106

# Cache directory for persistent model storage (avoids re-downloading)
HF_CACHE_DIR="${HOME}/.cache/huggingface"
mkdir -p "${HF_CACHE_DIR}"

# Context window and concurrency settings
MAX_MODEL_LEN=16384              # Maximum context length
MAX_NUM_SEQS=8                   # Concurrent sequences
GPU_MEMORY_UTILIZATION=0.5       # Use 50% of GPU memory

# Performance optimization flags
ENABLE_PREFIX_CACHING=true       # Enable automatic prefix caching
ENABLE_CHUNKED_PREFILL=true      # Reduce latency for long prompts
DTYPE="auto"                     # Automatic dtype selection (BF16)
ENFORCE_EAGER=true               # Disable CUDA graphs (required for VL models on GB10)
TRUST_REMOTE_CODE=true           # Allow custom model code

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
  -e TORCH_CUDNN_V8_API_ENABLED=0 \
  -e CUDNN_FRONTEND_ATTN_DP_WORKSPACE_LIMIT=0 \
  -e TORCH_CUDNN_ENABLED=0 \
  --restart unless-stopped \
  nvcr.io/nvidia/vllm:25.11-py3 \
  vllm serve \"${MODEL_NAME}\" \
  --max-model-len ${MAX_MODEL_LEN} \
  --max-num-seqs ${MAX_NUM_SEQS} \
  --gpu-memory-utilization ${GPU_MEMORY_UTILIZATION} \
  --dtype ${DTYPE} \
  --allowed-origins '[\"*\"]'"

# Add optional features
if [ "$ENABLE_PREFIX_CACHING" = true ]; then
  DOCKER_CMD="$DOCKER_CMD --enable-prefix-caching"
fi

if [ "$ENABLE_CHUNKED_PREFILL" = true ]; then
  DOCKER_CMD="$DOCKER_CMD --enable-chunked-prefill"
fi

if [ "$ENFORCE_EAGER" = true ]; then
  DOCKER_CMD="$DOCKER_CMD --enforce-eager"
fi

if [ "$TRUST_REMOTE_CODE" = true ]; then
  DOCKER_CMD="$DOCKER_CMD --trust-remote-code"
fi

# Remove limit-mm-per-prompt for now - testing compatibility

# ==============================================================================
# Run the server
# ==============================================================================

echo "=================================================="
echo "Starting vLLM Server - Chandra OCR"
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
echo "Chandra OCR Features:"
echo "  - Handwriting recognition"
echo "  - Table extraction with structure"
echo "  - Math equations as LaTeX"
echo "  - Form reconstruction (checkboxes, fields)"
echo "  - 40+ language support"
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
    echo "Model loading may take several minutes on first run (downloading ~18GB)."
    echo ""

    # Show initial logs
    echo "Initial logs (press Ctrl+C to exit log view):"
    echo "=================================================="
    docker logs -f ${CONTAINER_NAME}
else
    echo "Failed to start container"
    exit 1
fi
