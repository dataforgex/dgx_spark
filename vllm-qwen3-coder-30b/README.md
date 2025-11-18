# vLLM Qwen3-Coder-30B Server

This directory contains scripts and configuration for running the **Qwen3-Coder-30B-A3B-Instruct** model with vLLM.

**Container Name:** `vllm-qwen3-coder-30b`
**Default Port:** `8100`
**Model:** `Qwen/Qwen3-Coder-30B-A3B-Instruct`

## Multi-Model Setup

This model runs alongside Qwen2-VL-7B vision model:

| Model | Port | GPU Memory | Use Case |
|-------|------|------------|----------|
| **Qwen3-Coder-30B** | **8100** | **55% (~65 GB)** | **Text/code generation** |
| Qwen2-VL-7B | 8101 | 25% (~26 GB) | Vision understanding |
| **Total** | | **80%** | **20% safety margin** |

## Setting Up Additional Models

To set up another model, copy this entire directory and update:
1. **Folder name**: `vllm-{model-name}`
2. **In serve.sh**:
   - `CONTAINER_NAME` - unique name (e.g., `vllm-deepseek-v3`)
   - `MODEL_NAME` - HuggingFace model path
   - `PORT` - unique port (e.g., 8102, 8103, etc.)
   - `GPU_MEMORY_UTILIZATION` - adjust to fit (ensure total < 0.85)
3. **In test-server.sh**: Update default `PORT` to match

All models will share the same HuggingFace cache (`~/.cache/huggingface`), so models are downloaded only once.

## Quick Start

```bash
./serve.sh
```

The server will be available at `http://localhost:8100` with OpenAI-compatible API endpoints.

### Managing the Server

```bash
# Stop the server
docker stop vllm-qwen3-coder-30b

# Start the server (fast - model already cached)
docker start vllm-qwen3-coder-30b

# Restart the server
docker restart vllm-qwen3-coder-30b

# View logs
docker logs -f vllm-qwen3-coder-30b

# Remove container (to start fresh)
docker rm -f vllm-qwen3-coder-30b
```

## Configuration

Edit the variables at the top of `serve.sh` to customize your setup:

### Context Window & Concurrency
- `MAX_MODEL_LEN=32768` - Maximum context length (supports k/K/m/M/g/G suffixes)
- `MAX_NUM_SEQS=256` - Maximum number of concurrent sequences

### GPU Memory
- `GPU_MEMORY_UTILIZATION=0.55` - Fraction of GPU memory to use (0.0-1.0)
  - Current: 55% for multi-model setup (with Qwen2-VL at 25%)
  - Single model: Can increase to 0.85-0.95

### Performance Options
- `ENABLE_PREFIX_CACHING=true` - Cache common prefixes for faster responses
- `ENABLE_CHUNKED_PREFILL=true` - Reduce latency for long prompts

### Multi-GPU Support
Uncomment and configure these variables for multi-GPU setups:
```bash
TENSOR_PARALLEL_SIZE=2    # Split model across N GPUs
PIPELINE_PARALLEL_SIZE=1  # Pipeline stages across N GPUs
```

## Testing the Server

Once running, test with curl:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-Coder-30B-A3B-Instruct",
    "messages": [
      {"role": "user", "content": "Write a Python function to calculate fibonacci numbers"}
    ],
    "max_tokens": 500,
    "temperature": 0.7
  }'
```

## Common Configuration Scenarios

### Maximum Context Window (128K tokens)
Requires more GPU memory:
```bash
MAX_MODEL_LEN=131072
GPU_MEMORY_UTILIZATION=0.98
```

### High Concurrency Setup
For handling many simultaneous requests:
```bash
MAX_NUM_SEQS=512
ENABLE_PREFIX_CACHING=true
```

### Low Latency Setup
For faster response times:
```bash
ENABLE_CHUNKED_PREFILL=true
MAX_NUM_SEQS=128
```

### Multi-GPU (2 GPUs)
Split the model across 2 GPUs:
```bash
TENSOR_PARALLEL_SIZE=2
```

## Additional vLLM Options

To see all available options:
```bash
docker run --gpus all nvcr.io/nvidia/vllm:25.09-py3 vllm serve --help
```

### Useful Additional Flags

Add these to the `DOCKER_CMD` in `serve.sh` if needed:

**Memory & Performance:**
- `--swap-space 4` - CPU swap space in GiB (default: 4)
- `--kv-cache-dtype fp8` - Use FP8 for KV cache (saves memory)
- `--block-size 16` - Token block size (8, 16, or 32)

**Scheduling:**
- `--scheduler-delay-factor 0.0` - Scheduler delay (0.0-1.0)
- `--max-num-batched-tokens` - Max tokens per batch

**Data Types:**
- `--dtype bfloat16` - Force BF16 precision
- `--quantization awq` - Use AWQ quantization

**API Server:**
- `--api-key YOUR_KEY` - Require API key authentication
- `--host 0.0.0.0` - Listen on all interfaces

## Environment Variables

Set these before running if needed:
```bash
export VLLM_USE_DEEP_GEMM=1  # Enable DeepGEMM optimization
export HF_TOKEN=your_token    # Hugging Face token for gated models
```

## OpenAI Python Client Example

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="Qwen/Qwen3-Coder-30B-A3B-Instruct",
    messages=[
        {"role": "user", "content": "Explain quicksort algorithm"}
    ],
    max_tokens=1000
)

print(response.choices[0].message.content)
```

## Troubleshooting

### Out of Memory Errors
- Reduce `MAX_MODEL_LEN`
- Reduce `GPU_MEMORY_UTILIZATION`
- Reduce `MAX_NUM_SEQS`
- Enable `--kv-cache-dtype fp8`

### Slow Performance
- Enable `--enable-prefix-caching`
- Enable `--enable-chunked-prefill`
- Increase `GPU_MEMORY_UTILIZATION`
- Add more GPUs with `--tensor-parallel-size`

### Connection Issues
- Check firewall settings
- Use `--host 0.0.0.0` to listen on all interfaces
- Verify port is not in use: `lsof -i :8000`

## References

- [vLLM Documentation](https://docs.vllm.ai/)
- [Qwen3-Coder Recipe](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3-Coder-480B-A35B.html)
- [NVIDIA vLLM Container](https://build.nvidia.com/spark/vllm/instructions)
- [OpenAI API Compatibility](https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html)
