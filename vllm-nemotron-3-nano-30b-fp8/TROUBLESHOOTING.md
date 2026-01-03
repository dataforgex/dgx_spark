# Nemotron-3-Nano-30B-FP8 on DGX Spark (GB10) - Troubleshooting

## Problem
The FP8 model fails to start with error:
```
RuntimeError: Check failed: (status == CUBLAS_STATUS_SUCCESS) is false:
bmm_fp8_internal_cublaslt failed: the library was not initialized
```

## Root Cause
- GB10 GPU has SM 12.1 (Blackwell architecture)
- FlashInfer detects SM >= 10.0 and uses `fp8_gemm_sm100` code path
- cuBLAS library is not properly initialized for FP8 operations on this architecture
- Error occurs during CUDA graph warmup/compilation phase

## What Was Tried

### 1. Official Documentation Settings
Added per [HuggingFace docs](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8):
- `VLLM_USE_FLASHINFER_MOE_FP8=1`
- `--kv-cache-dtype fp8`
- Removed `--enforce-eager`

**Result:** Same cuBLAS error during graph compilation

### 2. Disable FlashInfer FP8 + Eager Mode
- `VLLM_USE_FLASHINFER_MOE_FP8=0`
- `VLLM_DISABLE_FLASHINFER_FP8=1`
- `--enforce-eager` (disable CUDA graphs)

**Result:** Same error - flashinfer FP8 still being used

### 3. Use V0 Engine (Current Attempt)
- `VLLM_USE_V1=0` (use older V0 engine)
- `VLLM_USE_FLASHINFER_MOE_FP8=0`

**Status:** Not yet tested

## Planned Next Steps

1. **Test V0 Engine** - V0 may have different FP8 handling
2. **Try Different Attention Backend** - `VLLM_ATTENTION_BACKEND=FLASH_ATTN`
3. **Consider BF16 Alternative** - The BF16 model works on GB10

## Working Reference
The BF16 version at `/home/dan/danProjects/dgx_spark/vllm-nemotron-3-nano-30b-fb16` works correctly with similar settings (no FP8-specific flags).

## Related Issues
- [vLLM #21648](https://github.com/vllm-project/vllm/issues/21648) - FP8 on RTX 50 series / SM120
- [vLLM #28589](https://github.com/vllm-project/vllm/issues/28589) - V1 Engine fails on GB10
- [DGX Spark vLLM Setup](https://github.com/eelbaz/dgx-spark-vllm-setup) - Community fixes for GB10
