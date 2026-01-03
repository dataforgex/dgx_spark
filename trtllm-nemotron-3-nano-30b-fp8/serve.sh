#!/bin/bash

# TensorRT-LLM Server - NVIDIA Nemotron-3-Nano-30B-A3B-FP8
# Hybrid Mamba-2 + Transformer MoE (30B params, 3.5B active)
# FP8 quantized with TRT-LLM AutoDeploy
# https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER_NAME="trtllm-nemotron-3-nano-30b-fp8"
MODEL_NAME="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8"
PORT=8107

# Cache directory for persistent model storage
HF_CACHE_DIR="${HOME}/.cache/huggingface"
mkdir -p "${HF_CACHE_DIR}"

# Check if container already exists
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

echo "=================================================="
echo "Starting TRT-LLM Nemotron-3-Nano-30B-FP8"
echo "=================================================="
echo "Container: ${CONTAINER_NAME}"
echo "Model: ${MODEL_NAME}"
echo "API: http://localhost:${PORT}/v1"
echo "=================================================="
echo ""

# Run TensorRT-LLM container with trtllm-serve
docker run -d \
  --name ${CONTAINER_NAME} \
  --gpus all \
  --ipc=host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -p ${PORT}:8000 \
  -v ${HF_CACHE_DIR}:/root/.cache/huggingface \
  -v ${SCRIPT_DIR}/nano_v3.yaml:/workspace/nano_v3.yaml \
  --restart unless-stopped \
  -e TRTLLM_ENABLE_PDL=1 \
  nvcr.io/nvidia/tensorrt-llm/release:1.2.0rc5 \
  trtllm-serve "${MODEL_NAME}" \
    --host 0.0.0.0 \
    --port 8000 \
    --backend _autodeploy \
    --trust_remote_code \
    --reasoning_parser deepseek-r1 \
    --tool_parser qwen3_coder \
    --extra_llm_api_options /workspace/nano_v3.yaml

if [ $? -eq 0 ]; then
    echo "Container started successfully!"
    echo ""
    echo "API will be available at: http://localhost:${PORT}"
    echo "OpenAI-compatible endpoint: http://localhost:${PORT}/v1"
    echo ""
    echo "Useful commands:"
    echo "  View logs:   docker logs -f ${CONTAINER_NAME}"
    echo "  Stop:        ./stop.sh"
    echo ""
    echo "Model loading may take several minutes on first run."
    echo "(TRT-LLM will auto-compile the engine)"

    # Only follow logs if running interactively (not from model-manager)
    if [ -t 1 ]; then
        echo ""
        echo "Initial logs (press Ctrl+C to exit log view):"
        echo "=================================================="
        docker logs -f ${CONTAINER_NAME}
    fi
else
    echo "Failed to start container"
    exit 1
fi
