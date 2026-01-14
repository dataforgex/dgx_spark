#!/bin/bash
# Start Ray head node on spark-1
# Reference: https://build.nvidia.com/spark/vllm/stacked-sparks

set -e

# Configuration
VLLM_IMAGE="nvcr.io/nvidia/vllm:25.11-py3"
MN_IF_NAME="enp1s0f1np1"
VLLM_HOST_IP="192.168.100.10"
HF_CACHE="$HOME/.cache/huggingface"

echo "Starting Ray head node on spark-1..."
echo "  Image: $VLLM_IMAGE"
echo "  Interface: $MN_IF_NAME"
echo "  IP: $VLLM_HOST_IP"

# Check if run_cluster.sh exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -f "$SCRIPT_DIR/run_cluster.sh" ]; then
    echo "Downloading run_cluster.sh..."
    wget -O "$SCRIPT_DIR/run_cluster.sh" \
        https://raw.githubusercontent.com/vllm-project/vllm/refs/heads/main/examples/online_serving/run_cluster.sh
    chmod +x "$SCRIPT_DIR/run_cluster.sh"
fi

# Start head node
cd "$SCRIPT_DIR"
bash run_cluster.sh "$VLLM_IMAGE" "$VLLM_HOST_IP" --head "$HF_CACHE" \
    -e VLLM_HOST_IP="$VLLM_HOST_IP" \
    -e UCX_NET_DEVICES="$MN_IF_NAME" \
    -e NCCL_SOCKET_IFNAME="$MN_IF_NAME" \
    -e OMPI_MCA_btl_tcp_if_include="$MN_IF_NAME" \
    -e GLOO_SOCKET_IFNAME="$MN_IF_NAME" \
    -e TP_SOCKET_IFNAME="$MN_IF_NAME" \
    -e RAY_memory_monitor_refresh_ms=0 \
    -e MASTER_ADDR="$VLLM_HOST_IP"
