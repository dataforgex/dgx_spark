#!/usr/bin/env python3
"""
Model Manager API - FastAPI backend for managing LLM model containers
"""

import json
import os
import subprocess
import asyncio
import time
import httpx
import yaml
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager

# Track models that are starting up
# Format: {model_id: {"start_time": float, "port": int, "timeout": int, "checks": int}}
_starting_models: dict = {}
_starting_lock = asyncio.Lock()

# Health check configuration
HEALTH_CHECK_INTERVAL = 5  # seconds between checks
DEFAULT_STARTUP_TIMEOUT = 600  # 10 minutes default
LARGE_MODEL_TIMEOUT = 900  # 15 minutes for 100B+ models

# Memory check configuration
MEMORY_WARNING_THRESHOLD_GB = 5  # Warn if less than 5GB headroom
MEMORY_BLOCK_THRESHOLD_GB = 2   # Block if less than 2GB would remain


async def health_check_loop():
    """Background task that polls health of starting models."""
    while True:
        await asyncio.sleep(HEALTH_CHECK_INTERVAL)

        async with _starting_lock:
            completed = []
            for model_id, info in _starting_models.items():
                elapsed = time.time() - info["start_time"]

                # Check timeout
                if elapsed > info["timeout"]:
                    print(f"[health] Model {model_id} startup timed out after {elapsed:.0f}s")
                    completed.append(model_id)
                    continue

                # Check health endpoint
                is_healthy = await check_model_health(info["port"])
                info["checks"] += 1

                if is_healthy:
                    print(f"[health] Model {model_id} is ready after {elapsed:.0f}s ({info['checks']} checks)")
                    completed.append(model_id)
                else:
                    if info["checks"] % 6 == 0:  # Log every 30s
                        print(f"[health] Model {model_id} still starting... {elapsed:.0f}s elapsed")

            # Remove completed models from tracking
            for model_id in completed:
                del _starting_models[model_id]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of background tasks."""
    # Start health check loop
    health_task = asyncio.create_task(health_check_loop())
    print("[startup] Health check background task started")
    yield
    # Cleanup on shutdown
    health_task.cancel()
    try:
        await health_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Model Manager API", version="1.0.0", lifespan=lifespan)

# CORS for web-gui
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base directory for model script directories (for engine: "script" models)
# In Docker: set via MODELS_BASE_DIR env var (mounted at /app/models)
# Local: use parent directory of this script
MODELS_BASE_DIR = Path(os.environ.get("MODELS_BASE_DIR", str(Path(__file__).parent.parent)))

# Config paths - prefer YAML over JSON for new format
MODELS_YAML_PATH = MODELS_BASE_DIR / "models.yaml"
MODELS_JSON_PATH = MODELS_BASE_DIR / "models.json"

# When running in Docker, we need to use host paths for volume mounts
# The container mounts host's ~/.cache/huggingface to /root/.cache/huggingface
# So we write configs to /root/.cache/huggingface but mount using host path
HOST_HOME = os.environ.get("HOST_HOME", str(Path.home()))
IN_DOCKER = os.environ.get("MODELS_BASE_DIR") is not None
HF_CACHE_DIR = Path("/root/.cache/huggingface") if IN_DOCKER else Path.home() / ".cache" / "huggingface"
HOST_HF_CACHE_DIR = f"{HOST_HOME}/.cache/huggingface"

# Cache for model status (TTL in seconds)
CACHE_TTL = 3.0
_cache: dict = {"models": None, "timestamp": 0, "lock": asyncio.Lock()}


class ModelStatus(BaseModel):
    id: str
    name: str
    engine: str
    port: int
    status: str  # running, stopped, starting, not_created
    container_name: str
    memory_mb: Optional[int] = None
    # Startup progress (only present when status="starting")
    startup_progress: Optional[dict] = None  # {elapsed_seconds, timeout_seconds, progress_percent}
    # From YAML config
    description: Optional[str] = None
    estimated_memory_gb: Optional[int] = None


class SystemMemory(BaseModel):
    total_mb: int
    used_mb: int
    free_mb: int
    processes: list


class UnifiedMemoryInfo(BaseModel):
    """Memory info for unified memory systems (DGX Spark, Jetson).

    On unified memory systems, CPU and GPU share the same memory pool.
    We track system memory as the total pool and GPU process memory separately.
    """
    total_gb: float
    available_gb: float
    used_gb: float
    gpu_used_gb: float  # Memory used by GPU processes specifically
    gpu_processes: list  # List of GPU processes with memory usage


class MemoryCheckResult(BaseModel):
    """Result of pre-start memory check."""
    can_start: bool
    available_gb: float
    required_gb: float
    remaining_gb: float
    warning: Optional[str] = None
    error: Optional[str] = None


async def get_unified_memory_info() -> UnifiedMemoryInfo:
    """Get memory info for unified memory systems (DGX Spark).

    Reads system memory from /proc/meminfo and GPU process memory from nvidia-smi.
    This approach works for systems where CPU and GPU share the same memory pool.
    """
    # Read system memory from /proc/meminfo
    total_kb = 0
    available_kb = 0
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    total_kb = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    available_kb = int(line.split()[1])
    except Exception as e:
        print(f"[memory] Error reading /proc/meminfo: {e}")

    total_gb = total_kb / 1024 / 1024
    available_gb = available_kb / 1024 / 1024
    used_gb = total_gb - available_gb

    # Get GPU process memory from nvidia-smi
    gpu_processes = []
    gpu_used_mb = 0
    try:
        returncode, stdout, _ = await async_run_command(
            ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory",
             "--format=csv,noheader,nounits"],
            timeout=5.0
        )
        if returncode == 0 and stdout.strip():
            for line in stdout.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    try:
                        mem_mb = int(parts[2]) if parts[2].isdigit() else 0
                        gpu_processes.append({
                            "pid": parts[0],
                            "name": parts[1],
                            "memory_mb": mem_mb
                        })
                        gpu_used_mb += mem_mb
                    except (ValueError, IndexError):
                        continue
    except Exception as e:
        print(f"[memory] Error querying nvidia-smi: {e}")

    return UnifiedMemoryInfo(
        total_gb=round(total_gb, 1),
        available_gb=round(available_gb, 1),
        used_gb=round(used_gb, 1),
        gpu_used_gb=round(gpu_used_mb / 1024, 1),
        gpu_processes=gpu_processes
    )


async def check_memory_for_model(model_config: dict) -> MemoryCheckResult:
    """Check if there's enough memory to start a model.

    Returns a MemoryCheckResult indicating whether the model can start,
    along with any warnings or errors.
    """
    estimated_gb = model_config.get("estimated_memory_gb")
    if not estimated_gb:
        # No estimate, allow with warning
        return MemoryCheckResult(
            can_start=True,
            available_gb=0,
            required_gb=0,
            remaining_gb=0,
            warning="No memory estimate for this model, proceeding without check"
        )

    memory_info = await get_unified_memory_info()
    available_gb = memory_info.available_gb
    remaining_gb = available_gb - estimated_gb

    # Check thresholds
    if remaining_gb < MEMORY_BLOCK_THRESHOLD_GB:
        return MemoryCheckResult(
            can_start=False,
            available_gb=available_gb,
            required_gb=estimated_gb,
            remaining_gb=remaining_gb,
            error=f"Insufficient memory: {available_gb:.1f}GB available, "
                  f"model needs ~{estimated_gb}GB, would leave only {remaining_gb:.1f}GB"
        )
    elif remaining_gb < MEMORY_WARNING_THRESHOLD_GB:
        return MemoryCheckResult(
            can_start=True,
            available_gb=available_gb,
            required_gb=estimated_gb,
            remaining_gb=remaining_gb,
            warning=f"Low memory: {available_gb:.1f}GB available, "
                    f"model needs ~{estimated_gb}GB, will leave {remaining_gb:.1f}GB"
        )
    else:
        return MemoryCheckResult(
            can_start=True,
            available_gb=available_gb,
            required_gb=estimated_gb,
            remaining_gb=remaining_gb
        )


# Cache for loaded config
_config_cache: dict = {"config": None, "mtime": 0}

# Supported engine types
SUPPORTED_ENGINES = {"vllm", "ollama", "script", "trtllm"}


def validate_config(config: dict, config_path: Path) -> list[str]:
    """Validate the loaded configuration.

    Returns a list of warning messages (non-fatal issues).
    Raises HTTPException for fatal errors.
    """
    warnings = []
    models = config.get("models", {})

    if not models:
        raise HTTPException(
            status_code=500,
            detail=f"No models defined in {config_path}"
        )

    # Track ports to detect duplicates
    ports_used = {}

    for model_id, model_config in models.items():
        # Required fields
        required = ["port", "model_id", "engine"]
        for field in required:
            if field not in model_config or model_config[field] is None:
                raise HTTPException(
                    status_code=500,
                    detail=f"Model '{model_id}' missing required field: {field}"
                )

        # Validate engine type
        engine = model_config["engine"]
        if engine not in SUPPORTED_ENGINES:
            raise HTTPException(
                status_code=500,
                detail=f"Model '{model_id}' has invalid engine '{engine}'. Must be one of: {SUPPORTED_ENGINES}"
            )

        # Validate port
        port = model_config["port"]
        if not isinstance(port, int) or port < 1 or port > 65535:
            raise HTTPException(
                status_code=500,
                detail=f"Model '{model_id}' has invalid port: {port}. Must be 1-65535"
            )

        # Check for duplicate ports
        if port in ports_used:
            raise HTTPException(
                status_code=500,
                detail=f"Duplicate port {port} used by models: '{ports_used[port]}' and '{model_id}'"
            )
        ports_used[port] = model_id

        # Validate script_dir for script-based models
        if engine == "script":
            script_dir = model_config.get("script_dir")
            if not script_dir:
                warnings.append(f"Model '{model_id}' (engine=script) has no script_dir")
            else:
                script_path = MODELS_BASE_DIR / script_dir
                if not script_path.exists():
                    warnings.append(f"Model '{model_id}' script_dir not found: {script_path}")
                else:
                    serve_script = script_path / "serve.sh"
                    if not serve_script.exists():
                        warnings.append(f"Model '{model_id}' missing serve.sh in {script_path}")

        # Warn about missing container_name for Docker-based models
        if engine in ("vllm", "ollama") and "container_name" not in model_config:
            warnings.append(f"Model '{model_id}' has no container_name, will use default")

    return warnings


def load_models_config() -> dict:
    """Load models configuration from YAML or JSON file.

    Prefers models.yaml (new format) over models.json (legacy).
    Normalizes YAML format to match the internal structure.
    """
    global _config_cache

    # Determine which config file to use
    if MODELS_YAML_PATH.exists():
        config_path = MODELS_YAML_PATH
        is_yaml = True
    elif MODELS_JSON_PATH.exists():
        config_path = MODELS_JSON_PATH
        is_yaml = False
    else:
        raise HTTPException(
            status_code=500,
            detail=f"No config file found. Expected {MODELS_YAML_PATH} or {MODELS_JSON_PATH}"
        )

    # Check if we need to reload (file changed)
    mtime = config_path.stat().st_mtime
    if _config_cache["config"] is not None and _config_cache["mtime"] == mtime:
        return _config_cache["config"]

    # Load config
    with open(config_path) as f:
        if is_yaml:
            raw_config = yaml.safe_load(f)
            config = normalize_yaml_config(raw_config)
        else:
            config = json.load(f)

    # Validate config (raises HTTPException on fatal errors)
    warnings = validate_config(config, config_path)

    # Log result
    format_type = "" if is_yaml else " (legacy JSON)"
    print(f"[config] Loaded {len(config['models'])} models from {config_path}{format_type}")
    for warning in warnings:
        print(f"[config] WARNING: {warning}")

    _config_cache["config"] = config
    _config_cache["mtime"] = mtime
    return config


def normalize_yaml_config(raw: dict) -> dict:
    """Normalize YAML config to internal format.

    YAML format has defaults and per-model settings.
    This merges them into the format expected by the rest of the code.
    """
    defaults = raw.get("defaults", {})
    models = {}

    for model_id, model_config in raw.get("models", {}).items():
        # Skip disabled models
        if not model_config.get("enabled", True):
            continue

        engine = model_config.get("engine", "vllm")
        engine_defaults = defaults.get(engine, {})

        # Build normalized model config
        normalized = {
            "name": model_config.get("name", model_id),
            "engine": engine,
            "port": model_config.get("port"),
            "container_name": model_config.get("container_name", f"{engine}-{model_id}"),
            "model_id": model_config.get("model_id"),
        }

        # Add optional fields
        if "script_dir" in model_config:
            normalized["script_dir"] = model_config["script_dir"]

        if "description" in model_config:
            normalized["description"] = model_config["description"]

        if "estimated_memory_gb" in model_config:
            normalized["estimated_memory_gb"] = model_config["estimated_memory_gb"]

        # Merge settings: defaults -> model settings
        if engine in ("vllm", "ollama"):
            normalized["image"] = model_config.get("image", engine_defaults.get("image"))

        # Merge settings
        model_settings = model_config.get("settings", {})
        merged_settings = {**engine_defaults, **model_settings}
        # Remove non-setting keys that were in defaults
        for key in ["image", "restart_policy"]:
            merged_settings.pop(key, None)

        if merged_settings:
            normalized["settings"] = merged_settings

        models[model_id] = normalized

    return {"models": models}


async def async_run_command(cmd: list[str], timeout: float = 10.0) -> tuple[int, str, str]:
    """Run a command asynchronously and return (returncode, stdout, stderr)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode, stdout.decode(), stderr.decode()
    except asyncio.TimeoutError:
        proc.kill()
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


async def get_container_status(container_name: str) -> str:
    """Check if a Docker container is running (async)."""
    try:
        returncode, stdout, _ = await async_run_command(
            ["docker", "ps", "-q", "-f", f"name=^{container_name}$"]
        )
        if stdout.strip():
            return "running"

        # Check if container exists but stopped
        returncode, stdout, _ = await async_run_command(
            ["docker", "ps", "-aq", "-f", f"name=^{container_name}$"]
        )
        if stdout.strip():
            return "stopped"

        return "not_created"
    except Exception:
        return "unknown"


async def get_container_memory(container_name: str) -> Optional[int]:
    """Get memory usage of a container in MB (async)."""
    try:
        returncode, stdout, _ = await async_run_command(
            ["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", container_name],
            timeout=5.0
        )
        if returncode == 0 and stdout.strip():
            # Parse memory like "33.5GiB / 125.6GiB"
            mem_str = stdout.strip().split("/")[0].strip()
            if "GiB" in mem_str:
                return int(float(mem_str.replace("GiB", "").strip()) * 1024)
            elif "MiB" in mem_str:
                return int(float(mem_str.replace("MiB", "").strip()))
        return None
    except Exception:
        return None


async def check_port_in_use(port: int) -> bool:
    """Check if a port is in use (for script-based models)."""
    import socket
    try:
        # Try to connect to the port - if successful, something is listening
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
    except Exception:
        return False


async def check_model_health(port: int) -> bool:
    """Check if a model's HTTP endpoint is healthy and ready to serve.

    Tries /health first (vLLM), then /v1/models as fallback.
    Returns True only if the model is fully loaded and ready.
    """
    async with httpx.AsyncClient(timeout=5.0) as client:
        # Try /health endpoint first (vLLM)
        try:
            response = await client.get(f"http://localhost:{port}/health")
            if response.status_code == 200:
                return True
        except Exception:
            pass

        # Try /v1/models as fallback (OpenAI-compatible)
        try:
            response = await client.get(f"http://localhost:{port}/v1/models")
            if response.status_code == 200:
                data = response.json()
                # Check if at least one model is loaded
                if data.get("data") and len(data["data"]) > 0:
                    return True
        except Exception:
            pass

        # Try Ollama-specific endpoint
        try:
            response = await client.get(f"http://localhost:{port}/api/tags")
            if response.status_code == 200:
                return True
        except Exception:
            pass

    return False


async def get_model_startup_info(model_id: str) -> Optional[dict]:
    """Get startup progress info for a model if it's currently starting."""
    async with _starting_lock:
        if model_id in _starting_models:
            info = _starting_models[model_id]
            elapsed = time.time() - info["start_time"]
            return {
                "elapsed_seconds": int(elapsed),
                "timeout_seconds": info["timeout"],
                "health_checks": info["checks"],
                "progress_percent": min(95, int((elapsed / info["timeout"]) * 100))
            }
    return None


async def register_starting_model(model_id: str, port: int, timeout: int = DEFAULT_STARTUP_TIMEOUT):
    """Register a model as starting up for health monitoring."""
    async with _starting_lock:
        _starting_models[model_id] = {
            "start_time": time.time(),
            "port": port,
            "timeout": timeout,
            "checks": 0
        }
    print(f"[health] Registered model {model_id} for health monitoring (port {port}, timeout {timeout}s)")


async def unregister_starting_model(model_id: str):
    """Remove a model from startup tracking."""
    async with _starting_lock:
        if model_id in _starting_models:
            del _starting_models[model_id]


async def get_script_model_status(port: int) -> str:
    """Get status of a script-based model by checking its port."""
    if await check_port_in_use(port):
        return "running"
    return "stopped"


async def get_all_container_statuses() -> dict[str, str]:
    """Get status of all containers in one batch (async)."""
    # Get all running containers
    _, running_output, _ = await async_run_command(
        ["docker", "ps", "--format", "{{.Names}}"]
    )
    running_containers = set(running_output.strip().split("\n")) if running_output.strip() else set()

    # Get all containers (including stopped)
    _, all_output, _ = await async_run_command(
        ["docker", "ps", "-a", "--format", "{{.Names}}"]
    )
    all_containers = set(all_output.strip().split("\n")) if all_output.strip() else set()

    return {"running": running_containers, "all": all_containers}


def build_vllm_command(model_id: str, model_config: dict) -> list:
    """Build docker run command for vLLM models.

    Supports all vLLM settings from models.yaml including:
    - Context length, concurrency, memory utilization
    - Swap space, dtype, KV cache settings
    - Tool calling, prefix caching, chunked prefill
    - Mistral-specific tokenizer settings
    """
    settings = model_config.get("settings", {})
    port = model_config["port"]
    container_name = model_config["container_name"]
    image = model_config.get("image", "nvcr.io/nvidia/vllm:25.11-py3")
    model = model_config["model_id"]

    # Docker run command
    cmd = [
        "docker", "run", "-d",
        "--name", container_name,
        "--gpus", settings.get("gpus", "all"),
        "--ipc=host",
        "--ulimit", f"memlock={settings.get('ulimit_memlock', -1)}",
        "--ulimit", f"stack={settings.get('ulimit_stack', 67108864)}",
        "-p", f"{port}:8000",
        "-v", f"{HOST_HF_CACHE_DIR}:/root/.cache/huggingface",
        "--restart", settings.get("restart_policy", "unless-stopped"),
        image,
        "vllm", "serve", model,
    ]

    # Core vLLM settings
    cmd.extend(["--max-model-len", str(settings.get("max_model_len", 32768))])
    cmd.extend(["--max-num-seqs", str(settings.get("max_num_seqs", 8))])
    cmd.extend(["--gpu-memory-utilization", str(settings.get("gpu_memory_utilization", 0.4))])
    cmd.extend(["--dtype", str(settings.get("dtype", "auto"))])

    # Swap space for KV cache overflow
    if "swap_space" in settings:
        cmd.extend(["--swap-space", str(settings["swap_space"])])

    # KV cache dtype
    if "kv_cache_dtype" in settings:
        cmd.extend(["--kv-cache-dtype", settings["kv_cache_dtype"]])

    # Performance features
    if settings.get("enable_prefix_caching"):
        cmd.append("--enable-prefix-caching")
    if settings.get("enable_chunked_prefill"):
        cmd.append("--enable-chunked-prefill")

    # Execution mode
    if settings.get("enforce_eager"):
        cmd.append("--enforce-eager")
    if settings.get("trust_remote_code"):
        cmd.append("--trust-remote-code")

    # Tool calling
    if settings.get("enable_auto_tool_choice"):
        cmd.append("--enable-auto-tool-choice")
        cmd.extend(["--tool-call-parser", settings.get("tool_call_parser", "hermes")])

    # Mistral-specific settings
    if settings.get("tokenizer_mode"):
        cmd.extend(["--tokenizer_mode", settings["tokenizer_mode"]])
    if settings.get("config_format"):
        cmd.extend(["--config_format", settings["config_format"]])

    # Tensor parallelism (for multi-GPU)
    if "tensor_parallel_size" in settings and settings["tensor_parallel_size"] > 1:
        cmd.extend(["--tensor-parallel-size", str(settings["tensor_parallel_size"])])

    return cmd


def build_ollama_command(model_id: str, model_config: dict) -> list:
    """Build docker run command for Ollama models."""
    port = model_config["port"]
    container_name = model_config["container_name"]
    image = model_config["image"]
    model = model_config["model_id"]

    ollama_dir = Path.home() / ".ollama"
    ollama_dir.mkdir(exist_ok=True)

    cmd = [
        "docker", "run", "-d",
        "--name", container_name,
        "--gpus", "all",
        "-p", f"{port}:11434",
        "-v", f"{ollama_dir}:/root/.ollama",
        "--restart", "unless-stopped",
        image
    ]

    return cmd, model  # Return model to pull after container starts


async def run_model_script(model_config: dict, script_name: str) -> tuple[int, str, str]:
    """Run a model's serve.sh or stop.sh script.

    This is a long-term solution for models with custom configurations.
    Each model directory contains its own serve.sh/stop.sh scripts.
    """
    script_dir = model_config.get("script_dir")
    if not script_dir:
        return -1, "", "No script_dir specified in model config"

    script_path = MODELS_BASE_DIR / script_dir / script_name
    if not script_path.exists():
        return -1, "", f"Script not found: {script_path}"

    # Run the script from its directory
    try:
        proc = await asyncio.create_subprocess_exec(
            "bash", str(script_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(script_path.parent)
        )
        # Don't wait for completion - serve.sh runs docker in detached mode
        # Give it a moment to start the container
        await asyncio.sleep(2)

        # Check if process is still running (script should exit quickly after docker run -d)
        if proc.returncode is None:
            # Script still running, that's fine for serve.sh with log following
            return 0, "Container starting", ""

        stdout, stderr = await proc.communicate()
        return proc.returncode, stdout.decode(), stderr.decode()
    except Exception as e:
        return -1, "", str(e)


@app.get("/api/models")
async def list_models() -> list[ModelStatus]:
    """List all models with their status (cached)."""
    global _cache

    now = time.time()

    # Check cache validity
    if _cache["models"] is not None and (now - _cache["timestamp"]) < CACHE_TTL:
        return _cache["models"]

    # Use lock to prevent multiple concurrent refreshes
    async with _cache["lock"]:
        # Double-check after acquiring lock
        if _cache["models"] is not None and (now - _cache["timestamp"]) < CACHE_TTL:
            return _cache["models"]

        config = load_models_config()

        # Batch fetch all container statuses in 2 docker calls instead of N*2
        container_statuses = await get_all_container_statuses()
        running_containers = container_statuses["running"]
        all_containers = container_statuses["all"]

        models = []
        running_model_containers = []
        script_models_to_check = []

        for model_id, model_config in config["models"].items():
            container_name = model_config.get("container_name", model_id)
            engine = model_config["engine"]
            port = model_config["port"]

            # Script-based models check port instead of container
            if engine == "script":
                script_models_to_check.append((model_id, model_config))
                continue

            # Check if this model is in the starting tracker
            startup_info = await get_model_startup_info(model_id)

            # Determine status from batch results (Docker-based models)
            if container_name in running_containers:
                # Container is running, but is it healthy?
                if startup_info:
                    # Still in startup tracking - check health
                    is_healthy = await check_model_health(port)
                    if is_healthy:
                        status = "running"
                        await unregister_starting_model(model_id)
                        startup_info = None
                    else:
                        status = "starting"
                else:
                    # Not in startup tracking, assume healthy
                    status = "running"
                running_model_containers.append(container_name)
            elif container_name in all_containers:
                status = "stopped"
                # Clear any stale startup tracking
                await unregister_starting_model(model_id)
                startup_info = None
            else:
                status = "not_created"
                startup_info = None

            models.append(ModelStatus(
                id=model_id,
                name=model_config["name"],
                engine=engine,
                port=port,
                status=status,
                container_name=container_name,
                memory_mb=None,  # Memory fetched separately to avoid slow docker stats
                startup_progress=startup_info,
                description=model_config.get("description"),
                estimated_memory_gb=model_config.get("estimated_memory_gb")
            ))

        # Check script-based models by port
        for model_id, model_config in script_models_to_check:
            port = model_config["port"]
            startup_info = await get_model_startup_info(model_id)

            # Check if port is in use
            port_in_use = await check_port_in_use(port)

            if port_in_use:
                # Port is listening, check if healthy
                if startup_info:
                    is_healthy = await check_model_health(port)
                    if is_healthy:
                        status = "running"
                        await unregister_starting_model(model_id)
                        startup_info = None
                    else:
                        status = "starting"
                else:
                    status = "running"
            else:
                status = "stopped"
                await unregister_starting_model(model_id)
                startup_info = None

            models.append(ModelStatus(
                id=model_id,
                name=model_config["name"],
                engine="script",
                port=port,
                status=status,
                container_name=model_config.get("script_dir", model_id),
                memory_mb=None,
                startup_progress=startup_info,
                description=model_config.get("description"),
                estimated_memory_gb=model_config.get("estimated_memory_gb")
            ))

        # Fetch memory for running containers in parallel (if any)
        if running_model_containers:
            memory_tasks = [get_container_memory(name) for name in running_model_containers]
            memories = await asyncio.gather(*memory_tasks)
            memory_map = dict(zip(running_model_containers, memories))

            # Update models with memory info
            for model in models:
                if model.container_name in memory_map:
                    model.memory_mb = memory_map[model.container_name]

        # Update cache
        _cache["models"] = models
        _cache["timestamp"] = time.time()

        return models


@app.get("/api/models/{model_id}")
async def get_model(model_id: str) -> ModelStatus:
    """Get status of a specific model."""
    config = load_models_config()

    if model_id not in config["models"]:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    model_config = config["models"][model_id]
    container_name = model_config["container_name"]
    status = await get_container_status(container_name)
    memory = await get_container_memory(container_name) if status == "running" else None

    return ModelStatus(
        id=model_id,
        name=model_config["name"],
        engine=model_config["engine"],
        port=model_config["port"],
        status=status,
        container_name=container_name,
        memory_mb=memory
    )


def invalidate_cache():
    """Invalidate the model status cache."""
    global _cache
    _cache["models"] = None
    _cache["timestamp"] = 0


@app.post("/api/models/{model_id}/start")
async def start_model(model_id: str, force: bool = False) -> dict:
    """Start a model container.

    Args:
        model_id: The model to start
        force: If True, skip memory check and start anyway
    """
    config = load_models_config()

    if model_id not in config["models"]:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    model_config = config["models"][model_id]
    engine = model_config["engine"]

    # Check memory availability before starting (unless forced)
    memory_check = await check_memory_for_model(model_config)
    if not force and not memory_check.can_start:
        raise HTTPException(
            status_code=409,  # Conflict - resource constraint
            detail={
                "error": memory_check.error,
                "available_gb": memory_check.available_gb,
                "required_gb": memory_check.required_gb,
                "hint": "Use force=true to start anyway"
            }
        )

    # Invalidate cache since we're changing state
    invalidate_cache()

    # Determine startup timeout based on model size/name
    # Large models (100B+) need more time
    startup_timeout = DEFAULT_STARTUP_TIMEOUT
    model_name = model_config.get("name", "").lower()
    if "235b" in model_name or "100b" in model_name or "70b" in model_name:
        startup_timeout = LARGE_MODEL_TIMEOUT

    # Script-based models use port check instead of container status
    if engine == "script":
        port = model_config["port"]
        if await check_port_in_use(port):
            # Check if it's actually healthy
            if await check_model_health(port):
                return {"message": f"Model {model_id} is already running", "status": "running"}
            # Port in use but not healthy - might be starting
            startup_info = await get_model_startup_info(model_id)
            if startup_info:
                return {
                    "message": f"Model {model_id} is already starting",
                    "status": "starting",
                    "startup_progress": startup_info
                }

        # Run serve.sh script
        try:
            returncode, stdout, stderr = await run_model_script(model_config, "serve.sh")
            if returncode != 0:
                raise HTTPException(status_code=500, detail=f"Failed to start model: {stderr}")

            # Register for health monitoring
            await register_starting_model(model_id, port, startup_timeout)

            response = {
                "message": f"Model {model_id} starting (health checks every {HEALTH_CHECK_INTERVAL}s)",
                "status": "starting",
                "port": port,
                "timeout_seconds": startup_timeout
            }
            if memory_check.warning:
                response["memory_warning"] = memory_check.warning
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Docker-based models
    container_name = model_config["container_name"]
    # Check if already running (async)
    status = await get_container_status(container_name)
    if status == "running":
        return {"message": f"Model {model_id} is already running", "status": "running"}

    # Remove stopped container if exists
    if status == "stopped":
        await async_run_command(["docker", "rm", container_name])

    # Build and run command based on engine type
    try:
        if engine == "vllm":
            cmd = build_vllm_command(model_id, model_config)
            returncode, stdout, stderr = await async_run_command(cmd, timeout=30.0)
        elif engine == "trtllm":
            # TRT-LLM models use local serve.sh scripts for full configuration control
            returncode, stdout, stderr = await run_model_script(model_config, "serve.sh")
        elif engine == "ollama":
            cmd, model_to_pull = build_ollama_command(model_id, model_config)
            returncode, stdout, stderr = await async_run_command(cmd, timeout=30.0)
            if returncode == 0:
                # Pull the model after container starts
                await asyncio.sleep(2)
                await async_run_command(
                    ["docker", "exec", container_name, "ollama", "pull", model_to_pull],
                    timeout=600.0
                )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown engine: {engine}")

        if returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start container: {stderr}"
            )

        # Register for health monitoring
        port = model_config["port"]
        await register_starting_model(model_id, port, startup_timeout)

        response = {
            "message": f"Model {model_id} starting (health checks every {HEALTH_CHECK_INTERVAL}s)",
            "status": "starting",
            "container_id": stdout.strip()[:12] if stdout else "",
            "timeout_seconds": startup_timeout
        }
        if memory_check.warning:
            response["memory_warning"] = memory_check.warning
        return response
    except asyncio.TimeoutError:
        raise HTTPException(status_code=500, detail="Command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/models/{model_id}/stop")
async def stop_model(model_id: str) -> dict:
    """Stop a model container or script-based process."""
    config = load_models_config()

    if model_id not in config["models"]:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    model_config = config["models"][model_id]
    engine = model_config["engine"]

    # Invalidate cache since we're changing state
    invalidate_cache()

    # Script-based models use stop.sh
    if engine == "script":
        port = model_config["port"]
        if not await check_port_in_use(port):
            return {"message": f"Model {model_id} is not running", "status": "stopped"}

        try:
            returncode, stdout, stderr = await run_model_script(model_config, "stop.sh")
            # Give it a moment to stop
            await asyncio.sleep(1)
            return {"message": f"Model {model_id} stopped successfully", "status": "stopped"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Docker-based models
    container_name = model_config["container_name"]
    status = await get_container_status(container_name)
    if status != "running":
        return {"message": f"Model {model_id} is not running", "status": status}

    try:
        returncode, _, stderr = await async_run_command(
            ["docker", "stop", container_name],
            timeout=30.0
        )

        if returncode != 0:
            raise HTTPException(status_code=500, detail=f"Failed to stop container: {stderr}")

        # Remove the stopped container
        await async_run_command(["docker", "rm", container_name])

        # Unregister from health monitoring
        await unregister_starting_model(model_id)

        return {"message": f"Model {model_id} stopped successfully", "status": "stopped"}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=500, detail="Command timed out")


@app.get("/api/models/{model_id}/health")
async def check_model_health_endpoint(model_id: str) -> dict:
    """Check if a model is healthy and ready to serve requests."""
    config = load_models_config()

    if model_id not in config["models"]:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    model_config = config["models"][model_id]
    port = model_config["port"]

    # Check if healthy
    is_healthy = await check_model_health(port)

    # Get startup info if available
    startup_info = await get_model_startup_info(model_id)

    if is_healthy:
        return {
            "model_id": model_id,
            "healthy": True,
            "status": "running",
            "port": port
        }
    elif startup_info:
        return {
            "model_id": model_id,
            "healthy": False,
            "status": "starting",
            "port": port,
            "startup_progress": startup_info
        }
    else:
        # Check if container/port is even up
        port_in_use = await check_port_in_use(port)
        return {
            "model_id": model_id,
            "healthy": False,
            "status": "starting" if port_in_use else "stopped",
            "port": port
        }


@app.get("/api/models/{model_id}/logs")
async def get_model_logs(model_id: str, lines: int = 100) -> dict:
    """Get container logs for a model."""
    config = load_models_config()

    if model_id not in config["models"]:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    model_config = config["models"][model_id]
    container_name = model_config["container_name"]

    try:
        returncode, stdout, stderr = await async_run_command(
            ["docker", "logs", "--tail", str(lines), container_name],
            timeout=10.0
        )

        return {
            "logs": stdout + stderr,
            "container_name": container_name
        }
    except asyncio.TimeoutError:
        raise HTTPException(status_code=500, detail="Command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/memory")
async def get_system_memory() -> dict:
    """Get memory usage for unified memory systems (DGX Spark).

    Returns both unified memory info and GPU process memory.
    For systems with discrete GPUs, this falls back to nvidia-smi queries.
    """
    try:
        # Get unified memory info (works for DGX Spark)
        unified = await get_unified_memory_info()

        # Try nvidia-smi query for discrete GPU memory (may return N/A on unified systems)
        mem_returncode, mem_stdout, _ = await async_run_command(
            ["nvidia-smi", "--query-gpu=memory.total,memory.used,memory.free",
             "--format=csv,noheader,nounits"]
        )

        discrete_gpu_memory = None
        if mem_returncode == 0 and "[N/A]" not in mem_stdout:
            parts = mem_stdout.strip().split(",")
            try:
                discrete_gpu_memory = {
                    "total_mb": int(parts[0].strip()),
                    "used_mb": int(parts[1].strip()),
                    "free_mb": int(parts[2].strip())
                }
            except (ValueError, IndexError):
                pass

        return {
            # Unified memory (system-wide, works on DGX Spark)
            "unified": {
                "total_gb": unified.total_gb,
                "available_gb": unified.available_gb,
                "used_gb": unified.used_gb,
                "gpu_used_gb": unified.gpu_used_gb
            },
            # GPU processes
            "gpu_processes": unified.gpu_processes,
            # Discrete GPU memory (None on unified memory systems)
            "discrete_gpu": discrete_gpu_memory,
            # Is this a unified memory system?
            "is_unified": discrete_gpu_memory is None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models/{model_id}/memory-check")
async def check_model_memory(model_id: str) -> MemoryCheckResult:
    """Check if there's enough memory to start a model.

    Returns memory check result with can_start flag and any warnings/errors.
    """
    config = load_models_config()

    if model_id not in config["models"]:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    model_config = config["models"][model_id]
    return await check_memory_for_model(model_config)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5175)
