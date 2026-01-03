#!/bin/bash
pkill -f "vllm serve.*FP8" && echo "vLLM FP8 stopped" || echo "No vLLM FP8 process found"
