# DGX Spark - Local LLM Serving with vLLM

Complete infrastructure for serving local LLMs using vLLM with OpenAI-compatible API and multiple client interfaces.

## Quick Start

### 1. Start the vLLM Server

```bash
cd vllm-qwen3-coder-30b
./serve-v2.sh
```

**Server Info:**
- Port: `8100`
- Model: Qwen3-Coder-30B-A3B-Instruct
- Startup time: ~8 minutes (cached), ~15 minutes (first run)
- API: http://localhost:8100/v1

### 2. Choose a Client

#### 🌐 Web GUI (Recommended)
```bash
cd web-gui
npm run dev
```
Open http://localhost:5173

#### 🐍 Python CLI
```bash
cd python
./start_chat.sh
```

#### 📘 TypeScript CLI
```bash
cd typescript
./start_chat.sh
```

## Project Structure

```
dgx_spark/
├── vllm-qwen3-coder-30b/    # vLLM server (port 8100)
├── web-gui/                  # React web interface (port 5173)
├── python/                   # Python CLI client
├── typescript/               # TypeScript CLI client
└── project_summary.md        # Complete documentation
```

## Components

### vLLM Server
- **Container:** `vllm-qwen3-coder-30b`
- **Port:** 8100
- **Features:** Persistent cache, auto-restart, OpenAI-compatible API
- **Manage:** `docker stop/start/restart vllm-qwen3-coder-30b`

### Web GUI
- Modern dark mode interface
- Real-time chat with animations
- Built with React + TypeScript + Vite

### CLI Clients
- **Python:** Streaming responses, history management
- **TypeScript:** Interactive terminal, type-safe

## Managing the Server

```bash
# Stop
docker stop vllm-qwen3-coder-30b

# Start (fast - uses cached model)
docker start vllm-qwen3-coder-30b

# Restart
docker restart vllm-qwen3-coder-30b

# View logs
docker logs -f vllm-qwen3-coder-30b
```

## Adding New Models

1. Copy the template:
   ```bash
   cp -r vllm-qwen3-coder-30b vllm-{new-model}
   ```

2. Edit `serve-v2.sh`:
   - Update `CONTAINER_NAME`
   - Update `MODEL_NAME`
   - Update `PORT` (use 8101, 8102, etc.)

3. Start the new model:
   ```bash
   cd vllm-{new-model}
   ./serve-v2.sh
   ```

All models share the same cache directory - downloads happen only once!

## Configuration

**Current Setup:**
- **API URL:** http://localhost:8100/v1
- **Model:** Qwen/Qwen3-Coder-30B-A3B-Instruct
- **Context Length:** 32,768 tokens
- **Max Concurrent Requests:** 256
- **GPU Memory:** 85% utilization

## Documentation

📖 **[project_summary.md](project_summary.md)** - Complete documentation including:
- Detailed server configuration
- Performance metrics & benchmarks
- API endpoints & examples
- Troubleshooting guide
- Client implementation details

## Requirements

- **GPU:** NVIDIA with 56+ GiB VRAM
- **Docker:** With NVIDIA container runtime
- **Node.js:** v18+ (for web-gui and TypeScript client)
- **Python:** 3.x (for Python client)

## Current Status

✅ vLLM Server: Running on port 8100
✅ Web GUI: Running on port 5173
✅ Model Cache: Active
✅ API: Fully operational

---

*For detailed information, see [project_summary.md](project_summary.md)*
