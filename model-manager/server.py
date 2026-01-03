#!/usr/bin/env python3
"""
Model Manager API - FastAPI backend for managing LLM model containers
"""

import json
import os
import subprocess
import asyncio
import time
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Model Manager API", version="1.0.0")

# CORS for web-gui
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to models.json (check /app first for Docker, then parent directory)
MODELS_CONFIG_PATH = Path("/app/models.json") if Path("/app/models.json").exists() else Path(__file__).parent.parent / "models.json"

# Base directory for model script directories (for engine: "script" models)
# In Docker: set via MODELS_BASE_DIR env var (mounted at /app/models)
# Local: use parent directory of this script
MODELS_BASE_DIR = Path(os.environ.get("MODELS_BASE_DIR", str(Path(__file__).parent.parent)))

# When running in Docker, we need to use host paths for volume mounts
# The container mounts host's ~/.cache/huggingface to /root/.cache/huggingface
# So we write configs to /root/.cache/huggingface but mount using host path
HOST_HOME = os.environ.get("HOST_HOME", str(Path.home()))
HF_CACHE_DIR = Path("/root/.cache/huggingface") if Path("/app/models.json").exists() else Path.home() / ".cache" / "huggingface"
HOST_HF_CACHE_DIR = f"{HOST_HOME}/.cache/huggingface"

# Cache for model status (TTL in seconds)
CACHE_TTL = 3.0
_cache: dict = {"models": None, "timestamp": 0, "lock": asyncio.Lock()}


class ModelStatus(BaseModel):
    id: str
    name: str
    engine: str
    port: int
    status: str  # running, stopped, starting
    container_name: str
    memory_mb: Optional[int] = None


class SystemMemory(BaseModel):
    total_mb: int
    used_mb: int
    free_mb: int
    processes: list


def load_models_config() -> dict:
    """Load models configuration from JSON file."""
    if not MODELS_CONFIG_PATH.exists():
        raise HTTPException(status_code=500, detail=f"models.json not found at {MODELS_CONFIG_PATH}")

    with open(MODELS_CONFIG_PATH) as f:
        return json.load(f)


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
    try:
        returncode, stdout, _ = await async_run_command(
            ["ss", "-tlnp", f"sport = :{port}"],
            timeout=5.0
        )
        # ss returns lines with LISTEN if port is in use
        return "LISTEN" in stdout
    except Exception:
        return False


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
    """Build docker run command for vLLM models."""
    settings = model_config.get("settings", {})
    port = model_config["port"]
    container_name = model_config["container_name"]
    image = model_config["image"]
    model = model_config["model_id"]

    cmd = [
        "docker", "run", "-d",
        "--name", container_name,
        "--gpus", "all",
        "--ipc=host",
        "--ulimit", "memlock=-1",
        "--ulimit", "stack=67108864",
        "-p", f"{port}:8000",
        "-v", f"{HOST_HF_CACHE_DIR}:/root/.cache/huggingface",
        "--restart", "unless-stopped",
        image,
        "vllm", "serve", model,
        "--max-model-len", str(settings.get("max_model_len", 32768)),
        "--max-num-seqs", str(settings.get("max_num_seqs", 8)),
        "--gpu-memory-utilization", str(settings.get("gpu_memory_utilization", 0.3)),
        "--dtype", "auto",
    ]

    if settings.get("enable_prefix_caching"):
        cmd.append("--enable-prefix-caching")
    if settings.get("enable_chunked_prefill"):
        cmd.append("--enable-chunked-prefill")
    if settings.get("enable_auto_tool_choice"):
        cmd.extend(["--enable-auto-tool-choice", "--tool-call-parser", settings.get("tool_call_parser", "hermes")])

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

            # Script-based models check port instead of container
            if engine == "script":
                script_models_to_check.append((model_id, model_config))
                continue

            # Determine status from batch results (Docker-based models)
            if container_name in running_containers:
                status = "running"
                running_model_containers.append(container_name)
            elif container_name in all_containers:
                status = "stopped"
            else:
                status = "not_created"

            models.append(ModelStatus(
                id=model_id,
                name=model_config["name"],
                engine=engine,
                port=model_config["port"],
                status=status,
                container_name=container_name,
                memory_mb=None  # Memory fetched separately to avoid slow docker stats
            ))

        # Check script-based models by port
        for model_id, model_config in script_models_to_check:
            port = model_config["port"]
            status = await get_script_model_status(port)
            models.append(ModelStatus(
                id=model_id,
                name=model_config["name"],
                engine="script",
                port=port,
                status=status,
                container_name=model_config.get("script_dir", model_id),
                memory_mb=None
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
async def start_model(model_id: str) -> dict:
    """Start a model container."""
    config = load_models_config()

    if model_id not in config["models"]:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    model_config = config["models"][model_id]
    engine = model_config["engine"]

    # Invalidate cache since we're changing state
    invalidate_cache()

    # Script-based models use port check instead of container status
    if engine == "script":
        port = model_config["port"]
        if await check_port_in_use(port):
            return {"message": f"Model {model_id} is already running", "status": "running"}

        # Run serve.sh script
        try:
            returncode, stdout, stderr = await run_model_script(model_config, "serve.sh")
            if returncode != 0:
                raise HTTPException(status_code=500, detail=f"Failed to start model: {stderr}")
            return {
                "message": f"Model {model_id} started successfully",
                "status": "starting",
                "port": port
            }
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

        return {
            "message": f"Model {model_id} started successfully",
            "status": "starting",
            "container_id": stdout.strip()[:12]
        }
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

        return {"message": f"Model {model_id} stopped successfully", "status": "stopped"}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=500, detail="Command timed out")


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
async def get_system_memory() -> SystemMemory:
    """Get GPU memory usage (async)."""
    try:
        # Run both nvidia-smi commands in parallel
        mem_task = async_run_command(
            ["nvidia-smi", "--query-gpu=memory.total,memory.used,memory.free",
             "--format=csv,noheader,nounits"]
        )
        proc_task = async_run_command(
            ["nvidia-smi", "--query-compute-apps=pid,name,used_memory",
             "--format=csv,noheader,nounits"]
        )

        (mem_returncode, mem_stdout, _), (proc_returncode, proc_stdout, _) = await asyncio.gather(
            mem_task, proc_task
        )

        total, used, free = 0, 0, 0
        if mem_returncode == 0:
            parts = mem_stdout.strip().split(",")
            try:
                total = int(parts[0].strip())
                used = int(parts[1].strip())
                free = int(parts[2].strip())
            except (ValueError, IndexError):
                pass

        processes = []
        if proc_returncode == 0 and proc_stdout.strip():
            for line in proc_stdout.strip().split("\n"):
                parts = line.split(",")
                if len(parts) >= 3:
                    try:
                        mem = parts[2].strip()
                        # Handle N/A or other non-numeric values
                        mem_val = int(mem) if mem.isdigit() else 0
                        processes.append({
                            "pid": parts[0].strip(),
                            "name": parts[1].strip(),
                            "memory_mb": mem_val
                        })
                    except (ValueError, IndexError):
                        continue

        return SystemMemory(
            total_mb=total,
            used_mb=used,
            free_mb=free,
            processes=processes
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5175)
