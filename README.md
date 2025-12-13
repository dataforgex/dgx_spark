# DGX Spark - Multi-Model LLM Serving

Local LLM infrastructure for DGX Spark (GB10 Blackwell) with vLLM, web UI, and model management.

## Quick Start

### 1. Start the Web GUI & Model Manager

```bash
cd web-gui
./start-docker.sh
```

Access at:
- **Dashboard**: http://localhost:5173 - Model management, GPU monitoring
- **Chat**: http://localhost:5173/chat - Interactive chat with web search

### 2. Start a Model

Use the Dashboard UI to start/stop models, or manually:

```bash
cd vllm-qwen3-coder-30b-awq
./serve.sh
```

## Available Models

| Model | Engine | Port | Use Case |
|-------|--------|------|----------|
| Qwen3-Coder-30B | vLLM | 8100 | Code generation |
| Qwen2-VL-7B | vLLM | 8101 | Vision/images |
| Ministral-3-14B | vLLM | 8103 | General chat |
| Qwen3-Coder-30B-AWQ | vLLM | 8104 | Code + tool calling |
| Qwen3-VL-32B | Ollama | 11435 | Advanced vision |

**Recommended**: `qwen3-coder-30b-awq` - Best balance of speed (52 TPS) and features (tool calling for web search).

## Project Structure

```
dgx_spark/
├── web-gui/                    # React dashboard + chat (port 5173)
├── model-manager/              # Model start/stop API (port 5175)
├── models.json                 # Centralized model configuration
├── vllm-qwen3-coder-30b/       # Text/code model
├── vllm-qwen3-coder-30b-awq/   # AWQ quantized (fastest)
├── vllm-qwen2-vl-7b/           # Vision model
├── vllm-ministral3-14b/        # Mistral model
├── searxng/                    # Local search engine
├── benchmarks/                 # Performance benchmarks
└── docs/                       # Documentation
```

## Features

### Web GUI
- **Model Manager**: Start/stop models from the dashboard
- **GPU Monitoring**: Real-time VRAM, temperature, power usage
- **Chat Interface**: Multi-model chat with streaming responses
- **Web Search**: SearXNG integration for real-time information
- **Image Support**: Upload images for vision models

### Model Management
- Centralized config in `models.json`
- Docker-based model serving
- Automatic container lifecycle management
- Health checks and status monitoring

### Web Search (Tool Calling)
Models with tool calling support can search the web:
```
User: What's the weather in Tokyo today?
Assistant: [searches web] Based on current data...
```

Requires:
1. SearXNG running: `cd searxng && docker compose up -d`
2. Model with tool calling (e.g., qwen3-coder-30b-awq)
3. Search toggle enabled in chat

## API Usage

### Chat Completion

```bash
curl http://localhost:8104/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "cpatonn/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 500
  }'
```

### Vision (Image Input)

```bash
curl http://localhost:8101/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2-VL-7B-Instruct",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}},
        {"type": "text", "text": "Describe this image"}
      ]
    }],
    "max_tokens": 300
  }'
```

## Managing Models

### Via Dashboard (Recommended)
1. Open http://localhost:5173
2. Click Start/Stop buttons for each model

### Via Command Line
```bash
# Start
cd vllm-qwen3-coder-30b-awq && ./serve.sh

# Stop
docker stop vllm-qwen3-coder-30b-awq

# Logs
docker logs -f vllm-qwen3-coder-30b-awq

# GPU usage
nvidia-smi
```

## Adding New Models

1. Create folder: `vllm-{model-name}/`
2. Add to `models.json`:
```json
"model-key": {
  "name": "Display Name",
  "engine": "vllm",
  "port": 8105,
  "container_name": "vllm-model-name",
  "image": "nvcr.io/nvidia/vllm:25.09-py3",
  "model_id": "org/model-name",
  "settings": {
    "max_num_seqs": 8,
    "max_model_len": 32768,
    "gpu_memory_utilization": 0.3
  }
}
```
3. Create `serve.sh` (copy from existing model)
4. Restart model-manager: `docker restart model-manager`

## Performance

Benchmarked on DGX Spark (GB10 Blackwell, 128GB unified memory):

| Model | TPS | TTFT | Memory |
|-------|-----|------|--------|
| Qwen3-Coder-30B-AWQ (vLLM) | **52** | 0.069s | ~34 GB |
| Qwen3-30B-FP4 (TRT-LLM)* | 32 | 0.054s | ~33 GB |

*TRT-LLM removed due to bugs and missing features. See [docs/TRTLLM_ISSUES.md](docs/TRTLLM_ISSUES.md).

## Troubleshooting

### Model Won't Start
```bash
# Check if port is in use
ss -tlnp | grep 8104

# Check container logs
docker logs vllm-qwen3-coder-30b-awq

# Remove stuck container
docker rm -f vllm-qwen3-coder-30b-awq
```

### Out of Memory
```bash
# Check GPU usage
nvidia-smi

# Reduce memory in serve.sh
GPU_MEMORY_UTILIZATION=0.25  # Lower value
```

### Web Search Not Working
1. Ensure SearXNG is running: `docker ps | grep searxng`
2. Check search toggle is enabled in chat
3. Use a model with tool calling support

## Requirements

- **Hardware**: DGX Spark or NVIDIA GPU with 64+ GB VRAM
- **Docker**: With NVIDIA container runtime
- **Node.js**: v18+ (for web GUI development)

## Services

| Service | Port | Description |
|---------|------|-------------|
| Web GUI | 5173 | Dashboard and chat |
| Metrics API | 5174 | GPU/system metrics |
| Model Manager | 5175 | Model lifecycle API |
| SearXNG | 8888 | Local search engine |
| Models | 8100-8104 | vLLM inference servers |
