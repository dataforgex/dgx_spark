# TensorRT-LLM Qwen3-32B-FP4 Server (Text/Code Model)

This directory contains scripts for running **Qwen3-32B-FP4** using NVIDIA TensorRT-LLM, optimized for DGX Spark with Blackwell GPUs.

**Container Name:** `trtllm-qwen3-32b-fp4`
**Default Port:** `8203`
**Model:** `nvidia/Qwen3-32B-FP4`
**Type:** Text/Code Generation (Dense)
**Quantization:** FP4 (4-bit floating point)

## Model Architecture

- **Parameters:** 32B (Dense - all parameters active)
- **Quantization:** FP4
- **Use Cases:** Code generation, text completion, chat, reasoning, complex tasks

## Qwen3-30B-A3B vs Qwen3-32B

| Aspect | Qwen3-30B-A3B (Port 8202) | Qwen3-32B (This - Port 8203) |
|--------|---------------------------|------------------------------|
| Architecture | MoE (Mixture of Experts) | Dense |
| Total Params | 30B | 32B |
| Active Params | 3B | 32B (all) |
| Memory | Lower | Higher |
| Speed | Faster | Slower |
| Quality | Good | Better for complex tasks |

**Choose 30B-A3B** for faster inference and lower memory usage.
**Choose 32B** for maximum quality on complex reasoning tasks.

## Prerequisites

1. **DGX Spark** with Blackwell GPU or compatible NVIDIA GPU with CUDA 12.x
2. **HuggingFace Token** - Get one at https://huggingface.co/settings/tokens
3. **Model Access** - Accept the license at https://huggingface.co/nvidia/Qwen3-32B-FP4
4. **Docker** with NVIDIA GPU support

## Quick Start

### 1. Set your HuggingFace Token

```bash
export HF_TOKEN="your-huggingface-token-here"
```

### 2. Start the Server

```bash
./serve.sh
```

The server will be available at `http://localhost:8203` with OpenAI-compatible API endpoints.

### Managing the Server

```bash
# Stop the server
docker stop trtllm-qwen3-32b-fp4

# Start the server (fast - model already cached)
docker start trtllm-qwen3-32b-fp4

# Restart the server
docker restart trtllm-qwen3-32b-fp4

# View logs
docker logs -f trtllm-qwen3-32b-fp4

# Remove container (to start fresh)
docker rm -f trtllm-qwen3-32b-fp4
```

## Configuration

Edit the variables at the top of `serve.sh` to customize:

### Key Settings
- `PORT=8203` - Server port (TRT-LLM range: 820x)
- `MAX_BATCH_SIZE=64` - Maximum concurrent batch size
- `FREE_GPU_MEMORY_FRACTION=0.9` - GPU memory for KV cache

## Testing the Server

### Basic Chat Test

```bash
curl -s http://localhost:8203/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nvidia/Qwen3-32B-FP4",
    "messages": [{"role": "user", "content": "Explain quantum computing in simple terms"}],
    "max_tokens": 500
  }'
```

### Code Generation Test

```bash
curl -s http://localhost:8203/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nvidia/Qwen3-32B-FP4",
    "messages": [
      {"role": "system", "content": "You are a helpful coding assistant."},
      {"role": "user", "content": "Write a REST API in Python using FastAPI with CRUD operations for a todo list."}
    ],
    "max_tokens": 1500,
    "temperature": 0.7
  }'
```

## Usage with Python

```python
import requests

response = requests.post(
    "http://localhost:8203/v1/chat/completions",
    json={
        "model": "nvidia/Qwen3-32B-FP4",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What are the key differences between TCP and UDP?"}
        ],
        "max_tokens": 500,
        "temperature": 0.7
    }
)

print(response.json()['choices'][0]['message']['content'])
```

## Usage with OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8203/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="nvidia/Qwen3-32B-FP4",
    messages=[
        {"role": "user", "content": "Write a haiku about programming"}
    ],
    max_tokens=100
)

print(response.choices[0].message.content)
```

## Troubleshooting

### HuggingFace Token Issues
```
ERROR: HF_TOKEN environment variable is not set!
```
Solution: `export HF_TOKEN="your-token-here"`

### Model Access Denied
Make sure you've accepted the model license at:
https://huggingface.co/nvidia/Qwen3-32B-FP4

### Out of Memory
This is a dense 32B model and requires significant GPU memory.
- Reduce `MAX_BATCH_SIZE` from 64 to 16 or 8
- Reduce `FREE_GPU_MEMORY_FRACTION` to 0.7
- Consider using Qwen3-30B-A3B-FP4 (port 8202) for lower memory

### Container Won't Start
Check if port 8203 is already in use:
```bash
lsof -i :8203
```

## Port Summary (TRT-LLM Models)

| Model | Port | Type | Architecture |
|-------|------|------|--------------|
| Qwen2.5-VL-7B-FP8 | 8200 | Vision | Dense |
| Qwen2.5-VL-7B-FP4 | 8201 | Vision | Dense |
| Qwen3-30B-A3B-FP4 | 8202 | Text/Code | MoE |
| **Qwen3-32B-FP4** | **8203** | **Text/Code** | **Dense** |

## References

- [NVIDIA TRT-LLM DGX Spark Guide](https://build.nvidia.com/spark/trt-llm/instructions)
- [Qwen3-32B Model Card](https://huggingface.co/nvidia/Qwen3-32B-FP4)
- [TensorRT-LLM Documentation](https://nvidia.github.io/TensorRT-LLM/)
