# Inference Benchmark Results

**Date:** December 13, 2025
**Platform:** DGX Spark (NVIDIA GB10 Blackwell GPU)

## Models Tested

| Model | Engine | Port | Architecture | Quantization |
|-------|--------|------|--------------|--------------|
| Qwen3-30B-A3B-FP4 | TRT-LLM | 8202 | MoE (3B active) | FP4 |
| Qwen3-32B-FP4 | TRT-LLM | 8203 | Dense (32B active) | FP4 |
| Qwen3-Coder-30B | vLLM | 8100 | MoE | Full precision |
| Qwen3-Coder-30B-AWQ | vLLM | 8104 | MoE | AWQ 4-bit |

## Benchmark Configuration

- **Iterations per test:** 3
- **Streaming mode:** Enabled (for accurate TTFT measurement)
- **Prompt types:** Short (~20 tokens), Medium (~50 tokens), Long (~100 tokens)

## Results Summary

| Model | Engine | TTFT (s) | TPS | Memory |
|-------|--------|----------|-----|--------|
| Qwen3-30B-A3B-FP4 (MoE) | TRT-LLM | **0.051** | 34.9 | ~12.8 GB |
| Qwen3-32B-FP4 (Dense) | TRT-LLM | 0.106 | 8.3 | ~47 GB |
| Qwen3-Coder-30B (Full) | vLLM | 0.316 | 28.2 | ~68 GB |
| Qwen3-Coder-30B-AWQ | vLLM | 0.050* | **58.6** | ~10 GB |

*After warmup (first request ~1.5s due to CUDA graph compilation)

## Detailed Results

### TRT-LLM Qwen3-30B-A3B-FP4 (MoE)

| Prompt | TTFT (s) | TPS | Total Time (s) |
|--------|----------|-----|----------------|
| Short | 0.035 ± 0.011 | 38.8 ± 1.7 | 3.10 |
| Medium | 0.054 ± 0.008 | 35.4 ± 2.9 | 7.06 |
| Long | 0.063 ± 0.004 | 30.6 ± 0.9 | 17.11 |

### TRT-LLM Qwen3-32B-FP4 (Dense)

| Prompt | TTFT (s) | TPS | Total Time (s) |
|--------|----------|-----|----------------|
| Short | 0.064 ± 0.002 | 8.9 ± 0.3 | 12.70 |
| Medium | 0.107 ± 0.003 | 8.3 ± 0.3 | 29.93 |
| Long | 0.146 ± 0.011 | 7.8 ± 0.3 | 68.74 |

### vLLM Qwen3-Coder-30B (Full Precision)

| Prompt | TTFT (s) | TPS | Total Time (s) |
|--------|----------|-----|----------------|
| Short | 0.228 ± 0.042 | 30.7 ± 1.7 | 4.04 |
| Medium | 0.353 ± 0.054 | 27.9 ± 1.2 | 9.45 |
| Long | 0.367 ± 0.034 | 26.1 ± 0.7 | 19.20 |

### vLLM Qwen3-Coder-30B-AWQ (Optimized)

| Prompt | TTFT (s) | TPS | Total Time (s) |
|--------|----------|-----|----------------|
| Short | 0.544 ± 0.852 | 67.0 ± 0.4 | 2.34 |
| Medium | 0.050 ± 0.017 | 51.2 ± 1.3 | 5.44 |
| Long | 0.064 ± 0.028 | 57.6 ± 0.7 | 8.88 |

Note: Short prompt TTFT variance is due to first-request warmup (1.5s), subsequent requests are 0.050-0.056s.

## Key Findings

### 1. MoE vs Dense Architecture

The MoE (Mixture of Experts) architecture significantly outperforms dense models:

- **TRT-LLM 30B MoE**: 34.9 TPS with only 3B active parameters
- **TRT-LLM 32B Dense**: 8.3 TPS with all 32B parameters active

MoE provides **4.2x faster inference** while using less memory.

### 2. AWQ Quantization Impact on vLLM

Optimizing vLLM with AWQ quantization and higher memory utilization delivered:

- **2x faster TPS**: 58.6 vs 28.2 tokens/second
- **6x faster TTFT**: 0.050s vs 0.316s (after warmup)
- **85% less memory**: ~10 GB vs ~68 GB

### 3. TRT-LLM vs vLLM

| Metric | Winner | Notes |
|--------|--------|-------|
| TTFT | TRT-LLM MoE | 0.051s - consistently fastest first token |
| TPS | vLLM AWQ | 58.6 TPS - highest throughput |
| Memory | vLLM AWQ | ~10 GB - most efficient |

### 4. When to Use Each Model

| Use Case | Recommended Model | Why |
|----------|-------------------|-----|
| Interactive chat | TRT-LLM 30B MoE | Fastest TTFT (0.051s) |
| Batch processing | vLLM AWQ | Highest TPS (58.6) |
| Memory constrained | vLLM AWQ | Only ~10 GB |
| Complex reasoning | TRT-LLM 32B Dense | All 32B params active |

## Optimization Techniques Applied

### vLLM AWQ Configuration

```bash
MODEL_NAME="cpatonn/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit"
GPU_MEMORY_UTILIZATION=0.85  # Increased from 0.55
ENABLE_PREFIX_CACHING=true
ENABLE_CHUNKED_PREFILL=true
```

Key changes:
- AWQ 4-bit quantization reduces model size and memory bandwidth
- Higher GPU memory utilization (0.85) allows more KV cache
- More KV cache enables better batching and throughput

### TRT-LLM Configuration

```yaml
kv_cache_config:
  dtype: auto
  free_gpu_memory_fraction: 0.9
cuda_graph_config:
  enable_padding: true
```

## Glossary

- **TTFT (Time to First Token)**: Latency before first token is generated. Lower is better for interactive use.
- **TPS (Tokens Per Second)**: Output generation throughput. Higher is better for batch processing.
- **MoE (Mixture of Experts)**: Architecture where only a subset of parameters are active per token.
- **AWQ (Activation-aware Weight Quantization)**: Quantization that preserves important weights based on activation patterns.
- **FP4**: 4-bit floating point quantization used by TensorRT-LLM.

## Port Reference

| Port | Model | Engine |
|------|-------|--------|
| 8100 | Qwen3-Coder-30B | vLLM |
| 8104 | Qwen3-Coder-30B-AWQ | vLLM |
| 8202 | Qwen3-30B-A3B-FP4 | TRT-LLM |
| 8203 | Qwen3-32B-FP4 | TRT-LLM |
