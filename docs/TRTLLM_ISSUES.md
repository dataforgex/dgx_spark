# TensorRT-LLM Issues Summary

Removed TRT-LLM models from the project on 2025-12-13 due to the following issues.

## Models Tested

| Model | Status | Issue |
|-------|--------|-------|
| Qwen2.5-VL-7B-FP8 | Failed | Garbage output |
| Qwen2.5-VL-7B-FP4 | Failed | Garbage output |
| Qwen3-30B-A3B-FP4 | Partial | No tool calling |
| Qwen3-32B-FP4 | Partial | No tool calling |

## Issue Details

### 1. Garbage Output (Qwen2.5-VL Models)

Both FP8 and FP4 quantized versions of Qwen2.5-VL-7B produced nonsensical repeated text:

```
addCriterion addCriterion addCriterion addCriterion...
```

- Occurred on simple prompts like "what time is it?"
- Not a configuration issue - followed NVIDIA's official examples
- Appears to be a bug in NVIDIA's model conversion/quantization

### 2. No Tool Calling Support

TRT-LLM does not support OpenAI-compatible tool calling:

- When given tools, models output raw `<tool_call>` XML in text response
- Cannot execute function calls like web search
- vLLM supports this with `--enable-auto-tool-choice` flag

**Example TRT-LLM response (broken):**
```
<tool_call>{"name": "web_search", "arguments": {"query": "current time"}}</tool_call>
```

**Expected behavior (vLLM):**
```json
{
  "tool_calls": [{"function": {"name": "web_search", "arguments": "{\"query\": \"current time\"}"}}]
}
```

### 3. No Native CORS Support

- TRT-LLM servers don't include CORS headers
- Required nginx reverse proxy layer for browser access
- Added complexity and potential failure points
- vLLM has CORS enabled by default

## Configuration Used

```yaml
# /home/dan/.cache/huggingface/trtllm-configs/qwen2.5-vl-7b-fp4-config.yml
print_iter_log: false
kv_cache_config:
  dtype: auto
  free_gpu_memory_fraction: 0.9
cuda_graph_config:
  enable_padding: true
disable_overlap_scheduler: true
```

## 4. Performance Not Competitive

Benchmark comparison (same MoE architecture, same settings):

| Metric | TRT-LLM FP4 | vLLM AWQ | Winner |
|--------|-------------|----------|--------|
| TTFT | **0.054s** | 0.069s | TRT-LLM (28% faster) |
| TPS | 32 | **52** | vLLM (63% faster) |
| Memory | ~33 GB | ~34 GB | Tie |

**Key finding:** vLLM delivers **63% higher throughput** while TRT-LLM only wins on TTFT by 28%.

For the Dense 32B model (TRT-LLM only):
- TPS: 7.8 (very slow)
- TTFT: 0.113s
- Memory: ~44 GB

The dense model is impractical for interactive use at 7.8 TPS.

## Conclusion

TRT-LLM was removed in favor of vLLM which provides:
- Reliable output quality (no garbage output bugs)
- OpenAI-compatible tool calling
- Native CORS support
- Simpler architecture (no proxy needed)
- **63% higher throughput** (52 vs 32 TPS)

May revisit TRT-LLM when NVIDIA addresses these issues.
