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
| Nemotron-3-Nano-30B | vLLM | 8105 | Reasoning model |
| Qwen3-VL-32B | Ollama | 11435 | Advanced vision |
| **Qwen3-235B-AWQ** | vLLM | 8235 | **Distributed** (2-node) |

**Single Node**: `qwen3-coder-30b-awq` - Best balance of speed (52 TPS) and features.

**Multi-Node**: `qwen3-235b-awq` - 235B parameter model distributed across 2 DGX Sparks via Ray cluster with tensor parallelism.

## Project Structure

```
dgx_spark/
├── web-gui/                    # React dashboard + chat (port 5173)
├── model-manager/              # Model start/stop API (port 5175)
├── tool-call-sandbox/          # Code execution sandbox (port 5176)
├── shared/                     # Shared utilities (auth, rate limiting)
├── models.yaml                 # Centralized model configuration
├── vllm-qwen3-coder-30b/       # Text/code model
├── vllm-qwen3-coder-30b-awq/   # AWQ quantized (fastest)
├── vllm-qwen3-235b-awq/        # 235B distributed model (2-node)
├── vllm-qwen2-vl-7b/           # Vision model
├── vllm-ministral3-14b/        # Mistral model
├── vllm-nemotron-3-nano-30b-bf16/  # Nemotron reasoning model
├── ollama-qwen3-vl-32b/        # Ollama vision model
├── searxng-docker/             # Local search engine
└── docs/                       # Documentation
```

## Features

### Web GUI
- **Model Manager**: Start/stop models from the dashboard
- **GPU Monitoring**: Real-time VRAM, temperature, power usage
- **Chat Interface**: Multi-model chat with streaming responses
- **Web Search**: SearXNG integration for real-time information
- **Image Support**: Upload images for vision models
- **Token Counter**: Live token usage tracking with context warnings
- **Startup Progress**: Visual progress bars for model loading

### Model Management
- Centralized config in `models.yaml`
- Docker-based model serving with CORS support
- Automatic container lifecycle management
- Health checks with startup progress tracking
- **GPU Memory Checking**: Pre-start memory validation prevents OOM
- Estimated memory display per model

### API Security (Optional)
Enable API authentication and rate limiting by setting environment variables:

```bash
export DGX_API_KEY="your-secret-key"  # Enable Bearer token auth
export DGX_RATE_LIMIT=60               # Requests per minute (default: 60)
```

All services support:
- Bearer token authentication
- Rate limiting per client IP
- Request logging with X-Request-ID correlation

### Tool Calling (Web Search + Code Sandbox)

Models with tool calling support can:
- **Search the web** for real-time information
- **Execute code** in a sandboxed Python/Bash environment

```
User: What's the weather in Tokyo today?
Assistant: [searches web] Based on current data...

User: Calculate the first 50 prime numbers
Assistant: [executes Python code] Here are the primes: [2, 3, 5, ...]
```

**Available Tools:**
| Tool | Description |
|------|-------------|
| `web_search` | Search the web via SearXNG |
| `code_execution` | Execute Python/JS/Bash code |
| `bash_command` | Run shell commands |
| `data_storage` | Persist data across calls |
| `file_analysis` | Analyze uploaded files |

**Sandbox Security:**
- Seccomp profile restricts dangerous syscalls
- Dangerous Python imports blocked (subprocess, pickle, etc.)
- Non-root execution with dropped capabilities
- Resource limits (CPU, memory, process count)
- Network disabled by default
- Read-only filesystem option

**Setup:**
1. Start SearXNG: `cd searxng-docker && docker compose up -d`
2. Start Sandbox: `cd tool-call-sandbox && ./serve.sh`
3. Use a model with tool calling (e.g., qwen3-235b-awq)
4. Enable Search and/or Sandbox toggles in chat

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
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}},
        {"type": "text", "text": "Describe this image"}
      ]
    }],
    "max_tokens": 300
  }'
```

### With API Authentication

```bash
curl http://localhost:5175/api/models \
  -H "Authorization: Bearer your-api-key"
```

## Managing Models

### Via Dashboard (Recommended)
1. Open http://localhost:5173
2. Click Start/Stop buttons for each model
3. Watch startup progress for large models

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
2. Add to `models.yaml`:
```yaml
model-key:
  name: "Display Name"
  description: "Model description"
  engine: vllm
  port: 8106
  container_name: "vllm-model-name"
  model_id: "org/model-name"
  estimated_memory_gb: 30
  settings:
    max_model_len: 32768
    max_num_seqs: 8
    gpu_memory_utilization: 0.3
    enable_auto_tool_choice: true
    tool_call_parser: "qwen3_coder"  # or "mistral", "hermes"
```
3. Create `serve.sh` (copy from existing model, add `--allowed-origins '["*"]'` for CORS)
4. Restart model-manager: `docker restart model-manager`

## Performance

Benchmarked on DGX Spark (GB10 Blackwell, 128GB unified memory):

| Model | TPS | TTFT | Memory |
|-------|-----|------|--------|
| Qwen3-Coder-30B-AWQ (vLLM) | **52** | 0.069s | ~34 GB |
| Qwen3-30B-FP4 (TRT-LLM)* | 32 | 0.054s | ~33 GB |

*TRT-LLM removed due to GB10 compatibility issues. See [docs/TRTLLM_ISSUES.md](docs/TRTLLM_ISSUES.md).

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
| Tool Sandbox | 5176 | Code execution sandbox |
| SearXNG | 8080 | Local search engine |
| Models | 8100-8235 | vLLM inference servers |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DGX_API_KEY` | (none) | Enable API authentication |
| `DGX_RATE_LIMIT` | 60 | Requests per minute per IP |
| `MODELS_BASE_DIR` | (auto) | Base directory for model configs |
| `VITE_*` | varies | Web GUI build-time configuration |

## Architecture

Key components:
- **Web GUI**: React + Vite frontend with real-time GPU monitoring
- **Model Manager**: FastAPI backend managing Docker containers
- **Tool Sandbox**: Isolated code execution with seccomp + capabilities
- **vLLM**: High-performance inference with OpenAI-compatible API
