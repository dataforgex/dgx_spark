# TensorRT-LLM Qwen2.5-VL-7B-FP4 Server (Vision Model)

This directory contains scripts for running **Qwen2.5-VL-7B-Instruct-FP4** using NVIDIA TensorRT-LLM, optimized for DGX Spark with Blackwell GPUs.

**Container Name:** `trtllm-qwen2.5-vl-7b-fp4`
**Default Port:** `8201`
**Model:** `nvidia/Qwen2.5-VL-7B-Instruct-FP4`
**Type:** Vision-Language Model (VLM)
**Quantization:** FP4 (4-bit floating point)

## Prerequisites

1. **DGX Spark** with Blackwell GPU or compatible NVIDIA GPU with CUDA 12.x
2. **HuggingFace Token** - Get one at https://huggingface.co/settings/tokens
3. **Model Access** - Accept the license at https://huggingface.co/nvidia/Qwen2.5-VL-7B-Instruct-FP4
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

The server will be available at `http://localhost:8201` with OpenAI-compatible vision API endpoints.

### Managing the Server

```bash
# Stop the server
docker stop trtllm-qwen2.5-vl-7b-fp4

# Start the server (fast - model already cached)
docker start trtllm-qwen2.5-vl-7b-fp4

# Restart the server
docker restart trtllm-qwen2.5-vl-7b-fp4

# View logs
docker logs -f trtllm-qwen2.5-vl-7b-fp4

# Remove container (to start fresh)
docker rm -f trtllm-qwen2.5-vl-7b-fp4
```

## FP4 vs FP8 Quantization

| Aspect | FP4 (This Model) | FP8 |
|--------|------------------|-----|
| Quality | Good | Higher |
| Memory Usage | ~5-6 GB | ~8-10 GB |
| Speed | Faster | Fast |
| Use Case | Memory-constrained, multi-model setups | Accuracy-sensitive tasks |

**Choose FP4 when:**
- Running multiple models simultaneously
- GPU memory is limited
- Speed is more important than perfect accuracy
- Doing simple vision tasks (OCR, basic descriptions)

**Choose FP8 when:**
- Running a single model
- Quality/accuracy is critical
- Doing complex reasoning about images

## Capabilities

This vision model can:
- **Understand images**: Describe scenes, objects, people, actions
- **OCR**: Extract text from images and documents
- **Visual Q&A**: Answer questions about images
- **PDF Processing**: Read text from PDF screenshots
- **Table Understanding**: Interpret Excel/CSV data from screenshots
- **Multi-turn conversations**: Discuss images across multiple messages

## Configuration

Edit the variables at the top of `serve.sh` to customize:

### Key Settings
- `PORT=8201` - Server port
- `MAX_BATCH_SIZE=64` - Maximum concurrent batch size
- `FREE_GPU_MEMORY_FRACTION=0.9` - GPU memory for KV cache

### TRT-LLM Specific Options
The script creates a YAML config with these optimizations:
```yaml
kv_cache_config:
  dtype: "auto"
  free_gpu_memory_fraction: 0.9
cuda_graph_config:
  enable_padding: true
disable_overlap_scheduler: true
```

## Testing the Server

### Basic Text Test

```bash
curl -s http://localhost:8201/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nvidia/Qwen2.5-VL-7B-Instruct-FP4",
    "messages": [{"role": "user", "content": "Hello! What can you do?"}],
    "max_tokens": 100
  }'
```

### Vision Test with Image URL

```bash
curl -s http://localhost:8201/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nvidia/Qwen2.5-VL-7B-Instruct-FP4",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "image_url",
            "image_url": {
              "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/300px-PNG_transparency_demonstration_1.png"
            }
          },
          {
            "type": "text",
            "text": "What do you see in this image?"
          }
        ]
      }
    ],
    "max_tokens": 300
  }'
```

## Usage with Python

### From URL

```python
import requests

response = requests.post(
    "http://localhost:8201/v1/chat/completions",
    json={
        "model": "nvidia/Qwen2.5-VL-7B-Instruct-FP4",
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": "https://example.com/image.jpg"}
                },
                {
                    "type": "text",
                    "text": "Describe this image"
                }
            ]
        }],
        "max_tokens": 300
    }
)

print(response.json()['choices'][0]['message']['content'])
```

### From Local File (Base64)

```python
import base64
import requests

# Encode image to base64
with open("image.jpg", "rb") as f:
    image_base64 = base64.b64encode(f.read()).decode('utf-8')

response = requests.post(
    "http://localhost:8201/v1/chat/completions",
    json={
        "model": "nvidia/Qwen2.5-VL-7B-Instruct-FP4",
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                },
                {
                    "type": "text",
                    "text": "Extract all text from this image"
                }
            ]
        }],
        "max_tokens": 500
    }
)

print(response.json()['choices'][0]['message']['content'])
```

## Multi-Model Setup

FP4's smaller memory footprint makes it ideal for multi-model deployments:

| Model | Port | Approx. Memory | Use Case |
|-------|------|----------------|----------|
| Qwen2.5-VL-7B-FP4 (TRT-LLM) | 8201 | ~5-6 GB | Vision |
| Qwen3-Coder-30B (vLLM) | 8100 | ~65 GB | Code |
| Total | | ~70 GB | Multi-purpose |

## Troubleshooting

### HuggingFace Token Issues
```
ERROR: HF_TOKEN environment variable is not set!
```
Solution: `export HF_TOKEN="your-token-here"`

### Model Access Denied
Make sure you've accepted the model license at:
https://huggingface.co/nvidia/Qwen2.5-VL-7B-Instruct-FP4

### Out of Memory
FP4 already uses minimal memory. If still OOM:
- Reduce `MAX_BATCH_SIZE` from 64 to 32 or 16
- Reduce `FREE_GPU_MEMORY_FRACTION` to 0.7

### Container Won't Start
Check if port 8201 is already in use:
```bash
lsof -i :8201
```

### Lower Quality Output
FP4 trades some quality for efficiency. If outputs seem degraded:
- Use the FP8 version instead for critical tasks
- Provide clearer, more detailed prompts
- Use higher resolution images

## Performance Notes

**Model Size:** ~5-6 GB (FP4 quantized)
**Startup Time:**
- First run (download): ~3-5 minutes
- Cached runs: ~1-2 minutes

**Throughput:** Highest among quantization options due to smaller model size

## Port Summary (TRT-LLM Vision Models)

| Model | Port | Quantization |
|-------|------|--------------|
| Qwen2.5-VL-7B-FP8 | 8200 | FP8 (higher quality) |
| Qwen2.5-VL-7B-FP4 | 8201 | FP4 (lower memory) |

## References

- [NVIDIA TRT-LLM DGX Spark Guide](https://build.nvidia.com/spark/trt-llm/instructions)
- [Qwen2.5-VL Model Card](https://huggingface.co/nvidia/Qwen2.5-VL-7B-Instruct-FP4)
- [TensorRT-LLM Documentation](https://nvidia.github.io/TensorRT-LLM/)
