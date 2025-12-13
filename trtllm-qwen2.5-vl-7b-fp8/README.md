# TensorRT-LLM Qwen2.5-VL-7B-FP8 Server (Vision Model)

This directory contains scripts for running **Qwen2.5-VL-7B-Instruct-FP8** using NVIDIA TensorRT-LLM, optimized for DGX Spark with Blackwell GPUs.

**Container Name:** `trtllm-qwen2.5-vl-7b-fp8`
**Default Port:** `8200`
**Model:** `nvidia/Qwen2.5-VL-7B-Instruct-FP8`
**Type:** Vision-Language Model (VLM)
**Quantization:** FP8 (8-bit floating point)

## Prerequisites

1. **DGX Spark** with Blackwell GPU or compatible NVIDIA GPU with CUDA 12.x
2. **HuggingFace Token** - Get one at https://huggingface.co/settings/tokens
3. **Model Access** - Accept the license at https://huggingface.co/nvidia/Qwen2.5-VL-7B-Instruct-FP8
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

The server will be available at `http://localhost:8200` with OpenAI-compatible vision API endpoints.

### Managing the Server

```bash
# Stop the server
docker stop trtllm-qwen2.5-vl-7b-fp8

# Start the server (fast - model already cached)
docker start trtllm-qwen2.5-vl-7b-fp8

# Restart the server
docker restart trtllm-qwen2.5-vl-7b-fp8

# View logs
docker logs -f trtllm-qwen2.5-vl-7b-fp8

# Remove container (to start fresh)
docker rm -f trtllm-qwen2.5-vl-7b-fp8
```

## FP8 vs FP4 Quantization

| Aspect | FP8 (This Model) | FP4 |
|--------|------------------|-----|
| Quality | Higher | Lower |
| Memory Usage | ~8-10 GB | ~5-6 GB |
| Speed | Fast | Faster |
| Use Case | Better for accuracy-sensitive tasks | Better for memory-constrained setups |

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
- `PORT=8200` - Server port (NVIDIA recommended for VLM)
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
curl -s http://localhost:8200/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nvidia/Qwen2.5-VL-7B-Instruct-FP8",
    "messages": [{"role": "user", "content": "Hello! What can you do?"}],
    "max_tokens": 100
  }'
```

### Vision Test with Image URL

```bash
curl -s http://localhost:8200/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nvidia/Qwen2.5-VL-7B-Instruct-FP8",
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
    "http://localhost:8200/v1/chat/completions",
    json={
        "model": "nvidia/Qwen2.5-VL-7B-Instruct-FP8",
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
    "http://localhost:8200/v1/chat/completions",
    json={
        "model": "nvidia/Qwen2.5-VL-7B-Instruct-FP8",
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

## Troubleshooting

### HuggingFace Token Issues
```
ERROR: HF_TOKEN environment variable is not set!
```
Solution: `export HF_TOKEN="your-token-here"`

### Model Access Denied
Make sure you've accepted the model license at:
https://huggingface.co/nvidia/Qwen2.5-VL-7B-Instruct-FP8

### Out of Memory
- Reduce `FREE_GPU_MEMORY_FRACTION` from 0.9 to 0.7
- Reduce `MAX_BATCH_SIZE` from 64 to 32
- Consider using FP4 version instead

### Container Won't Start
Check if port 8200 is already in use:
```bash
lsof -i :8200
```

### Slow Performance
- Ensure CUDA drivers are compatible with CUDA 12.x
- Check GPU utilization: `nvidia-smi`
- Clear page cache: `sudo sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'`

## Performance Notes

**Model Size:** ~8-10 GB (FP8 quantized)
**Startup Time:**
- First run (download): ~5-10 minutes
- Cached runs: ~2-3 minutes

**Throughput:** Higher than vLLM due to TensorRT optimizations

## Comparison with vLLM Version

| Feature | TRT-LLM (This) | vLLM |
|---------|----------------|------|
| Engine | TensorRT-LLM | vLLM |
| Quantization | FP8 (NVIDIA optimized) | Full precision |
| Memory | ~8-10 GB | ~15 GB |
| Target | DGX Spark / Blackwell | General NVIDIA GPUs |
| Performance | Optimized for NVIDIA | General purpose |

## References

- [NVIDIA TRT-LLM DGX Spark Guide](https://build.nvidia.com/spark/trt-llm/instructions)
- [Qwen2.5-VL Model Card](https://huggingface.co/nvidia/Qwen2.5-VL-7B-Instruct-FP8)
- [TensorRT-LLM Documentation](https://nvidia.github.io/TensorRT-LLM/)
