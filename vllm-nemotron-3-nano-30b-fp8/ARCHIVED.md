# ARCHIVED: vLLM Nemotron-3-Nano-30B-FP8

**Status:** Not working - FP8 quantization issues on GB10

## Why This Was Archived

FP8 (8-bit floating point) quantization has issues on DGX Spark:

1. **NVFP8 Compatibility**: The FP8 kernels are not fully optimized for GB10
2. **Accuracy Issues**: FP8 inference produced degraded results
3. **Duplicate Effort**: BF16 version works reliably

## Alternative

Use BF16 precision instead:
- Model: `nemotron-3-nano-30b-bf16`
- Folder: `vllm-nemotron-3-nano-30b-bf16`

BF16 provides good balance of speed and accuracy on unified memory systems.

## Original Files

The original serve.sh and configuration files were removed on 2026-01-14.
See git history for the original implementation.
