# DGX Spark - vLLM Model Serving Project

## Overview

Local LLM serving infrastructure using vLLM with OpenAI-compatible API, supporting multiple models with persistent caching.

## Current Setup

### vLLM Server - Qwen3-Coder-30B

**Container:** `vllm-qwen3-coder-30b`
**Port:** `8100`
**Model:** `Qwen/Qwen3-Coder-30B-A3B-Instruct`
**Image:** `nvcr.io/nvidia/vllm:25.09-py3`
**vLLM Version:** 0.10.1.1+381074ae.nv25.09

#### Configuration
- **Max Context Length:** 32,768 tokens
- **Max Concurrent Sequences:** 256
- **GPU Memory Utilization:** 85%
- **Features:**
  - Prefix caching enabled
  - Chunked prefill enabled
  - Auto tool choice enabled
  - Qwen3 Coder tool parser

#### Performance Metrics
- **Model Size:** 56.9 GiB GPU memory
- **KV Cache:** 42.24 GiB (461,376 tokens)
- **Max Concurrency:** 14.08x for 32K token requests
- **Startup Time (with cache):** ~8 minutes
  - Model loading: 6 minutes
  - Compilation: 33 seconds
  - CUDA graph capture: 7 seconds

#### Default Sampling Parameters
```json
{
  "temperature": 0.7,
  "top_p": 0.8,
  "top_k": 20,
  "repetition_penalty": 1.05
}
```

### Cache Configuration

**Cache Directory:** `~/.cache/huggingface`
**Benefit:** Persistent model storage across container restarts

**Performance Comparison:**
- First run (no cache): ~15 minutes (7.7 min download + 6 min load + 1 min init)
- Subsequent runs (cached): ~8 minutes (6 min load + 1 min init)
- **Time saved per restart:** ~7 minutes

## Directory Structure

```
dgx_spark/
├── vllm-qwen3-coder-30b/      # Model-specific server setup
│   ├── serve-v2.sh             # Main server script (persistent cache)
│   ├── serve.sh                # One-time run script
│   ├── test-server.sh          # API test script
│   └── README.md               # Model-specific documentation
│
├── web-gui/                    # React/Vite web interface
│   ├── src/api.ts              # API client (port: 8100)
│   └── package.json            # Dependencies
│
├── python/                     # Python CLI client
│   ├── chat.py                 # CLI chat (port: 8100)
│   └── start_chat.sh           # Launcher script
│
├── typescript/                 # TypeScript CLI client
│   ├── chat.ts                 # CLI chat (port: 8100)
│   └── start_chat.sh           # Launcher script
│
└── project_summary.md          # This file
```

## Port Allocation

- **8100** - Qwen3-Coder-30B (current)
- **8101** - Reserved for next model
- **8102** - Reserved for next model
- **5173** - Web GUI (Vite dev server)

## Managing Services

### vLLM Server

**Start:**
```bash
cd vllm-qwen3-coder-30b
./serve-v2.sh
```

**Manage:**
```bash
# Stop
docker stop vllm-qwen3-coder-30b

# Start (fast - cached model)
docker start vllm-qwen3-coder-30b

# Restart
docker restart vllm-qwen3-coder-30b

# View logs
docker logs -f vllm-qwen3-coder-30b

# Remove
docker rm -f vllm-qwen3-coder-30b
```

### Web GUI

**Start:**
```bash
cd web-gui
npm run dev
```

**Access:** http://localhost:5173

### Python Client

**Start:**
```bash
cd python
./start_chat.sh
```

### TypeScript Client

**Start:**
```bash
cd typescript
./start_chat.sh
```

## API Endpoints

**Base URL:** http://localhost:8100/v1

### Available Routes
- `/v1/chat/completions` - Chat completions (OpenAI compatible)
- `/v1/completions` - Text completions
- `/v1/models` - List available models
- `/health` - Health check
- `/metrics` - Prometheus metrics
- `/docs` - API documentation

### Example Request

```bash
curl http://localhost:8100/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-Coder-30B-A3B-Instruct",
    "messages": [
      {"role": "user", "content": "Write a Python function to check if a number is prime"}
    ],
    "max_tokens": 500,
    "temperature": 0.7
  }'
```

## Adding New Models

### 1. Copy Template
```bash
cp -r vllm-qwen3-coder-30b vllm-{new-model-name}
```

### 2. Update Configuration
Edit `serve-v2.sh`:
```bash
CONTAINER_NAME="vllm-{new-model-name}"
MODEL_NAME="huggingface/model-path"
PORT=8101  # Next available port
```

### 3. Update Test Script
Edit `test-server.sh`:
```bash
PORT=${1:-8101}
```

### 4. Start Server
```bash
cd vllm-{new-model-name}
./serve-v2.sh
```

All models share the same HuggingFace cache, so downloads happen only once.

## Client Implementations

The project includes three ways to interact with the LLM API:

### 1. Python CLI Chat

**Location:** `python/`

**Features:**
- Streaming text output with typewriter effect
- Conversation history management
- Commands: `/exit`, `/quit`, `/clear`, `/history`
- Model info fetching

**How to Run:**
```bash
cd python
./start_chat.sh
# or
python chat.py
```

**Dependencies:**
- Python 3.x
- `requests` library

### 2. TypeScript CLI Chat

**Location:** `typescript/`

**Features:**
- Interactive CLI with typewriter effect
- Message history tracking
- Model info fetching
- Commands: `/exit`, `/quit`, `/clear`, `/history`

**How to Run:**
```bash
cd typescript
./start_chat.sh
# or
npm run chat
```

**Dependencies:**
- Node.js v18+
- npm packages: `typescript`, `tsx`, `@types/node`

### 3. Web GUI (React + TypeScript)

**Location:** `web-gui/`

**Features:**
- Modern dark mode UI
- Real-time chat with animations
- Auto-scroll to latest messages
- Clear history button
- Loading indicators & error handling
- Responsive design with gradients

**How to Run:**
```bash
cd web-gui
npm install    # First time only
npm run dev
```

**Access:** http://localhost:5173

**Dependencies:**
- Node.js v18+
- npm packages: `react`, `vite`, `typescript`

### Client Comparison

| Feature | Python CLI | TypeScript CLI | Web GUI |
|---------|-----------|----------------|---------|
| Interface | Terminal | Terminal | Browser |
| Streaming | Yes | No | No |
| History | Yes | Yes | Yes |
| Model Info | Yes | Yes | Yes |
| UI/UX | Basic | Good | Excellent |
| Dark Mode | N/A | N/A | Yes |
| Port Used | 8100 | 8100 | 8100 |

## GPU Information

**GPU:** NVIDIA GB10
**Total Memory:** 119.7 GiB
**Driver:** 580.95.05
**CUDA:** 13.0

## System Requirements

### Docker Configuration
```bash
docker run \
  --gpus all \
  --ipc=host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -p {PORT}:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  nvcr.io/nvidia/vllm:25.09-py3
```

## Known Issues & Warnings

### Non-Critical Warnings

1. **MoE Performance Warning**
   - Impact: Sub-optimal MoE layer performance
   - Status: Acceptable for dev/testing
   - Fix: Create custom config for NVIDIA GB10 (advanced)

2. **SM Count Warning**
   - Impact: GEMM operations won't use maximum auto-tuning
   - Status: GPU hardware limitation
   - Fix: None (hardware-specific)

3. **Deprecated Package (pynvml)**
   - Impact: None currently
   - Status: Will be fixed in future vLLM releases

## Performance Tuning

### Increase Context Window
```bash
# In serve-v2.sh
MAX_MODEL_LEN=65536  # 64K tokens
```

### Adjust Concurrency
```bash
# More concurrent users
MAX_NUM_SEQS=512

# Faster single responses
MAX_NUM_SEQS=128
```

### GPU Memory Optimization
```bash
# Use more GPU memory
GPU_MEMORY_UTILIZATION=0.95

# Conservative (safer)
GPU_MEMORY_UTILIZATION=0.80
```

## Client Configuration

All clients are configured to connect to `http://localhost:8100/v1`:

- **web-gui:** `src/api.ts` line 10
- **python:** `chat.py` lines 13, 189
- **typescript:** `chat.ts` line 248

## Troubleshooting

### Container Won't Start
```bash
# Check if port is in use
lsof -i :8100

# Check GPU availability
nvidia-smi

# View container logs
docker logs vllm-qwen3-coder-30b
```

### Out of Memory
1. Reduce `GPU_MEMORY_UTILIZATION` to 0.80
2. Reduce `MAX_MODEL_LEN` to 16384
3. Reduce `MAX_NUM_SEQS` to 128
4. Close other GPU processes (Firefox, VS Code)

### Slow Performance
1. Ensure model is cached (check startup logs)
2. Enable prefix caching (already enabled)
3. Check GPU utilization: `nvidia-smi`

## Resources

- [vLLM Documentation](https://docs.vllm.ai/)
- [Qwen3-Coder Recipe](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3-Coder-480B-A35B.html)
- [NVIDIA vLLM Container](https://build.nvidia.com/spark/vllm/instructions)
- [OpenAI API Compatibility](https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html)

## Current Status

✅ vLLM server: Running on port 8100
✅ Web GUI: Running on port 5173
✅ Model cache: Active
✅ API: Fully operational
✅ Clients: Python, TypeScript, Web GUI configured

**Last Updated:** 2025-11-15
