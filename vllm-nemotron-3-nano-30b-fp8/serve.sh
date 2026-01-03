#!/bin/bash

# vLLM Server - NVIDIA Nemotron-3-Nano-30B-A3B-FP8
# Hybrid Mamba-2 + Transformer MoE (30B params, 3.5B active)
# FP8 quantized - lower memory, faster inference
# https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_NAME="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8"
PORT=8106

# Memory settings (tested on DGX Spark GB10)
MAX_MODEL_LEN=16384
MAX_NUM_SEQS=8

# GB10 (SM 12.1) FP8 workarounds
# Use V0 engine - V1 has flashinfer FP8 GEMM issues on Blackwell
export VLLM_USE_V1=0
# Disable flashinfer FP8 GEMM
export VLLM_USE_FLASHINFER_MOE_FP8=0

# Activate virtual environment
source "${SCRIPT_DIR}/venv/bin/activate"

# Check if already running
if lsof -i:${PORT} >/dev/null 2>&1; then
    echo "Port ${PORT} is already in use!"
    echo "To stop: ./stop.sh"
    exit 1
fi

echo "=================================================="
echo "Starting Nemotron-3-Nano-30B-FP8"
echo "=================================================="
echo "API: http://localhost:${PORT}/v1"
echo "Context: ${MAX_MODEL_LEN} tokens"
echo "=================================================="

exec vllm serve "${MODEL_NAME}" \
  --port ${PORT} \
  --max-model-len ${MAX_MODEL_LEN} \
  --max-num-seqs ${MAX_NUM_SEQS} \
  --trust-remote-code \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --reasoning-parser-plugin "${SCRIPT_DIR}/nano_v3_reasoning_parser.py" \
  --reasoning-parser nano_v3 \
  --kv-cache-dtype fp8 \
  --enforce-eager
