# TensorRT-LLM Nemotron-3-Nano-30B FP8

NVIDIA Nemotron-3-Nano-30B-A3B with FP8 quantization using TensorRT-LLM AutoDeploy.

## Web GUI Integration

This model is managed via the web-gui model-manager. It uses `engine: "trtllm"` in `models.json`, which calls the local `serve.sh`/`stop.sh` scripts.

**Entry in `/home/dan/danProjects/dgx_spark/models.json`:**
```json
{
  "nemotron-3-nano-30b-fp8": {
    "name": "Nemotron-3-Nano-30B-FP8",
    "engine": "trtllm",
    "port": 8107,
    "container_name": "trtllm-nemotron-3-nano-30b-fp8",
    "model_id": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8",
    "script_dir": "trtllm-nemotron-3-nano-30b-fp8"
  }
}
```

## Quick Start

```bash
./serve.sh      # Start (first time: ~5min compile, subsequent: instant if container preserved)
./stop.sh       # Stop (preserves container for fast restart)
./restart.sh    # Fast restart (if container was stopped, not removed)
```

## API Endpoint

**Base URL:** `http://localhost:8107/v1`

## API Usage Examples

### List Models
```bash
curl http://localhost:8107/v1/models
```

### Chat Completion
```bash
curl http://localhost:8107/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }'
```

### Chat Completion (Disable Reasoning)
```bash
curl http://localhost:8107/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8",
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "max_tokens": 100,
    "extra_body": {"chat_template_kwargs": {"enable_thinking": false}}
  }'
```

### Streaming
```bash
curl http://localhost:8107/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8",
    "messages": [{"role": "user", "content": "Tell me a joke"}],
    "max_tokens": 200,
    "stream": true
  }'
```

### Tool Calling
```bash
curl http://localhost:8107/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8",
    "messages": [{"role": "user", "content": "What is the weather in Paris?"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get weather for a location",
        "parameters": {
          "type": "object",
          "properties": {"location": {"type": "string"}},
          "required": ["location"]
        }
      }
    }],
    "max_tokens": 200
  }'
```

### Python Client
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8107/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=100
)
print(response.choices[0].message.content)
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/v1/models` | List available models |
| `/v1/chat/completions` | Chat completion (OpenAI compatible) |
| `/v1/completions` | Text completion |
| `/health` | Health check |
| `/metrics` | Runtime statistics |
| `/version` | Server version |

## Response Format

The model returns responses with reasoning enabled by default:

```json
{
  "choices": [{
    "message": {
      "content": "Final answer here",
      "reasoning_content": "Model's thinking process..."
    }
  }]
}
```

## Container Management

```bash
# View logs
docker logs -f trtllm-nemotron-3-nano-30b-fp8

# Stop (preserve for fast restart)
./stop.sh

# Fast restart (no recompilation)
./restart.sh

# Full restart (removes container, requires recompilation)
docker rm trtllm-nemotron-3-nano-30b-fp8
./serve.sh
```

## Configuration

See `nano_v3.yaml` for TRT-LLM settings:
- `max_batch_size`: 8
- `max_seq_len`: 16384
- FP8 quantization enabled
- Mamba-2 + Transformer MoE optimizations

## Adding New Models (Template)

This directory serves as a template for adding new models with custom configurations.

### Step 1: Create model directory

```bash
mkdir /home/dan/danProjects/dgx_spark/<engine>-<model-name>
cd /home/dan/danProjects/dgx_spark/<engine>-<model-name>
```

### Step 2: Create serve.sh

```bash
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER_NAME="<container-name>"
PORT=<port>

# Check if already running
if [ "$(docker ps -q -f name=^${CONTAINER_NAME}$)" ]; then
    echo "Already running"
    exit 0
fi

# Remove stopped container
if [ "$(docker ps -aq -f name=^${CONTAINER_NAME}$)" ]; then
    docker rm ${CONTAINER_NAME}
fi

# Start container
docker run -d \
  --name ${CONTAINER_NAME} \
  --gpus all \
  -p ${PORT}:<internal-port> \
  # ... your docker options ...
  <image> <command>

# Only follow logs if interactive
if [ -t 1 ]; then
    docker logs -f ${CONTAINER_NAME}
fi
```

### Step 3: Create stop.sh

```bash
#!/bin/bash
CONTAINER_NAME="<container-name>"
if [ "$(docker ps -q -f name=^${CONTAINER_NAME}$)" ]; then
    docker stop ${CONTAINER_NAME}
    echo "Stopped (preserved for fast restart)"
fi
```

### Step 4: Add to models.json

```json
{
  "<model-id>": {
    "name": "<Display Name>",
    "engine": "trtllm",
    "port": <port>,
    "container_name": "<container-name>",
    "model_id": "<huggingface-model-id>",
    "script_dir": "<directory-name>"
  }
}
```

### Key files in this directory

| File | Purpose |
|------|---------|
| `serve.sh` | Starts the Docker container |
| `stop.sh` | Stops container (preserves for fast restart) |
| `restart.sh` | Restarts a stopped container |
| `nano_v3.yaml` | TRT-LLM AutoDeploy configuration |
| `README.md` | This documentation |

## References

- [TRT-LLM trtllm-serve docs](https://nvidia.github.io/TensorRT-LLM/commands/trtllm-serve.html)
- [Nemotron-3-Nano Cookbook](https://github.com/NVIDIA-NeMo/Nemotron/blob/main/usage-cookbook/Nemotron-3-Nano/trtllm_cookbook.ipynb)
- [Model on HuggingFace](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8)
