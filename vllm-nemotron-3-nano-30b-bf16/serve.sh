#!/bin/bash

# vLLM Server - NVIDIA Nemotron-3-Nano-30B-A3B-BF16
# Hybrid Mamba-2 + Transformer MoE (30B params, 3.5B active)
# https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16
# Reference: https://github.com/NVIDIA-NeMo/Nemotron/blob/main/usage-cookbook/Nemotron-3-Nano/vllm_cookbook.ipynb

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_NAME="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16"
PORT=8105

# CUDA libraries path (DGX Spark uses CUDA 13, but vLLM needs CUDA 12 libs)
export LD_LIBRARY_PATH="/usr/local/lib/ollama/cuda_v12:${LD_LIBRARY_PATH}"

# GB10 (sm_121a) compatibility: Disable Triton-based kernels
# Triton's ptxas doesn't support sm_121a yet
export VLLM_USE_TRITON_FLASH_ATTN=0
export VLLM_ATTENTION_BACKEND=FLASH_ATTN

# Memory settings (tested on DGX Spark GB10)
MAX_MODEL_LEN=16384
MAX_NUM_SEQS=8
GPU_MEMORY_UTILIZATION=0.85

# Activate virtual environment
source "${SCRIPT_DIR}/venv/bin/activate"

# Check if already running
if lsof -i:${PORT} >/dev/null 2>&1; then
    echo "Port ${PORT} is already in use!"
    echo "To stop: pkill -f 'vllm.entrypoints.openai.api_server'"
    exit 1
fi

echo "=================================================="
echo "Starting Nemotron-3-Nano-30B"
echo "=================================================="
echo "API: http://localhost:${PORT}/v1"
echo "Context: ${MAX_MODEL_LEN} tokens"
echo "=================================================="

# Launch per official HuggingFace documentation:
# https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16#use-it-with-vllm
# --enforce-eager: Required for GB10 (sm_121a) - Triton doesn't support this SM yet
exec vllm serve "${MODEL_NAME}" \
  --port ${PORT} \
  --max-model-len ${MAX_MODEL_LEN} \
  --max-num-seqs ${MAX_NUM_SEQS} \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization ${GPU_MEMORY_UTILIZATION} \
  --trust-remote-code \
  --enforce-eager \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --allowed-origins '["*"]' \
  --reasoning-parser-plugin "${SCRIPT_DIR}/nano_v3_reasoning_parser.py" \
  --reasoning-parser nano_v3
