#!/bin/bash
# Download Qwen3-235B-A22B-AWQ model
# Model size: ~116GB

set -e

MODEL="QuantTrio/Qwen3-235B-A22B-Instruct-2507-AWQ"

echo "=== Downloading Qwen3-235B-A22B-AWQ ==="
echo "Model: $MODEL"
echo "Size: ~116GB"
echo ""
echo "This will download to: ~/.cache/huggingface/hub/"
echo ""

# Check if huggingface-cli is available
if ! command -v huggingface-cli &> /dev/null; then
    echo "Installing huggingface_hub..."
    pip install -q huggingface_hub
fi

# Download model
echo "Starting download..."
huggingface-cli download "$MODEL"

echo ""
echo "=== Download Complete ==="
echo ""
echo "If using NFS shared storage, the model is now available on both nodes."
echo "Otherwise, run this script on spark-2 as well:"
echo "  ssh 192.168.100.11 \"huggingface-cli download $MODEL\""
echo ""
echo "Next steps:"
echo "  1. Start cluster: ./start-cluster.sh"
echo "  2. Start server: ./serve.sh"
