#!/bin/bash
# Start vLLM distributed inference server
# Requires Ray cluster to be running (./start-cluster.sh)

set -e

#=============================================================================
# CONFIGURATION - Edit these variables to customize your setup
#=============================================================================

# Model to serve (must be accessible in HuggingFace cache)
MODEL="Qwen/Qwen3-Coder-30B-A3B-Instruct"

# Tensor parallelism (number of GPUs across nodes)
TENSOR_PARALLEL_SIZE=2

# Maximum context length
MAX_MODEL_LEN=32768

# GPU memory utilization (0.0-1.0)
GPU_MEMORY_UTILIZATION=0.80

# API port
PORT=8000

#=============================================================================

echo "=== Starting vLLM Distributed Server ==="
echo "  Model: $MODEL"
echo "  Tensor Parallel Size: $TENSOR_PARALLEL_SIZE"
echo "  Max Model Length: $MAX_MODEL_LEN"
echo "  GPU Memory Utilization: $GPU_MEMORY_UTILIZATION"
echo "  Port: $PORT"
echo ""

# Find the running container
CONTAINER=$(docker ps --format '{{.Names}}' | grep -E '^node-[0-9]+$' | head -1)

if [ -z "$CONTAINER" ]; then
    echo "ERROR: No Ray container found. Start the cluster first:"
    echo "  ./start-cluster.sh"
    exit 1
fi

echo "Using container: $CONTAINER"
echo ""

# Check Ray cluster status
echo "Checking Ray cluster..."
GPU_COUNT=$(docker exec "$CONTAINER" ray status 2>/dev/null | grep -oP '\d+\.\d+/\d+\.\d+ GPU' | grep -oP '/\K\d+\.\d+' | head -1)
echo "Available GPUs: $GPU_COUNT"

if [ "$(echo "$GPU_COUNT < $TENSOR_PARALLEL_SIZE" | bc -l)" -eq 1 ]; then
    echo "WARNING: Not enough GPUs for tensor parallel size $TENSOR_PARALLEL_SIZE"
fi

echo ""
echo "Starting vLLM server..."
echo "(This may take 1-2 minutes for model loading and CUDA graph compilation)"
echo ""

# Start vLLM server
docker exec -d "$CONTAINER" /bin/bash -c "vllm serve $MODEL \
    --tensor-parallel-size $TENSOR_PARALLEL_SIZE \
    --max-model-len $MAX_MODEL_LEN \
    --gpu-memory-utilization $GPU_MEMORY_UTILIZATION \
    --port $PORT \
    2>&1 | tee /tmp/vllm_serve.log"

# Wait for server to start
echo "Waiting for server to start..."
for i in {1..120}; do
    if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
        echo ""
        echo "=== Server is ready! ==="
        echo "  API: http://localhost:$PORT"
        echo "  Health: http://localhost:$PORT/health"
        echo "  Docs: http://localhost:$PORT/docs"
        echo ""
        echo "Test with: ./test-server.sh"
        exit 0
    fi
    sleep 2
    printf "."
done

echo ""
echo "Server may still be starting. Check logs:"
echo "  docker exec $CONTAINER cat /tmp/vllm_serve.log | tail -30"
