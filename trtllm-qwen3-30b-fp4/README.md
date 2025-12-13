# TensorRT-LLM Qwen3-30B-A3B-FP4 Server (Text/Code Model)

This directory contains scripts for running **Qwen3-30B-A3B-FP4** using NVIDIA TensorRT-LLM, optimized for DGX Spark with Blackwell GPUs.

**Container Name:** `trtllm-qwen3-30b-fp4`
**Default Port:** `8202`
**Model:** `nvidia/Qwen3-30B-A3B-FP4`
**Type:** Text/Code Generation (MoE)
**Quantization:** FP4 (4-bit floating point)

## Model Architecture

- **Total Parameters:** 30B
- **Active Parameters:** 3B (MoE - Mixture of Experts)
- **Quantization:** FP4
- **Use Cases:** Code generation, text completion, chat, reasoning

## Prerequisites

1. **DGX Spark** with Blackwell GPU or compatible NVIDIA GPU with CUDA 12.x
2. **HuggingFace Token** - Get one at https://huggingface.co/settings/tokens
3. **Model Access** - Accept the license at https://huggingface.co/nvidia/Qwen3-30B-A3B-FP4
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

The server will be available at `http://localhost:8202` with OpenAI-compatible API endpoints.

### Managing the Server

```bash
# Stop the server
docker stop trtllm-qwen3-30b-fp4

# Start the server (fast - model already cached)
docker start trtllm-qwen3-30b-fp4

# Restart the server
docker restart trtllm-qwen3-30b-fp4

# View logs
docker logs -f trtllm-qwen3-30b-fp4

# Remove container (to start fresh)
docker rm -f trtllm-qwen3-30b-fp4
```

## Comparison: TRT-LLM vs vLLM for Qwen3-30B

| Aspect | TRT-LLM FP4 (This) | vLLM (Full Precision) |
|--------|--------------------|-----------------------|
| Engine | TensorRT-LLM | vLLM |
| Quantization | FP4 | None (BF16) |
| Memory Usage | ~15-20 GB (estimated) | ~68 GB |
| Speed | Optimized for Blackwell | General purpose |
| Target | DGX Spark | Any NVIDIA GPU |

## Configuration

Edit the variables at the top of `serve.sh` to customize:

### Key Settings
- `PORT=8202` - Server port (TRT-LLM range: 820x)
- `MAX_BATCH_SIZE=64` - Maximum concurrent batch size
- `FREE_GPU_MEMORY_FRACTION=0.9` - GPU memory for KV cache

### TRT-LLM Specific Options
The script creates a YAML config with these optimizations:
```yaml
kv_cache_config:
  dtype: auto
  free_gpu_memory_fraction: 0.9
cuda_graph_config:
  enable_padding: true
disable_overlap_scheduler: true
```

## Testing the Server

### Basic Chat Test

```bash
curl -s http://localhost:8202/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nvidia/Qwen3-30B-A3B-FP4",
    "messages": [{"role": "user", "content": "Write a Python function to calculate fibonacci numbers"}],
    "max_tokens": 500
  }'
```

### Code Generation Test

```bash
curl -s http://localhost:8202/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nvidia/Qwen3-30B-A3B-FP4",
    "messages": [
      {"role": "system", "content": "You are a helpful coding assistant."},
      {"role": "user", "content": "Implement a binary search tree in Python with insert, search, and delete methods."}
    ],
    "max_tokens": 1000,
    "temperature": 0.7
  }'
```

## Usage with Python

```python
import requests

response = requests.post(
    "http://localhost:8202/v1/chat/completions",
    json={
        "model": "nvidia/Qwen3-30B-A3B-FP4",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Explain how neural networks work in simple terms."}
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
    base_url="http://localhost:8202/v1",
    api_key="not-needed"  # TRT-LLM doesn't require API key
)

response = client.chat.completions.create(
    model="nvidia/Qwen3-30B-A3B-FP4",
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
https://huggingface.co/nvidia/Qwen3-30B-A3B-FP4

### Out of Memory
- Reduce `MAX_BATCH_SIZE` from 64 to 32 or 16
- Reduce `FREE_GPU_MEMORY_FRACTION` to 0.7

### Container Won't Start
Check if port 8202 is already in use:
```bash
lsof -i :8202
```

## Port Summary (TRT-LLM Models)

| Model | Port | Type | Quantization |
|-------|------|------|--------------|
| Qwen2.5-VL-7B-FP8 | 8200 | Vision | FP8 |
| Qwen2.5-VL-7B-FP4 | 8201 | Vision | FP4 |
| **Qwen3-30B-A3B-FP4** | **8202** | **Text/Code** | **FP4** |

## References

- [NVIDIA TRT-LLM DGX Spark Guide](https://build.nvidia.com/spark/trt-llm/instructions)
- [Qwen3-30B Model Card](https://huggingface.co/nvidia/Qwen3-30B-A3B-FP4)
- [TensorRT-LLM Documentation](https://nvidia.github.io/TensorRT-LLM/)
