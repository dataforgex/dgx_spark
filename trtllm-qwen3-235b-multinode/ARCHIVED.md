# ARCHIVED: TensorRT-LLM Qwen3-235B Multinode

**Status:** Not working on DGX Spark (GB10)

## Why This Was Archived

TensorRT-LLM multinode deployment failed for multiple reasons:

1. **TRT-LLM GB10 Compatibility**: TensorRT-LLM has limited support for GB10 (sm_121a)
2. **MPI/NCCL Issues**: Multinode communication setup was problematic
3. **Engine Build**: Could not successfully build TRT-LLM engines for this model

## Alternative

Use vLLM with Ray cluster instead:
- Model: `qwen3-235b-awq`
- Folder: `vllm-qwen3-235b-awq`
- Uses AWQ quantization (116GB) distributed across 2 DGX Sparks via Ray

## Original Files

The original serve.sh and configuration files were removed on 2026-01-14.
See git history for the original implementation.
