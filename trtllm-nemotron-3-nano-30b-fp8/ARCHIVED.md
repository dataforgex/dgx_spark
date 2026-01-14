# ARCHIVED: TensorRT-LLM Nemotron-3-Nano-30B-FP8

**Status:** Not working on DGX Spark (GB10)

## Why This Was Archived

TensorRT-LLM has compatibility issues with the GB10 (Blackwell) GPU architecture:

1. **CUDA Compute Capability**: GB10 uses sm_121a which has limited TRT-LLM support
2. **FP8 Kernels**: The FP8 quantization kernels are not optimized for GB10
3. **Engine Build Failures**: TRT-LLM engine builds fail or produce incorrect results

## Alternative

Use vLLM with BF16 precision instead:
- Model: `nemotron-3-nano-30b-bf16`
- Folder: `vllm-nemotron-3-nano-30b-bf16`

## Original Files

The original serve.sh and configuration files were removed on 2026-01-14.
See git history for the original implementation.

## References

- [NVIDIA DGX Spark Documentation](https://docs.nvidia.com/dgx/)
- [TensorRT-LLM GitHub Issues](https://github.com/NVIDIA/TensorRT-LLM/issues)
