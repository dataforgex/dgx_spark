#!/bin/bash
# Start Ray cluster on both DGX Spark nodes
# Run this from spark-1 (192.168.100.10)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HEAD_NODE_IP="192.168.100.10"
WORKER_NODE_IP="192.168.100.11"

echo "=== Starting Distributed Ray Cluster ==="
echo ""

# Stop any existing containers
echo "Cleaning up existing containers..."
"$SCRIPT_DIR/stop-cluster.sh" 2>/dev/null || true
sleep 2

# Start head node in background
echo ""
echo "Starting head node on spark-1 ($HEAD_NODE_IP)..."
cd "$SCRIPT_DIR"
nohup bash start-head.sh > /tmp/ray-head.log 2>&1 &
HEAD_PID=$!
echo "Head node starting (PID: $HEAD_PID)"

# Wait for head node to be ready
echo "Waiting for head node to initialize..."
sleep 15

# Copy scripts to worker if needed
echo ""
echo "Syncing scripts to worker node..."
scp -q "$SCRIPT_DIR/run_cluster.sh" "$SCRIPT_DIR/start-worker.sh" \
    "$WORKER_NODE_IP:$SCRIPT_DIR/" 2>/dev/null || true

# Start worker node on spark-2
echo ""
echo "Starting worker node on spark-2 ($WORKER_NODE_IP)..."
ssh "$WORKER_NODE_IP" "cd $SCRIPT_DIR && nohup bash start-worker.sh > /tmp/ray-worker.log 2>&1 &"
echo "Worker node starting..."

# Wait for worker to join
echo "Waiting for worker to join cluster..."
sleep 15

# Verify cluster status
echo ""
echo "=== Ray Cluster Status ==="
CONTAINER=$(docker ps --format '{{.Names}}' | grep -E '^node-[0-9]+$' | head -1)
if [ -n "$CONTAINER" ]; then
    docker exec "$CONTAINER" ray status
    echo ""
    echo "Cluster is ready!"
    echo "Container name: $CONTAINER"
    echo ""
    echo "Next steps:"
    echo "  1. Run: ./serve.sh"
    echo "  2. Test: ./test-server.sh"
else
    echo "ERROR: Could not find Ray container"
    echo "Check logs: cat /tmp/ray-head.log"
    exit 1
fi
