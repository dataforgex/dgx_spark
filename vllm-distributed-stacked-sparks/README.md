# vLLM Distributed Inference - Stacked DGX Sparks

This directory contains scripts and configuration for running distributed vLLM inference across two stacked DGX Spark systems using tensor parallelism.

**Reference**: https://build.nvidia.com/spark/vllm/stacked-sparks

## Architecture

```
┌─────────────────────┐     200GbE QSFP      ┌─────────────────────┐
│      spark-1        │◄───────────────────►│      spark-2        │
│   (Head Node)       │                      │   (Worker Node)     │
│   192.168.100.10    │                      │   192.168.100.11    │
│   NVIDIA GB10 GPU   │                      │   NVIDIA GB10 GPU   │
│   Ray Head + vLLM   │                      │   Ray Worker        │
└─────────────────────┘                      └─────────────────────┘
```

| Component | Value |
|-----------|-------|
| Container Image | `nvcr.io/nvidia/vllm:25.11-py3` |
| Network Interface | `enp1s0f1np1` |
| Head Node IP | `192.168.100.10` |
| Worker Node IP | `192.168.100.11` |
| API Port | `8000` |
| Default Model | `deepseek-ai/DeepSeek-R1-Distill-Llama-8B` |
| Tensor Parallel Size | `2` |

## Prerequisites

1. **Network Setup**: Both Sparks connected via 200GbE QSFP cable
   - Follow: https://build.nvidia.com/spark/connect-two-sparks/stacked-sparks

2. **NFS Shared Storage**: HuggingFace cache shared between nodes
   ```bash
   # On spark-1 (server)
   sudo apt install nfs-kernel-server
   echo "/home/dan/.cache/huggingface 192.168.100.0/24(rw,sync,no_subtree_check,no_root_squash)" | sudo tee -a /etc/exports
   sudo exportfs -ra
   sudo systemctl restart nfs-kernel-server

   # On spark-2 (client)
   sudo apt install nfs-common
   sudo mount -t nfs 192.168.100.10:/home/dan/.cache/huggingface /home/dan/.cache/huggingface
   ```

3. **Passwordless SSH**: Between nodes
   ```bash
   ssh-copy-id dan@192.168.100.11
   ```

4. **Docker Image**: Pull on both nodes
   ```bash
   docker pull nvcr.io/nvidia/vllm:25.11-py3
   ssh 192.168.100.11 "docker pull nvcr.io/nvidia/vllm:25.11-py3"
   ```

## Quick Start

### Option 1: All-in-One Script
```bash
./start-cluster.sh                    # Start Ray cluster on both nodes
./serve.sh                            # Start vLLM server
./test-server.sh                      # Test the API
```

### Option 2: Manual Start
```bash
# Terminal 1 (spark-1): Start head node
./start-head.sh

# Terminal 2 (spark-2 via SSH): Start worker node
ssh 192.168.100.11
cd /home/dan/danProjects/dgx_spark/vllm-distributed-stacked-sparks
./start-worker.sh

# Terminal 3 (spark-1): Start vLLM server
./serve.sh
```

## Scripts

| Script | Description |
|--------|-------------|
| `start-head.sh` | Start Ray head node on spark-1 |
| `start-worker.sh` | Start Ray worker node on spark-2 |
| `start-cluster.sh` | Start both head and worker nodes |
| `serve.sh` | Start vLLM inference server |
| `stop-cluster.sh` | Stop all containers on both nodes |
| `test-server.sh` | Test the inference API |
| `run_cluster.sh` | Official vLLM cluster script |

## Configuration

Edit variables at the top of `serve.sh`:

```bash
MODEL="deepseek-ai/DeepSeek-R1-Distill-Llama-8B"  # Model to serve
TENSOR_PARALLEL_SIZE=2                             # GPUs across nodes
MAX_MODEL_LEN=4096                                 # Context window
GPU_MEMORY_UTILIZATION=0.8                         # Memory usage
```

### Supported Models for TP=2

| Model | Size | Notes |
|-------|------|-------|
| `deepseek-ai/DeepSeek-R1-Distill-Llama-8B` | 15GB | Works well |
| `Qwen/Qwen3-Coder-30B-A3B-Instruct` | 57GB | Requires full BF16 |
| `meta-llama/Llama-3.3-70B-Instruct` | ~140GB | Official doc example |

## API Endpoints

Server runs on `http://localhost:8000` with OpenAI-compatible API.

### Completions
```bash
curl http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
    "prompt": "Hello, world!",
    "max_tokens": 64
  }'
```

### Chat Completions
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
    "messages": [{"role": "user", "content": "Hi!"}],
    "max_tokens": 64
  }'
```

### Python Client
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
    messages=[{"role": "user", "content": "Explain distributed computing"}],
    max_tokens=200
)
print(response.choices[0].message.content)
```

## Managing the Cluster

```bash
# Check Ray cluster status
docker exec node-* ray status

# View vLLM logs
docker exec node-* cat /tmp/vllm_serve.log

# Stop cluster
./stop-cluster.sh

# Restart cluster
./stop-cluster.sh && ./start-cluster.sh && ./serve.sh
```

## Performance

### Network Bandwidth (NCCL)
| Test | Bandwidth |
|------|-----------|
| All-gather (32MB) | 17.5 GB/s |
| All-gather (16GB) | 22.2 GB/s (177.6 Gbps) |

### Inference Performance
- Model load time: ~30 seconds (with CUDA graph compilation)
- Time to first token: depends on prompt length
- Throughput: scales with tensor parallelism

## Troubleshooting

### Worker Node Not Joining
```bash
# Check if worker can reach head
ssh 192.168.100.11 "ping -c 1 192.168.100.10"

# Check worker container logs
ssh 192.168.100.11 "docker logs node-*"
```

### Out of Memory
- Reduce `GPU_MEMORY_UTILIZATION`
- Reduce `MAX_MODEL_LEN`
- Use a smaller model

### Connection Refused on Port 8000
- Ensure vLLM server has fully started
- Check logs: `docker exec node-* cat /tmp/vllm_serve.log`

### NFS Mount Issues
```bash
# Remount on worker
ssh 192.168.100.11 "sudo mount -t nfs 192.168.100.10:/home/dan/.cache/huggingface /home/dan/.cache/huggingface"
```

## References

- [NVIDIA Stacked Sparks vLLM Guide](https://build.nvidia.com/spark/vllm/stacked-sparks)
- [NVIDIA Connect Two Sparks](https://build.nvidia.com/spark/connect-two-sparks/stacked-sparks)
- [NVIDIA NCCL Testing](https://build.nvidia.com/spark/nccl/stacked-sparks)
- [vLLM Documentation](https://docs.vllm.ai/)
- [vLLM Multi-Node Guide](https://docs.vllm.ai/en/latest/serving/distributed_serving.html)
