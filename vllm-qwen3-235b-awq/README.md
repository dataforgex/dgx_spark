# vLLM Qwen3-235B-A22B-AWQ - Distributed Inference

Run Qwen3-235B-A22B-AWQ (116GB) across two DGX Sparks using vLLM with tensor parallelism.

## Why AWQ Instead of NVFP4?

The `nvidia/Qwen3-235B-A22B-FP4` model uses NVFP4 quantization which has compatibility issues on GB10 (sm_121a):

| Issue | Details |
|-------|---------|
| CUTLASS kernels | Not fully compiled for sm_121a |
| FlashInfer fallback | Fails with "FP4 gemm Runner" error |
| Performance | ~20 tok/s vs ~40 tok/s for AWQ |

AWQ quantization works reliably on GB10 with better performance.

## Architecture

```
+---------------------+     200GbE QSFP      +---------------------+
|      spark-1        |<------------------->|      spark-2        |
|   192.168.100.10    |                      |   192.168.100.11    |
|   NVIDIA GB10 GPU   |                      |   NVIDIA GB10 GPU   |
|   Ray Head + vLLM   |                      |   Ray Worker        |
+---------------------+                      +---------------------+
```

| Component | Value |
|-----------|-------|
| Model | `QuantTrio/Qwen3-235B-A22B-Instruct-2507-AWQ` |
| Model Size | 116GB |
| Quantization | AWQ 4-bit |
| Architecture | MoE (128 experts, 8 active) |
| API Port | `8235` |
| Context Length | 8192 (configurable up to 262144) |

## Quick Start

```bash
# 1. Download the model (~116GB)
./download-model.sh

# 2. Start Ray cluster on both nodes
./start-cluster.sh

# 3. Start the inference server
./serve.sh

# 4. Test the API
./test-server.sh
```

## Configuration

Edit `serve.sh` to adjust:

```bash
MAX_MODEL_LEN=8192           # Context window (reduce if OOM)
GPU_MEMORY_UTILIZATION=0.75  # Memory usage (0.0-1.0)
SWAP_SPACE=16                # KV cache swap in GB
PORT=8235                    # API port
```

## Tool Calling (Function Calling)

This model supports OpenAI-compatible tool calling with the `qwen3_xml` parser:

```bash
# Enabled in serve.sh:
--enable-auto-tool-choice
--tool-call-parser qwen3_xml
```

Example API call with tools:

```bash
curl http://localhost:8235/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-235b-awq",
    "messages": [{"role": "user", "content": "What is 127 factorial?"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "calculate",
        "description": "Perform calculations",
        "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}}
      }
    }],
    "tool_choice": "auto",
    "max_tokens": 500
  }'
```

**Note**: The model outputs tool calls in `<tool_call>` XML format. The web-gui has been updated to parse these tags from the response content.

### Context Length vs Memory

| Context | Recommended For |
|---------|-----------------|
| 8192 | Safe default, plenty of headroom |
| 16384 | Most use cases |
| 32768 | Long documents (may need lower GPU util) |
| 65536+ | Experimental, risk of OOM |

## API Usage

### Chat Completions

```bash
curl http://localhost:8235/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-235b-awq",
    "messages": [{"role": "user", "content": "Explain quantum computing"}],
    "max_tokens": 256
  }'
```

### Python Client

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8235/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="qwen3-235b-awq",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=100
)
print(response.choices[0].message.content)
```

## GB10-Specific Flags

The `serve.sh` includes flags required for GB10:

| Flag | Reason |
|------|--------|
| `--enforce-eager` | CUDA graphs crash on sm_121a |
| `--trust-remote-code` | Required for Qwen models |
| `--swap-space 16` | KV cache offloading for large contexts |
| `--enable-auto-tool-choice` | Enable function/tool calling |
| `--tool-call-parser qwen3_xml` | Parse Qwen3's XML tool format |

## Troubleshooting

### Model loading takes forever
- Model is 116GB - expect 5-10 minutes for loading
- Check logs: `docker exec $(docker ps --format '{{.Names}}' | grep node | head -1) cat /tmp/vllm_serve.log | tail -50`

### Out of Memory
- Reduce `MAX_MODEL_LEN` in serve.sh
- Reduce `GPU_MEMORY_UTILIZATION`
- Increase `SWAP_SPACE`

### Worker not joining
```bash
# Check worker container
ssh 192.168.100.11 "docker logs \$(docker ps --format '{{.Names}}' | grep node | head -1)"

# Verify NFS mount
ssh 192.168.100.11 "ls ~/.cache/huggingface/hub/ | grep -i qwen"
```

### Slow inference
- AWQ on GB10 typically achieves ~35-40 tok/s
- First request may be slower due to warmup
- Reduce `max_tokens` in requests for faster responses

## Scripts

| Script | Description |
|--------|-------------|
| `download-model.sh` | Download the AWQ model |
| `start-cluster.sh` | Start Ray cluster on both nodes |
| `serve.sh` | Start vLLM inference server |
| `test-server.sh` | Test the API |
| `stop-cluster.sh` | Stop all containers |

## References

- [HuggingFace Model](https://huggingface.co/QuantTrio/Qwen3-235B-A22B-Instruct-2507-AWQ)
- [NVIDIA Forum: NVFP4 on DGX Spark](https://forums.developer.nvidia.com/t/help-running-nvfp4-model-on-2x-dgx-spark-with-vllm-ray-multi-node/353723)
- [vLLM Distributed Serving](https://docs.vllm.ai/en/latest/serving/distributed_serving.html)
