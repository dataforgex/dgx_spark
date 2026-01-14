#!/bin/bash
# Serve Qwen3-235B-A22B-AWQ using vLLM across two DGX Sparks
# Compatible with model-manager (exits quickly, runs in background)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

#=============================================================================
# CONFIGURATION
#=============================================================================

MODEL="QuantTrio/Qwen3-235B-A22B-Instruct-2507-AWQ"
TENSOR_PARALLEL_SIZE=2
MAX_MODEL_LEN=8192
GPU_MEMORY_UTILIZATION=0.75
SWAP_SPACE=16
PORT=8235

#=============================================================================

# Check if already running
if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
    echo "Server already running on port $PORT"
    exit 0
fi

# Find Ray container
CONTAINER=$(docker ps --format '{{.Names}}' | grep -E '^node-[0-9]+$' | head -1)

# Start cluster if not running (in background, don't wait)
if [ -z "$CONTAINER" ]; then
    echo "Starting Ray cluster in background..."
    nohup "$SCRIPT_DIR/start-cluster.sh" > /tmp/ray-cluster-start.log 2>&1 &

    # Wait up to 60s for cluster to start
    for i in {1..12}; do
        sleep 5
        CONTAINER=$(docker ps --format '{{.Names}}' | grep -E '^node-[0-9]+$' | head -1)
        if [ -n "$CONTAINER" ]; then
            echo "Cluster started: $CONTAINER"
            break
        fi
        echo "Waiting for cluster... ($((i*5))s)"
    done

    if [ -z "$CONTAINER" ]; then
        echo "ERROR: Cluster failed to start. Check /tmp/ray-cluster-start.log"
        exit 1
    fi

    # Wait for worker to join
    sleep 10
fi

echo "Using container: $CONTAINER"

# Check GPU count
GPU_COUNT=$(docker exec "$CONTAINER" ray status 2>/dev/null | grep -oP '\d+\.\d+/\d+\.\d+ GPU' | grep -oP '/\K\d+\.\d+' | head -1 || echo "0")
echo "Available GPUs: $GPU_COUNT"

# Start vLLM server (detached)
echo "Starting vLLM server on port $PORT..."
docker exec -d "$CONTAINER" /bin/bash -c "vllm serve $MODEL \
    --served-model-name qwen3-235b-awq \
    --tensor-parallel-size $TENSOR_PARALLEL_SIZE \
    --max-model-len $MAX_MODEL_LEN \
    --gpu-memory-utilization $GPU_MEMORY_UTILIZATION \
    --swap-space $SWAP_SPACE \
    --enforce-eager \
    --trust-remote-code \
    --disable-log-requests \
    --enable-auto-tool-choice \
    --tool-call-parser qwen3_xml \
    --allowed-origins '[\"*\"]' \
    --port $PORT \
    2>&1 | tee /tmp/vllm_serve.log"

echo "vLLM starting in background. Model loading takes 5-10 minutes."
echo "Check status: curl http://localhost:$PORT/health"
echo "Check logs: docker exec $CONTAINER tail -f /tmp/vllm_serve.log"
