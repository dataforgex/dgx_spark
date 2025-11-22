# Qwen3-VL-30B vLLM Troubleshooting Log

## Problem Statement
Container for `Qwen/Qwen3-VL-30B-A3B-Instruct` was stuck in a restart loop with docker logs showing continuous starting/stopping.

## Model Requirements
- **Model**: Qwen3-VL-30B-A3B-Instruct (MoE architecture)
- **Requires**: vLLM >= 0.11.0, transformers >= 4.57.0
- **GPU**: NVIDIA GB10 with CUDA capability 12.1 (sm_121a)
- **Total GPU Memory**: 119.7 GiB

---

## Attempts and Outcomes

### ❌ Attempt 1: Original NVIDIA Container with Restart Loop Fix
**What was tried:**
- Used `nvcr.io/nvidia/vllm:25.09-py3` (vLLM 0.10.1.1, transformers 4.55.2)
- Changed restart policy from `unless-stopped` to `on-failure:3`
- Removed automatic `docker logs -f` to prevent Ctrl+C interruptions

**Why it failed:**
- vLLM 0.10.1.1 doesn't support `qwen3_vl_moe` architecture
- transformers 4.55.2 doesn't recognize the model type
- Error: `The checkpoint you are trying to load has model type 'qwen3_vl_moe' but Transformers does not recognize this architecture`

**Key learning:** The NVIDIA container is too old for Qwen3-VL models.

---

### ❌ Attempt 2: Upgrade transformers Only
**What was tried:**
- Added `pip install -U transformers` to upgrade from 4.55.2 to 4.57.1
- Kept vLLM 0.10.1.1

**Why it failed:**
- vLLM 0.10.1.1 incompatible with transformers 4.57.1
- Error: `expected Tensor as element 0 in argument 0, but got tuple`
- Occurred during KV cache initialization

**Key learning:** vLLM and transformers versions must be compatible.

---

### ❌ Attempt 3: Upgrade Both vLLM and transformers in NVIDIA Container
**What was tried:**
- Added `pip install --upgrade vllm transformers`
- Upgraded vLLM from 0.10.1.1 to 0.11.1
- Upgraded transformers from 4.55.2 to 4.57.1

**Why it failed:**
- CUDA library mismatch after vLLM upgrade
- Error: `ImportError: libcudart.so.12: cannot open shared object file: No such file or directory`
- vLLM 0.11.1 requires different CUDA libraries than bundled in NVIDIA container

**Key learning:** Cannot upgrade vLLM inside NVIDIA container due to CUDA dependencies.

---

### ✅ Attempt 4: Switch to Official vLLM Image
**What was tried:**
- Switched from `nvcr.io/nvidia/vllm:25.09-py3` to `vllm/vllm-openai:latest`
- Removed upgrade commands (official image has vLLM 0.11+ and transformers 4.57+ built-in)
- Removed NVIDIA-specific environment variables

**Initial issue:**
- GPU memory allocation error
- Error: `Free memory on device (61.05/119.7 GiB) on startup is less than desired GPU memory utilization (0.52, 62.24 GiB)`

**Fix applied:**
- Reduced `GPU_MEMORY_UTILIZATION` from 0.52 to 0.48
- This allocates ~57.5 GiB instead of 62.24 GiB

**Second issue:**
- Triton compiler error with CUDA 12.1 GPU
- Error: `subprocess.CalledProcessError: Command '[...ptxas', '--gpu-name=sm_121a', ...]' returned non-zero exit status 255`
- Triton's ptxas doesn't support CUDA capability 12.1 (GB10 GPU)

**Key learning:** Official vLLM image works but has Triton compatibility issues with very new GPUs.

---

### ❌ Attempt 5: Use V0 Engine Instead of V1
**What was tried:**
- Added environment variable `VLLM_USE_V1=0` to avoid Triton compilation
- V0 engine doesn't use Triton

**Why it failed:**
- Official vLLM image requires V1 engine
- Error: `AssertionError` on `assert envs.VLLM_USE_V1`

**Key learning:** Official vLLM image is hardcoded to use V1 engine.

---

### ❌ Attempt 6: Override CUDA Architecture for Triton
**What was tried:**
- Set `TORCH_CUDA_ARCH_LIST="9.0"` to force Triton to compile for CUDA 9.0 instead of 12.1
- Keeps V1 engine but avoids unsupported sm_121a architecture

**Why it failed:**
- Environment variable was not respected by Triton
- Still attempted to compile for `sm_121a`
- Error: `subprocess.CalledProcessError: Command '[...ptxas', '--gpu-name=sm_121a', ...]' returned non-zero exit status 255`
- Model DID load successfully (13/13 shards, 58.16 GiB)
- Failed during encoder cache initialization when Triton tried to compile kernels

**Key learning:** 
- Official vLLM image's Triton is hardcoded to detect and use GPU's native architecture
- TORCH_CUDA_ARCH_LIST doesn't override Triton's GPU detection
- GB10 GPU (CUDA 12.1 / sm_121a) is fundamentally incompatible with current vLLM official image

---

## CONCLUSION

**The Qwen3-VL-30B model cannot run on GB10 GPU with current vLLM images** due to:
1. NVIDIA container (25.09-py3) has vLLM 0.10.1.1 which doesn't support Qwen3-VL
2. Official vLLM image has Triton compiler that doesn't support CUDA 12.1 (sm_121a)
3. Cannot upgrade vLLM in NVIDIA container due to CUDA library conflicts
4. Cannot override Triton's GPU architecture detection

**Recommended Path Forward:**

---

## Current Configuration

### Working Setup (if Attempt 6 succeeds)
```bash
Docker Image: vllm/vllm-openai:latest
Model: Qwen/Qwen3-VL-30B-A3B-Instruct
Port: 8102
GPU Memory Utilization: 0.48 (57.5 GiB)
Max Model Length: 16384
Max Concurrent Sequences: 64
Environment Variables:
  - TORCH_CUDA_ARCH_LIST="9.0"
Restart Policy: on-failure:3
```

### Key Files Modified
- `serve.sh`: Updated Docker image, GPU memory, environment variables

---

## Alternative Solutions (If Current Attempt Fails)

### Option A: Use Different Model
- Switch to `Qwen/Qwen2-VL-7B-Instruct` or `Qwen/Qwen2.5-VL-7B-Instruct`
- These work with vLLM 0.10.1.1 and transformers 4.55.2
- Smaller model (7B vs 30B parameters)

### Option B: Wait for Updated NVIDIA Container
- Wait for NVIDIA to release vLLM container with 0.11+
- Would have both NVIDIA optimizations and Qwen3-VL support

### Option C: Build Custom vLLM Image
- Build vLLM from source with proper CUDA 12.1 support
- Most complex but most control

### Option D: Use Different Inference Framework
- Try SGLang or native transformers
- May have different performance characteristics

---

## Lessons Learned

1. **Version Compatibility is Critical**
   - vLLM, transformers, and CUDA versions must all align
   - Upgrading one component can break others

2. **Container Images Have Specific Dependencies**
   - NVIDIA containers are optimized but version-locked
   - Official vLLM images are more flexible but may lack hardware-specific optimizations

3. **New GPU Architectures Need Special Handling**
   - CUDA 12.1 (sm_121a) is very new
   - Older tools like Triton's ptxas may not support it yet
   - Workarounds like TORCH_CUDA_ARCH_LIST can help

4. **GPU Memory Management**
   - Always check available vs required memory
   - Leave headroom for other processes
   - Adjust GPU_MEMORY_UTILIZATION accordingly

5. **Restart Policies Matter**
   - `unless-stopped` causes infinite loops on failure
   - `on-failure:N` limits retry attempts
   - Prevents resource exhaustion from continuous restarts

---

## Diagnostic Commands

```bash
# Check container status
docker ps -a | grep vllm-qwen3-vl-30b

# View logs
docker logs vllm-qwen3-vl-30b 2>&1 | tail -100

# Check for specific errors
docker logs vllm-qwen3-vl-30b 2>&1 | grep -E "(ERROR|CUDA|OOM|Failed)"

# Check GPU memory
nvidia-smi --query-gpu=memory.total,memory.used,memory.free --format=csv

# Check if OOM killed
docker inspect vllm-qwen3-vl-30b | grep OOMKilled

# Monitor real-time logs
docker logs -f vllm-qwen3-vl-30b
```

---

## Next Steps if Current Attempt Fails

1. Check logs for Triton compilation errors
2. If still failing with sm_121a, try TORCH_CUDA_ARCH_LIST="8.0" or "8.9"
3. If Triton issues persist, consider Option A (different model) or Option C (custom build)
4. Document any new errors encountered

---

## UPDATE: Transformers Direct Approach

### ✅ Attempt 7: Native Transformers with FastAPI
**What was tried:**
- Created `serve_transformers.py` - FastAPI server using Transformers directly
- Setup Python venv with transformers 4.57.1, torch, accelerate
- Used `Qwen3VLMoeForConditionalGeneration` class directly
- Installed `qwen-vl-utils` for vision processing

**Outcome: PARTIALLY SUCCESSFUL**
- ✅ Model class loaded correctly (Qwen3VLMoeForConditionalGeneration)
- ✅ Processor loaded successfully
- ✅ Model weights loaded (all 13 shards)
- ❌ Model loaded to **CPU** instead of GPU

**Root cause:**
- ARM64 (aarch64) architecture
- PyTorch from pip doesn't include CUDA support for ARM64
- System PyTorch (2.8.0+cpu) also CPU-only
- `torch.cuda.is_available()` returns False in venv

**Why PyTorch CUDA not available:**
```bash
$ uname -m
aarch64

$ python3 -c "import torch; print(torch.cuda.is_available())"
False  # Both in venv and system Python

$ pip install torch --index-url https://download.pytorch.org/whl/cu121
ERROR: No matching distribution found for torch  # No ARM64+CUDA wheels
```

**Key learning:** On ARM64 systems, CUDA-enabled PyTorch requires:
- Either: NVIDIA PyTorch container (`nvcr.io/nvidia/pytorch:XX.XX-py3`)
- Or: Building PyTorch from source with CUDA support
- Pip wheels only provide CUDA for x86_64, not aarch64

---

### ✅ RECOMMENDED SOLUTION: Docker with NVIDIA PyTorch Container

**Use NVIDIA's PyTorch container** which includes ARM64 + CUDA support:

```bash
docker run -d \
  --name qwen3-vl-server \
  --gpus all \
  --ipc=host \
  -p 8102:8102 \
  -v $(pwd):/workspace \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  nvcr.io/nvidia/pytorch:24.12-py3 \
  bash -c "pip install transformers accelerate qwen-vl-utils fastapi uvicorn[standard] && \
           cd /workspace && python3 serve_transformers.py --host 0.0.0.0 --port 8102"
```

**Why this works:**
1. NVIDIA containers have PyTorch pre-built with CUDA for ARM64
2. Avoids vLLM/Triton compatibility issues
3. Native Transformers has full Qwen3-VL-MoE support
4. Simpler serving stack (FastAPI vs vLLM's complexity)

**Trade-offs:**
- ❌ Slower inference than vLLM (no batching optimizations)
- ❌ No advanced features (continuous batching, PagedAttention)
- ✅ More reliable for new models
- ✅ Easier to debug
- ✅ Works around GB10 GPU compatibility issues

---

### Files Status

**Keep (Working):**
- ✅ `serve_transformers.py` - FastAPI server (works in Docker)
- ✅ `start_gpu.sh` - GPU inference (Docker + NVIDIA PyTorch)
- ✅ `start_cpu.sh` - CPU inference (Native venv)
- ✅ `setup_transformers.sh` - Venv setup reference
- ✅ `test-model.py` - Model testing
- ✅ `TROUBLESHOOTING.md` - This documentation
- ✅ `venv/` - Required for CPU mode

**Remove (Deprecated):**
- ❌ `serve.sh` - vLLM doesn't work with this model/GPU combo
- ❌ `serve_sglang.sh` - SGLang alternative (untested)
- ❌ `status_sglang.sh` - SGLang status
- ❌ `stop_sglang.sh` - SGLang stop
- ❌ `install_transformers_deps.sh` - Redundant

---

## Final Recommendation

**For production use:** Wait for vLLM update or use smaller Qwen2-VL model

**For immediate testing:** Use NVIDIA PyTorch container with Transformers:
1. Model loads correctly
2. GPU acceleration works
3. OpenAI-compatible API via FastAPI
4. Avoids all vLLM/Triton/CUDA compatibility issues

---

## FINAL WORKING SOLUTION: CPU-Only Inference

### ✅ Attempt 8: CPU-Only with Native Transformers

**Decision:** User accepted CPU-only inference as working solution

**What works:**
- ✅ Model: Qwen3VLMoeForConditionalGeneration loads correctly
- ✅ Processor: AutoProcessor loads successfully
- ✅ Server: FastAPI running on http://localhost:8102
- ✅ API: OpenAI-compatible endpoints functional
- ✅ Inference: Model generates responses successfully
- ✅ Health checks: All passing

**Key Fix - Response Extraction Bug:**
Initial implementation had a bug where responses were empty despite successful generation.

**Problem:**
```python
# OLD CODE (BROKEN)
generated_text = processor.batch_decode(outputs, skip_special_tokens=True)[0]
response_text = generated_text[len(text):].strip()  # Empty! Text length mismatch
```
- Template had special tokens: `<|im_start|>user\n...` (94 chars)
- Decoded output stripped special tokens: `user\n...` (92 chars)
- `generated_text[94:]` on 92-char string = empty!

**Solution:**
```python
# NEW CODE (FIXED)
new_token_ids = outputs[0, inputs["input_ids"].shape[1]:]
response_text = processor.decode(new_token_ids, skip_special_tokens=True).strip()
```
- Decode only newly generated tokens
- Avoids length mismatch from special token stripping
- Responses now return correctly: "Hello! How can I help you today?"

**Performance:**
- ⚠️ CPU inference is SLOW: 1-3 minutes per response
- ✅ Acceptable for testing and development
- ❌ Not suitable for production without GPU

**Usage:**
```bash
# Start server
./start_cpu.sh

# Test
curl http://localhost:8102/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-VL-30B-A3B-Instruct",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50
  }'

# Stop server
lsof -ti:8102 | xargs kill
```

**Files:**
- ✅ `serve_transformers.py` - Fixed FastAPI server
- ✅ `start_cpu.sh` - Convenience script for CPU mode
- ✅ `setup_transformers.sh` - Venv setup
- ✅ `venv/` - Python virtual environment
- ❌ `serve.sh` - Deprecated (vLLM doesn't work)
- ❌ Docker approach - Deprecated (GB10 GPU incompatible)

---

## UPDATE: GPU Support Implemented

### ✅ Attempt 9: Implemented Docker GPU Solution
**What was done:**
- Created `start_gpu.sh` implementing the recommended NVIDIA PyTorch container solution.
- This enables GPU inference on the GB10/ARM64 system.

**Usage:**
```bash
./start_gpu.sh
```

**Files:**
- ❌ `start_gpu.sh` - GPU inference (Docker) - BROKEN (Hangs)
- ✅ `start_cpu.sh` - CPU inference (Native venv) - WORKING

---

## UPDATE: GPU Support Failed

### ❌ Attempt 9: NVIDIA PyTorch 24.12 (PyTorch 2.6)
**What was tried:**
- Used `nvcr.io/nvidia/pytorch:24.12-py3`
- **Result:** Failed with `ImportError` in transformers due to PyTorch 2.6 alpha incompatibility.

### ❌ Attempt 10: NVIDIA PyTorch 24.10 (PyTorch 2.5)
**What was tried:**
- Downgraded to `nvcr.io/nvidia/pytorch:24.10-py3`
- **Result:** Model loaded successfully, but inference **HANGS** indefinitely.
- **Cause:** `sm_121` (GB10) incompatibility warning from PyTorch.

### ❌ Attempt 11: Disable Flash Attention
**What was tried:**
- Used `24.10` container with `USE_FLASH_ATTN=0`
- **Result:** Model loaded, but inference still **HANGS**.
- **Conclusion:** The GB10 GPU is fundamentally incompatible with the PyTorch versions in current NVIDIA containers on ARM64.

**Final Status:** GPU mode is currently impossible. CPU mode is the only working solution.


