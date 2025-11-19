# Qwen3-VL-30B Server (CPU Mode)

OpenAI-compatible API server for Qwen3-VL-30B-A3B-Instruct using Transformers.

## Status: Working on CPU

✅ **Server**: http://localhost:8102
✅ **API**: OpenAI-compatible v1 endpoints
⚠️ **Performance**: CPU-only (1-3 minutes per response)
❌ **GPU**: Not working due to GB10/sm_121 incompatibility

## Quick Start

### Start Server
```bash
./start_cpu.sh
```

### Test Server
```bash
# Health check
curl http://localhost:8102/health

# List models
curl http://localhost:8102/v1/models

# Chat completion
curl http://localhost:8102/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-VL-30B-A3B-Instruct",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50
  }'
```

### Stop Server
```bash
lsof -ti:8102 | xargs kill
```

### View Logs
```bash
tail -f server_cpu.log
```

## API Usage

### Chat Completions (Text)
```bash
curl http://localhost:8102/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-VL-30B-A3B-Instruct",
    "messages": [
      {"role": "user", "content": "Explain quantum computing in simple terms"}
    ],
    "max_tokens": 200,
    "temperature": 0.7
  }'
```

### Chat Completions (Vision + Text)
```bash
# With image URL
curl http://localhost:8102/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-VL-30B-A3B-Instruct",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}},
        {"type": "text", "text": "Describe this image"}
      ]
    }],
    "max_tokens": 300
  }'

# With base64 image
IMAGE_B64=$(base64 -w 0 image.jpg)
curl http://localhost:8102/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-VL-30B-A3B-Instruct",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,'$IMAGE_B64'"}},
        {"type": "text", "text": "What text is in this image?"}
      ]
    }],
    "max_tokens": 500
  }'
```

## Files

- **start_cpu.sh** - Start server in background (recommended)
- **serve_transformers.py** - FastAPI server implementation
- **setup_transformers.sh** - Setup virtual environment
- **server_cpu.log** - Server output and errors
- **venv/** - Python virtual environment
- **TROUBLESHOOTING.md** - Complete history of all deployment attempts

## Why CPU-Only?

This model runs on CPU due to hardware/software incompatibilities:

1. **vLLM doesn't support Qwen3-VL-MoE** architecture on this system
2. **GB10 GPU (sm_121)** too new for current ML frameworks on ARM64
3. **PyTorch CUDA for ARM64** requires NVIDIA containers, which reject GB10

See `TROUBLESHOOTING.md` for detailed attempts and failures.

## Performance Expectations

**CPU Mode:**
- ⏱️ **Response time**: 60-180 seconds per request
- 📊 **Throughput**: ~0.5-1 requests/minute
- 💻 **Use case**: Development, testing, experimentation
- ❌ **Not suitable**: Production, real-time applications

**GPU Mode (when available):**
- Would be ~60-100x faster
- Requires PyTorch with sm_121 support on ARM64

## Setup (If Rebuilding)

```bash
# Create virtual environment
./setup_transformers.sh

# Start server
./start_cpu.sh
```

## Requirements

- Python 3.x
- ~60 GB disk space (model weights)
- ~80 GB RAM (for CPU inference)
- Virtual environment with:
  - transformers >= 4.57.0
  - torch (CPU version)
  - accelerate
  - qwen-vl-utils
  - fastapi
  - uvicorn

## Troubleshooting

**Server won't start:**
```bash
# Check if port is in use
lsof -i :8102

# View error logs
tail -50 server_cpu.log

# Check virtual environment
source venv/bin/activate
python3 -c "import torch; print(torch.__version__)"
```

**Out of memory:**
- Ensure you have 80+ GB available RAM
- Close other applications
- Consider using a smaller model (Qwen2-VL-7B)

**Slow responses:**
- This is expected on CPU (1-3 minutes per response)
- Reduce `max_tokens` for faster responses
- GPU acceleration not currently available (see TROUBLESHOOTING.md)

## Integration

Works with any OpenAI-compatible client:

**Python:**
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8102/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="Qwen/Qwen3-VL-30B-A3B-Instruct",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=50
)
print(response.choices[0].message.content)
```

**JavaScript:**
```javascript
const response = await fetch('http://localhost:8102/v1/chat/completions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    model: 'Qwen/Qwen3-VL-30B-A3B-Instruct',
    messages: [{ role: 'user', content: 'Hello!' }],
    max_tokens: 50
  })
});
const data = await response.json();
console.log(data.choices[0].message.content);
```

## Future Improvements

- GPU support when PyTorch adds sm_121 support for ARM64
- Batching for better throughput
- Streaming responses
- Model caching optimizations

---

For detailed deployment history and all attempted solutions, see `TROUBLESHOOTING.md`.
