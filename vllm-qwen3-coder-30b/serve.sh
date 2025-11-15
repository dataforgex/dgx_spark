#!/bin/bash

# vLLM Server Configuration for Qwen3-Coder-30B-A3B-Instruct
# This script runs the vLLM OpenAI-compatible API server with optimized settings

# ==============================================================================
# Configuration Variables - Modify these as needed
# ==============================================================================

# Model configuration
MODEL_NAME="Qwen/Qwen3-Coder-30B-A3B-Instruct"
PORT=8000

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
# Build Docker Command
# ==============================================================================

DOCKER_CMD="docker run --rm \
  --gpus all \
  --ipc=host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -p ${PORT}:8000 \
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
echo "Starting vLLM Server"
echo "=================================================="
echo "Model: ${MODEL_NAME}"
echo "Port: ${PORT}"
echo "Max Context Length: ${MAX_MODEL_LEN}"
echo "Max Concurrent Sequences: ${MAX_NUM_SEQS}"
echo "GPU Memory Utilization: ${GPU_MEMORY_UTILIZATION}"
echo "=================================================="
echo ""
echo "API will be available at: http://localhost:${PORT}"
echo "OpenAI-compatible endpoint: http://localhost:${PORT}/v1"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=================================================="
echo ""

# Execute the command
eval $DOCKER_CMD
