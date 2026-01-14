# vLLM Ministral-3-14B Server (Vision + Tool Use Model)

This directory contains scripts and configuration for running the **Ministral-3-14B-Instruct-2512** vision-language model with vLLM.

**Container Name:** `vllm-mistral3-14b`
**Default Port:** `8102`
**Model:** `mistralai/Ministral-3-14B-Instruct-2512`
**Type:** Vision-Language Model with Function Calling

## Quick Start

### Start the Server

```bash
./serve.sh
```

The server will be available at `http://localhost:8102` with OpenAI-compatible API endpoints.

### Managing the Server

```bash
# Stop the server
docker stop vllm-mistral3-14b

# Start the server (fast - model already cached)
docker start vllm-mistral3-14b

# Restart the server
docker restart vllm-mistral3-14b

# View logs
docker logs -f vllm-mistral3-14b

# Remove container (to start fresh)
docker rm -f vllm-mistral3-14b
```

## Model Features

- **Vision Understanding**: Analyze images, documents, screenshots
- **Function Calling**: Native tool use support with Mistral parser
- **JSON Output**: Structured output generation
- **256K Context**: Supports up to 256K tokens (default 32K for efficiency)
- **FP8 Weights**: Efficient inference, fits in ~24GB VRAM

## Configuration

Edit the variables at the top of `serve.sh` to customize:

### Memory & Concurrency
- `MAX_MODEL_LEN=32768` - Maximum context length
- `MAX_NUM_SEQS=64` - Maximum concurrent sequences
- `GPU_MEMORY_UTILIZATION=0.30` - 30% GPU memory

### Performance Options
- `ENABLE_PREFIX_CACHING=true` - Cache common prefixes
- `ENABLE_CHUNKED_PREFILL=true` - Reduce latency for long prompts

## Testing

Run the test suite:

```bash
python3 test-vision.py
```

Tests include:
1. Basic text generation
2. Vision/image understanding
3. Function calling / tool use
4. JSON structured output
5. Multi-turn conversations

## API Examples

### Basic Chat

```bash
curl http://localhost:8102/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistralai/Ministral-3-14B-Instruct-2512",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100,
    "temperature": 0.1
  }'
```

### Vision (Image Analysis)

```bash
curl http://localhost:8102/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistralai/Ministral-3-14B-Instruct-2512",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}},
        {"type": "text", "text": "Describe this image"}
      ]
    }],
    "max_tokens": 300
  }'
```

### Function Calling

```python
import requests

tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"}
            },
            "required": ["location"]
        }
    }
}]

response = requests.post(
    "http://localhost:8102/v1/chat/completions",
    json={
        "model": "mistralai/Ministral-3-14B-Instruct-2512",
        "messages": [{"role": "user", "content": "What's the weather in Tokyo?"}],
        "tools": tools,
        "tool_choice": "auto"
    }
)

print(response.json())
```

### JSON Output

```python
response = requests.post(
    "http://localhost:8102/v1/chat/completions",
    json={
        "model": "mistralai/Ministral-3-14B-Instruct-2512",
        "messages": [{"role": "user", "content": "List 3 fruits as JSON"}],
        "response_format": {"type": "json_object"}
    }
)
```

## Multi-Model Setup

This model can run alongside other vLLM servers:

| Model | Port | GPU Memory | Use Case |
|-------|------|------------|----------|
| Qwen3-Coder-30B | 8100 | 55% | Text/code generation |
| Qwen2-VL-7B | 8101 | 25% | Vision understanding |
| Ministral-3-14B | 8102 | 30% | Vision + tool use |

Adjust `GPU_MEMORY_UTILIZATION` based on your setup.

## Troubleshooting

### Out of Memory
- Reduce `GPU_MEMORY_UTILIZATION` to 0.25 or lower
- Reduce `MAX_MODEL_LEN` to 16384
- Stop other GPU processes

### Model Loading Fails
- Ensure vLLM >= 0.12.0 (nvcr.io/nvidia/vllm:25.09-py3 includes this)
- Check HuggingFace cache permissions
- Verify network access to huggingface.co

### Tool Calling Not Working
- The `--enable-auto-tool-choice --tool-call-parser mistral` flags are required
- These are included in serve.sh by default

## Performance Notes

**Model Size:** ~14GB (13.5B language + 0.4B vision encoder)
**Weights Format:** FP8 (efficient)
**Startup Time:**
- First run (download): ~5-10 minutes
- Cached runs: ~2-3 minutes

## References

- [Ministral-3-14B Model Card](https://huggingface.co/mistralai/Ministral-3-14B-Instruct-2512)
- [vLLM Mistral Documentation](https://docs.vllm.ai/projects/recipes/en/latest/Mistral/Ministral-3-Instruct.html)
- [Mistral AI Blog](https://mistral.ai/news/mistral-3)
