# Session Summary: New Model Deployment Attempts

**Date:** November 22, 2025  
**System:** NVIDIA GB10 (ARM64/aarch64, CUDA 12.1, 120GB VRAM)

## Models Attempted

### ❌ Moonlight-16B-A3B-Instruct
- **Status:** Failed
- **Issue:** Stopped to try newer models
- **Would it work?** Yes, but user wanted to try latest models

### ❌ Kimi-Linear-48B-A3B (Base & Instruct)
**Multiple blocking issues:**
1. **vLLM Nightly Bug**: `MLAModules.__init__()` missing argument - incomplete implementation
2. **ARM64 Incompatibility**: Required `fla-core` CUDA kernels fail to import on ARM64
3. **Multi-GPU Requirement**: Official guide recommends 4-8 GPUs, we have 1
4. **Docker Image Mismatch**: AMD64-only images fail on ARM64 with "exec format error"

**Conclusion:** Model designed for x86_64 multi-GPU data centers. Not compatible with ARM64 single-GPU systems.

### ❌ Qwen2.5-VL-7B-Instruct
- **Status:** Failed
- **Issue:** Triton kernel compilation error - `ptxas fatal: Value 'sm_121a' is not defined`
- **Root Cause:** NVIDIA GB10 GPU (CUDA capability 12.1) too new for current vLLM/Triton toolchain on ARM64

## Key Learnings

### Your System is Cutting-Edge but Limited
- ✅ **Hardware:** Powerful (120GB VRAM, modern GPU)
- ❌ **Software Support:** ARM64 + GB10 combination has poor ML tooling compatibility
- ✅ **What Works:** Qwen3-Coder-30B, Qwen2-VL-7B (proven models with mature support)

### Compatibility Checklist for Future Models
Before attempting a new model, verify:
1. ✅ **Architecture:** Is it supported in vLLM stable? (Not just nightly)
2. ✅ **System:** Does it work on ARM64? (`uname -m` returns aarch64)
3. ✅ **GPU:** Does the model's CUDA code compile for your GPU architecture?
4. ✅ **Hardware Requirements:** Single GPU vs. multi-GPU requirements

### What to Avoid
- ❌ Brand-new model architectures (wait 3-6 months for tooling maturity)
- ❌ Models requiring custom CUDA kernels (`fla-core`, etc.)
- ❌ Models officially recommending multi-GPU setups
- ❌ Pinning Docker image versions (use `:latest` for ARM64 multi-arch support)

## Working Models on Your System
- ✅ Qwen3-Coder-30B (Port 8100)
- ✅ Qwen2-VL-7B (Port 8101)
- ✅ Qwen3-VL-30B (Port 8102, if started)

## Recommendations
1. **Stick with proven models** (Qwen family works well on your system)
2. **Wait 6+ months** before trying bleeding-edge architectures
3. **Monitor vLLM releases** for ARM64 + GB10 support improvements
4. **Use cloud APIs** for experimental models instead of self-hosting

## Files Created
- `/home/dan/danProjects/dgx_spark/vllm-kimi-linear-48b/TROUBLESHOOTING.md` - Detailed analysis of Kimi-Linear issues
- `/home/dan/danProjects/dgx_spark/vllm-qwen2.5-vl-7b/` - Qwen2.5-VL attempt (failed)

---

**Bottom Line:** Your ARM64 + GB10 system is too new for bleeding-edge ML models. Stick with mature, well-supported models like the Qwen family until tooling catches up (6-12 months).
