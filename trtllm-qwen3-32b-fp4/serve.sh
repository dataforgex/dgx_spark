#!/bin/bash

# TensorRT-LLM Server - Qwen3-32B-FP4 (Text/Code Model)
# Features:
# - NVIDIA TensorRT-LLM optimized inference
# - FP4 quantization for memory efficiency
# - 32B parameter dense model
# - Persistent model cache (no re-downloading)
# - Named container for easy management
# - OpenAI-compatible API

# ==============================================================================
# Configuration Variables - Modify these as needed
# ==============================================================================

# Container configuration
CONTAINER_NAME="trtllm-qwen3-32b-fp4"

# Model configuration (NVIDIA optimized FP4 quantized model)
MODEL_HANDLE="nvidia/Qwen3-32B-FP4"
PORT=8203  # TRT-LLM range: 820x

# HuggingFace token (required for gated models)
# Set this environment variable before running: export HF_TOKEN="your-token-here"
if [ -z "$HF_TOKEN" ]; then
    echo "ERROR: HF_TOKEN environment variable is not set!"
    echo "Please set it with: export HF_TOKEN='your-huggingface-token'"
    echo ""
    echo "You can get a token from: https://huggingface.co/settings/tokens"
    echo "Make sure you have accepted the model license at:"
    echo "https://huggingface.co/${MODEL_HANDLE}"
    exit 1
fi

# Cache directory for persistent model storage (avoids re-downloading)
HF_CACHE_DIR="${HOME}/.cache/huggingface"
mkdir -p "${HF_CACHE_DIR}"

# Server settings
MAX_BATCH_SIZE=64                # Maximum batch size for concurrent requests

# TRT-LLM specific configuration
FREE_GPU_MEMORY_FRACTION=0.9     # Use 90% of GPU memory for KV cache

# Docker image
DOCKER_IMAGE="nvcr.io/nvidia/tensorrt-llm/release:spark-single-gpu-dev"

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
# Create config file
# ==============================================================================

CONFIG_DIR="${HF_CACHE_DIR}/trtllm-configs"
mkdir -p "${CONFIG_DIR}"
CONFIG_FILE="${CONFIG_DIR}/qwen3-32b-fp4-config.yml"

cat > "${CONFIG_FILE}" << 'CONFIGEOF'
print_iter_log: false
kv_cache_config:
  dtype: auto
  free_gpu_memory_fraction: 0.9
cuda_graph_config:
  enable_padding: true
disable_overlap_scheduler: true
CONFIGEOF

echo "Created config file: ${CONFIG_FILE}"

# ==============================================================================
# Run the server
# ==============================================================================

echo "=================================================="
echo "Starting TensorRT-LLM Server - Qwen3-32B-FP4"
echo "=================================================="
echo "Container Name: ${CONTAINER_NAME}"
echo "Model: ${MODEL_HANDLE}"
echo "Port: ${PORT}"
echo "Max Batch Size: ${MAX_BATCH_SIZE}"
echo "GPU Memory Fraction: ${FREE_GPU_MEMORY_FRACTION}"
echo "Cache Directory: ${HF_CACHE_DIR}"
echo "Docker Image: ${DOCKER_IMAGE}"
echo "=================================================="
echo ""
echo "NOTE: This is a dense 32B parameter model"
echo "    - FP4 quantization for memory efficiency"
echo "    - Great for coding, reasoning, and text tasks"
echo ""

# Run the container
docker run -d \
  --name ${CONTAINER_NAME} \
  --gpus all \
  --ipc=host \
  --network host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -e HF_TOKEN=${HF_TOKEN} \
  -v ${HF_CACHE_DIR}:/root/.cache/huggingface \
  --restart unless-stopped \
  ${DOCKER_IMAGE} \
  bash -c "hf download ${MODEL_HANDLE} && trtllm-serve ${MODEL_HANDLE} --max_batch_size ${MAX_BATCH_SIZE} --trust_remote_code --port ${PORT} --extra_llm_api_options /root/.cache/huggingface/trtllm-configs/qwen3-32b-fp4-config.yml"

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
    echo "Test with:"
    echo "  curl -s http://localhost:${PORT}/v1/chat/completions \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{"
    echo "      \"model\": \"${MODEL_HANDLE}\","
    echo "      \"messages\": [{\"role\": \"user\", \"content\": \"Hello!\"}],"
    echo "      \"max_tokens\": 64"
    echo "    }'"
    echo ""

    # Show initial logs
    echo "Initial logs (press Ctrl+C to exit log view):"
    echo "=================================================="
    docker logs -f ${CONTAINER_NAME}
else
    echo "Failed to start container"
    exit 1
fi
