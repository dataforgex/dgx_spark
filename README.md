# DGX Spark - Multi-Model LLM Serving

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Website](https://img.shields.io/badge/Website-acloudpartner.dk-green)](https://www.acloudpartner.dk)

Local LLM infrastructure for DGX Spark (GB10 Blackwell) with vLLM, web UI, and model management. Works with 1 or 2 DGX Sparks.

## Quick Start

```bash
cd web-gui && ./start-docker.sh
```

**Dashboard**: http://localhost:5173 | **Chat**: http://localhost:5173/chat

## Features

- **Web Dashboard** - Start/stop models, GPU monitoring, chat interface
- **7 Models** - Code, vision, reasoning, 235B distributed
- **Tool Calling** - Web search + sandboxed code execution
- **OpenAI API** - Compatible endpoints on ports 8100-8235

## Models

| Model | Port | Best For |
|-------|------|----------|
| Qwen3-Coder-30B-AWQ | 8104 | Code + tools (recommended) |
| Qwen3-235B-AWQ | 8235 | Large tasks (2-node) |
| Qwen2-VL-7B | 8101 | Vision |
| Nemotron-3-Nano-30B | 8105 | Reasoning |

---

## Technical Reference

> For Claude Code and developers

### Services

| Service | Port | Start Command |
|---------|------|---------------|
| Web GUI | 5173 | `cd web-gui && ./start-docker.sh` |
| Model Manager | 5175 | `cd model-manager && ./serve.sh` |
| Tool Sandbox | 5176 | `cd tool-call-sandbox && ./serve.sh` |
| SearXNG | 8080 | `cd searxng-docker && docker compose up -d` |

### Key Files

- `models.yaml` - All model configurations
- `shared/auth.py` - API authentication (Bearer token via `DGX_API_KEY`)
- `vllm-*/serve.sh` - Model startup scripts

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `DGX_API_KEY` | Enable API authentication |
| `DGX_RATE_LIMIT` | Requests/min per IP (default: 60) |
| `DGX_LOG_LEVEL` | Log level: debug, info, warning, error (default: info) |
| `HF_TOKEN` | HuggingFace access token |

### Runtime Configuration

```bash
# Check current log level
curl http://localhost:5175/api/config/log-level

# Enable debug logging (no restart needed)
curl -X POST http://localhost:5175/api/config/log-level \
  -H "Content-Type: application/json" -d '{"level": "debug"}'
```

### Architecture

- **Frontend**: React + Vite (`web-gui/`)
- **APIs**: FastAPI with shared auth middleware
- **Models**: vLLM in Docker with CORS enabled
- **Sandbox**: Seccomp + capabilities + non-root execution
