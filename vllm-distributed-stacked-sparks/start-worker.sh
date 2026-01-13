#!/bin/bash
# Start Ray worker node on spark-2
# Run this script on spark-2 (192.168.100.11)
# Reference: https://build.nvidia.com/spark/vllm/stacked-sparks
#
# Usage (from spark-1):
#   ssh 192.168.100.11 "bash /home/dan/danProjects/dgx_spark/vllm-distributed-stacked-sparks/start-worker.sh"
#
# Or on spark-2 directly:
#   cd /home/dan/danProjects/dgx_spark/vllm-distributed-stacked-sparks
#   ./start-worker.sh

set -e

# Configuration
VLLM_IMAGE="nvcr.io/nvidia/vllm:25.11-py3"
MN_IF_NAME="enp1s0f1np1"
VLLM_HOST_IP="192.168.100.11"
HEAD_NODE_IP="192.168.100.10"
HF_CACHE="$HOME/.cache/huggingface"

echo "Starting Ray worker node on spark-2..."
echo "  Image: $VLLM_IMAGE"
echo "  Interface: $MN_IF_NAME"
echo "  Worker IP: $VLLM_HOST_IP"
echo "  Head Node IP: $HEAD_NODE_IP"

# Check if run_cluster.sh exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -f "$SCRIPT_DIR/run_cluster.sh" ]; then
    echo "Downloading run_cluster.sh..."
    wget -O "$SCRIPT_DIR/run_cluster.sh" \
        https://raw.githubusercontent.com/vllm-project/vllm/refs/heads/main/examples/online_serving/run_cluster.sh
    chmod +x "$SCRIPT_DIR/run_cluster.sh"
fi

# Start worker node
cd "$SCRIPT_DIR"
bash run_cluster.sh "$VLLM_IMAGE" "$HEAD_NODE_IP" --worker "$HF_CACHE" \
    -e VLLM_HOST_IP="$VLLM_HOST_IP" \
    -e UCX_NET_DEVICES="$MN_IF_NAME" \
    -e NCCL_SOCKET_IFNAME="$MN_IF_NAME" \
    -e OMPI_MCA_btl_tcp_if_include="$MN_IF_NAME" \
    -e GLOO_SOCKET_IFNAME="$MN_IF_NAME" \
    -e TP_SOCKET_IFNAME="$MN_IF_NAME" \
    -e RAY_memory_monitor_refresh_ms=0 \
    -e MASTER_ADDR="$HEAD_NODE_IP"
