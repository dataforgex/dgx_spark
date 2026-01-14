#!/bin/bash
pkill -f "vllm serve" && echo "vLLM stopped" || echo "No vLLM process found"
