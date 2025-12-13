# Inference Benchmark Results

**Date:** December 13, 2025
**Platform:** DGX Spark (NVIDIA GB10 Blackwell GPU)

## Models Tested

| Model | Engine | Port | Architecture | Quantization |
|-------|--------|------|--------------|--------------|
| Qwen3-30B-A3B-FP4 | TRT-LLM | 8202 | MoE (3B active) | FP4 |
| Qwen3-32B-FP4 | TRT-LLM | 8203 | Dense (32B active) | FP4 |
| Qwen3-Coder-30B-AWQ | vLLM | 8104 | MoE (3B active) | AWQ 4-bit |

## Benchmark Configuration

- **Iterations per test:** 3
- **Streaming mode:** Enabled (for accurate TTFT measurement)
- **Prompt types:** Short (~20 tokens), Medium (~50 tokens), Long (~100 tokens)
- **Standard settings:** 32K context, 8 concurrent, 0.3 GPU memory fraction

## Results Summary

| Model | Engine | TTFT (s) | TPS | Model Size | Runtime Memory |
|-------|--------|----------|-----|------------|----------------|
| Qwen3-30B-A3B-FP4 (MoE) | TRT-LLM | **0.054** | 32.0 | ~12.8 GB | ~33 GB |
| Qwen3-32B-FP4 (Dense) | TRT-LLM | 0.113 | 7.8 | ~47 GB | ~44 GB |
| Qwen3-Coder-30B-AWQ (MoE) | vLLM | 0.069 | **52.0** | ~17 GB | ~34 GB |

All tests use: 32K context, 8 concurrent sequences, 0.3-0.85 GPU memory fraction

## Detailed Results

### TRT-LLM Qwen3-30B-A3B-FP4 (MoE)

| Prompt | TTFT (s) | TPS | Total Time (s) |
|--------|----------|-----|----------------|
| Short | 0.088 | 32.2 | 3.20 |
| Medium | 0.055 | 32.0 | 3.18 |
| Long | 0.054 | 32.1 | 3.17 |

### TRT-LLM Qwen3-32B-FP4 (Dense)

| Prompt | TTFT (s) | TPS | Total Time (s) |
|--------|----------|-----|----------------|
| Short | 0.118 ± 0.009 | 7.8 ± 0.2 | 13.22 |
| Medium | 0.110 ± 0.006 | 7.8 ± 0.0 | 39.46 |
| Long | 0.112 ± 0.005 | 7.8 ± 0.0 | 66.11 |

### vLLM Qwen3-Coder-30B-AWQ (MoE)

| Prompt | TTFT (s) | TPS | Total Time (s) |
|--------|----------|-----|----------------|
| Short | 0.074 | 52.5 | 1.98 |
| Medium | 0.069 | 51.4 | 1.55 |
| Long | 0.070 | 52.0 | 2.00 |

Note: First request has ~1-2s warmup due to CUDA graph compilation.

## Key Findings

### 1. MoE vs Dense Architecture

The MoE (Mixture of Experts) architecture significantly outperforms dense models:

- **30B MoE**: 32-52 TPS with only 3B active parameters
- **32B Dense**: 8.3 TPS with all 32B parameters active

MoE provides **4-6x faster inference** while using less memory.

### 2. TRT-LLM vs vLLM (Same Settings)

| Metric | TRT-LLM MoE | vLLM AWQ | Winner |
|--------|-------------|----------|--------|
| TTFT | **0.054s** | 0.069s | TRT-LLM (28% faster) |
| TPS | 32 | **52** | vLLM (63% faster) |
| Memory | ~33 GB | ~34 GB | Tie |

### 3. When to Use Each Model

| Use Case | Recommended Model | Why |
|----------|-------------------|-----|
| Interactive chat | TRT-LLM 30B MoE | Fastest TTFT (0.054s) |
| Batch processing | vLLM AWQ | Highest TPS (52) |
| Memory constrained | Either MoE model | Both ~33-34 GB |
| Complex reasoning | TRT-LLM 32B Dense | All 32B params active |

## Configuration

### vLLM AWQ (`vllm-qwen3-coder-30b-awq/serve.sh`)

```bash
MAX_MODEL_LEN=32768              # 32K context
MAX_NUM_SEQS=8                   # 8 concurrent sequences
GPU_MEMORY_UTILIZATION=0.30      # ~34 GB runtime
```

Features:
- AWQ 4-bit quantization (model weights ~17 GB)
- Prefix caching enabled
- Chunked prefill enabled

### TRT-LLM FP4 (`trtllm-qwen3-30b-fp4/serve.sh`)

```bash
MAX_BATCH_SIZE=8                 # 8 concurrent sequences
MAX_SEQ_LEN=32768                # 32K context
```

```yaml
kv_cache_config:
  dtype: auto
  free_gpu_memory_fraction: 0.3  # ~33 GB runtime
cuda_graph_config:
  enable_padding: true
```

### Recommended Settings

The default `serve.sh` scripts use optimized settings for DGX Spark:

| Setting | Value | Rationale |
|---------|-------|-----------|
| Context | 32K | Full context for complex tasks |
| Concurrent | 8 | Good balance of throughput and memory |
| GPU Memory | 0.3 | ~33-34 GB, leaves room for other tasks |

## DGX Spark / GB10 Notes

**FP8 KV Cache:** Not yet supported on GB10/Blackwell in vLLM. TRT-LLM handles this automatically.

**Unified Memory Architecture (UMA):** The GB10 shares 128GB RAM between CPU and GPU. Clear page cache before loading large models:
```bash
sudo sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'
```

## Glossary

- **TTFT (Time to First Token)**: Latency before first token is generated. Lower is better for interactive use.
- **TPS (Tokens Per Second)**: Output generation throughput. Higher is better for batch processing.
- **MoE (Mixture of Experts)**: Architecture where only a subset of parameters are active per token.
- **AWQ (Activation-aware Weight Quantization)**: 4-bit quantization that preserves important weights.
- **FP4**: 4-bit floating point quantization used by TensorRT-LLM.
- **Runtime Memory**: Actual GPU memory used during inference (model weights + KV cache + overhead).

## Port Reference

| Port | Model | Engine | Memory | Context | Concurrent |
|------|-------|--------|--------|---------|------------|
| 8104 | Qwen3-Coder-30B-AWQ | vLLM | ~34 GB | 32K | 8 |
| 8202 | Qwen3-30B-A3B-FP4 | TRT-LLM | ~33 GB | 32K | 8 |
| 8203 | Qwen3-32B-FP4 (Dense) | TRT-LLM | ~44 GB | 32K | 8 |
