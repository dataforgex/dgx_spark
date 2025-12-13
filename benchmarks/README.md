# Inference Benchmarks

Scripts to compare inference speed across different model deployments.

## Metrics

- **TTFT (Time to First Token)**: Latency before first token is generated
- **TPS (Tokens Per Second)**: Output generation throughput

## Models Compared

| Model | Port | Engine | Architecture |
|-------|------|--------|--------------|
| Qwen3-30B-A3B-FP4 | 8202 | TRT-LLM | MoE (3B active) |
| Qwen3-32B-FP4 | 8203 | TRT-LLM | Dense (32B active) |
| Qwen3-Coder-30B | 8100 | vLLM | MoE (full precision) |

## Quick Start

### 1. Start the models you want to test

```bash
# Start one at a time (they use significant GPU memory)

# Option A: TRT-LLM 30B MoE
cd /home/dan/danProjects/dgx_spark/trtllm-qwen3-30b-fp4 && ./serve.sh

# Option B: TRT-LLM 32B Dense
cd /home/dan/danProjects/dgx_spark/trtllm-qwen3-32b-fp4 && ./serve.sh

# Option C: vLLM 30B
cd /home/dan/danProjects/dgx_spark/vllm-qwen3-coder-30b && ./serve.sh
```

### 2. Run the benchmark

```bash
cd /home/dan/danProjects/dgx_spark/benchmarks

# Test all available models
python benchmark_inference.py

# Test only TRT-LLM models
python benchmark_inference.py --models trtllm

# Test only vLLM
python benchmark_inference.py --models vllm

# More iterations for better accuracy
python benchmark_inference.py --iterations 5
```

## Test Plan

### Phase 1: Individual Model Testing
Test each model separately to get baseline numbers:

1. Start TRT-LLM Qwen3-30B-A3B-FP4, run benchmark, stop
2. Start TRT-LLM Qwen3-32B-FP4, run benchmark, stop
3. Start vLLM Qwen3-Coder-30B, run benchmark, stop

### Phase 2: Prompt Complexity
The benchmark tests 3 prompt types:
- **Short**: ~20 input tokens, 100 output tokens
- **Medium**: ~50 input tokens, 300 output tokens
- **Long**: ~100 input tokens, 500 output tokens

### Phase 3: Analysis
Compare:
- TTFT across models (lower is better for interactive use)
- TPS across models (higher is better for throughput)
- Memory usage (check nvidia-smi during tests)

## Expected Results

Based on architecture:

| Model | Expected TTFT | Expected TPS | Memory |
|-------|---------------|--------------|--------|
| TRT-LLM 30B MoE | Fastest | Highest | Lowest |
| TRT-LLM 32B Dense | Medium | Medium | Higher |
| vLLM 30B | Slowest | Lower | Highest |

**Why MoE should be faster:**
- Only 3B parameters active per token
- FP4 quantization reduces memory bandwidth

**Why TRT-LLM should beat vLLM:**
- TensorRT optimizations for Blackwell GPU
- FP4 quantization vs full precision

## Output

Results are saved to `benchmark_results_<timestamp>.json` and printed as a comparison table.

## Customization

Edit `benchmark_inference.py` to:
- Add more test prompts
- Change max_tokens
- Adjust temperature
- Add new models
