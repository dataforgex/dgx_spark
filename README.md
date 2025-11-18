# DGX Spark - Multi-Model LLM Serving with vLLM

Complete multi-model infrastructure for serving local LLMs using vLLM with OpenAI-compatible API and multiple client interfaces.

## Quick Start

### 1. Start the vLLM Servers

**Text/Code Model:**
```bash
cd vllm-qwen3-coder-30b
./serve.sh
```

**Vision Model:**
```bash
cd vllm-qwen2-vl-7b
./serve.sh
```

**Server Info:**
- **Port 8100**: Qwen3-Coder-30B (text/code generation)
- **Port 8101**: Qwen2-VL-7B (vision/image understanding)
- **Startup time**: ~8 minutes (cached), ~15 minutes (first run)
- **API**: http://localhost:8100/v1 and http://localhost:8101/v1

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
├── vllm-qwen3-coder-30b/    # Text/code model server (port 8100)
├── vllm-qwen2-vl-7b/         # Vision model server (port 8101)
├── web-gui/                  # React web interface (port 5173)
├── python/                   # Python CLI client
├── typescript/               # TypeScript CLI client
└── project_summary.md        # Complete documentation
```

## Components

### vLLM Servers

**Qwen3-Coder-30B (Text/Code):**
- **Container:** `vllm-qwen3-coder-30b`
- **Port:** 8100
- **GPU Memory:** 55% (~65 GB)
- **Use Cases:** Code generation, text analysis, structured outputs
- **Manage:** `docker stop/start/restart vllm-qwen3-coder-30b`

**Qwen2-VL-7B (Vision):**
- **Container:** `vllm-qwen2-vl-7b`
- **Port:** 8101
- **GPU Memory:** 25% (~26 GB)
- **Use Cases:** Image understanding, OCR, PDF/Excel processing, visual Q&A
- **Manage:** `docker stop/start/restart vllm-qwen2-vl-7b`

### Web GUI
- Modern dark mode interface
- Real-time chat with animations
- Built with React + TypeScript + Vite

### CLI Clients
- **Python:** Streaming responses, history management
- **TypeScript:** Interactive terminal, type-safe

## Managing the Servers

```bash
# Stop both models
docker stop vllm-qwen3-coder-30b vllm-qwen2-vl-7b

# Start individual models (fast - uses cached models)
docker start vllm-qwen3-coder-30b
docker start vllm-qwen2-vl-7b

# Restart
docker restart vllm-qwen3-coder-30b
docker restart vllm-qwen2-vl-7b

# View logs
docker logs -f vllm-qwen3-coder-30b
docker logs -f vllm-qwen2-vl-7b

# Check GPU usage
nvidia-smi
```

## Adding New Models

1. Copy the template:
   ```bash
   cp -r vllm-qwen3-coder-30b vllm-{new-model}
   ```

2. Edit `serve.sh`:
   - Update `CONTAINER_NAME`
   - Update `MODEL_NAME`
   - Update `PORT` (use 8102, 8103, etc.)
   - Adjust `GPU_MEMORY_UTILIZATION` (ensure total < 0.85)

3. Start the new model:
   ```bash
   cd vllm-{new-model}
   ./serve.sh
   ```

All models share the same cache directory - downloads happen only once!

**Current GPU Allocation:**
- Qwen3-Coder-30B: 55%
- Qwen2-VL-7B: 25%
- Total: 80% (20% safety margin)

## Configuration

**Current Multi-Model Setup:**

**Qwen3-Coder-30B:**
- **API URL:** http://localhost:8100/v1
- **Model:** Qwen/Qwen3-Coder-30B-A3B-Instruct
- **Context Length:** 32,768 tokens
- **Max Concurrent Requests:** 256
- **GPU Memory:** 55% (~65 GB)

**Qwen2-VL-7B:**
- **API URL:** http://localhost:8101/v1
- **Model:** Qwen/Qwen2-VL-7B-Instruct
- **Context Length:** 32,768 tokens
- **Max Concurrent Requests:** 64
- **GPU Memory:** 25% (~26 GB)

## Use Cases

**Qwen3-Coder-30B:**
- Code generation and analysis
- Mind map creation (JSON/Markdown)
- Data processing and transformation
- Complex reasoning tasks

**Qwen2-VL-7B:**
- Image description and understanding
- OCR / text extraction from images
- PDF document processing (via screenshots)
- Excel/table understanding (via screenshots)
- Visual question answering

**Combined Pipeline:**
1. Use Qwen2-VL to extract text from images/PDFs
2. Use Qwen3-Coder to analyze/transform extracted text

## API Examples

### Text/Code Generation (Port 8100)

```bash
curl http://localhost:8100/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-Coder-30B-A3B-Instruct",
    "messages": [
      {"role": "user", "content": "Write a Python function to check if a number is prime"}
    ],
    "max_tokens": 500
  }'
```

### Vision Understanding (Port 8101)

**Image from URL:**
```bash
curl http://localhost:8101/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2-VL-7B-Instruct",
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

**Local Image (Base64):**
```bash
IMAGE_B64=$(base64 -w 0 image.jpg)

curl http://localhost:8101/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2-VL-7B-Instruct",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,'$IMAGE_B64'"}},
        {"type": "text", "text": "Extract all text from this image"}
      ]
    }],
    "max_tokens": 500
  }'
```

## Troubleshooting

### Out of Memory Errors
```bash
# Check GPU usage
nvidia-smi

# If OOM occurs:
# 1. Stop both models
docker stop vllm-qwen3-coder-30b vllm-qwen2-vl-7b

# 2. Reduce GPU memory in serve.sh files:
#    - Qwen3-Coder: GPU_MEMORY_UTILIZATION=0.5 (down from 0.55)
#    - Qwen2-VL: GPU_MEMORY_UTILIZATION=0.2 (down from 0.25)

# 3. Restart models
cd vllm-qwen3-coder-30b && ./serve.sh
cd vllm-qwen2-vl-7b && ./serve.sh
```

### Container Won't Start
```bash
# Check if port is in use
lsof -i :8100
lsof -i :8101

# View container logs
docker logs vllm-qwen3-coder-30b
docker logs vllm-qwen2-vl-7b

# Remove stuck containers
docker rm -f vllm-qwen3-coder-30b vllm-qwen2-vl-7b
```

### Slow Performance
- Enable caching (already enabled in serve.sh)
- Reduce concurrent sequences if needed
- Ensure models are cached (check startup logs)
- Check GPU utilization: `nvidia-smi`

## Requirements

- **GPU:** NVIDIA with 93+ GiB VRAM (for both models)
- **Docker:** With NVIDIA container runtime
- **Node.js:** v18+ (for web-gui and TypeScript client)
- **Python:** 3.x (for Python client)

## Current Status

✅ Qwen3-Coder-30B: Running on port 8100 (text/code)
✅ Qwen2-VL-7B: Running on port 8101 (vision)
✅ Web GUI: Running on port 5173
✅ Model Cache: Active (shared across models)
✅ APIs: Fully operational
✅ Total GPU Usage: ~80% (~93 GB)
✅ Multi-model serving: Operational

---

**Need help?** Check the individual model READMEs:
- [vllm-qwen3-coder-30b/README.md](vllm-qwen3-coder-30b/README.md) - Text/code model details
- [vllm-qwen2-vl-7b/README.md](vllm-qwen2-vl-7b/README.md) - Vision model details
