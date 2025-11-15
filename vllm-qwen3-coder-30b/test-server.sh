#!/bin/bash

# Test script for vLLM server
# This script sends a sample request to the running vLLM server

PORT=${1:-8100}  # Default port for Qwen3-Coder-30B
HOST=${2:-localhost}

echo "Testing vLLM server at http://${HOST}:${PORT}"
echo "=================================================="
echo ""

curl "http://${HOST}:${PORT}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-Coder-30B-A3B-Instruct",
    "messages": [
      {"role": "user", "content": "Write a Python function to check if a number is prime"}
    ],
    "max_tokens": 500,
    "temperature": 0.7
  }' | jq '.'

echo ""
echo "=================================================="
echo "Test complete!"
echo ""
echo "Usage: $0 [PORT] [HOST]"
echo "Example: $0 8000 localhost"
