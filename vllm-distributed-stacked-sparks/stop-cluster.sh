#!/bin/bash
# Stop Ray cluster on both DGX Spark nodes

HEAD_NODE_IP="192.168.100.10"
WORKER_NODE_IP="192.168.100.11"

echo "Stopping Ray cluster..."

# Stop containers on head node (spark-1)
echo "Stopping containers on spark-1..."
for container in $(docker ps --format '{{.Names}}' | grep -E '^node-[0-9]+$'); do
    echo "  Stopping $container"
    docker stop "$container" 2>/dev/null || true
    docker rm "$container" 2>/dev/null || true
done

# Stop containers on worker node (spark-2)
echo "Stopping containers on spark-2..."
ssh "$WORKER_NODE_IP" 'for container in $(docker ps --format "{{.Names}}" | grep -E "^node-[0-9]+$"); do
    echo "  Stopping $container"
    docker stop "$container" 2>/dev/null || true
    docker rm "$container" 2>/dev/null || true
done' 2>/dev/null || true

echo "Cluster stopped."
