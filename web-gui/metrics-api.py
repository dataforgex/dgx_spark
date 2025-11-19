#!/usr/bin/env python3
"""
Metrics API Server for DGX Spark Dashboard

Provides real-time system metrics, GPU information, vLLM model status,
and Docker container information.
"""

import json
import subprocess
import time
from typing import List, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import requests
import psutil

app = FastAPI(title="DGX Spark Metrics API")

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for network access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize CPU percent on startup to establish baseline
@app.on_event("startup")
async def startup_event():
    """Initialize psutil CPU percent with a baseline reading"""
    psutil.cpu_percent(interval=None)


def get_gpu_metrics() -> List[Dict[str, Any]]:
    """Get GPU metrics using nvidia-smi"""
    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=index,name,temperature.gpu,power.draw,power.limit,memory.used,memory.total,utilization.gpu",
            "--format=csv,noheader,nounits",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        def safe_float(value: str, default: float = 0.0) -> float:
            """Convert string to float, handling N/A and [N/A] values"""
            value = value.strip()
            if value in ["N/A", "[N/A]", "", "Not Supported"]:
                return default
            try:
                return float(value)
            except ValueError:
                return default

        gpus = []
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = [p.strip() for p in line.split(",")]
                gpus.append({
                    "index": int(parts[0]),
                    "name": parts[1],
                    "temperature": safe_float(parts[2]),
                    "powerDraw": safe_float(parts[3]),
                    "powerLimit": safe_float(parts[4], 999.0),  # Default high value for limit
                    "memoryUsed": safe_float(parts[5]),
                    "memoryTotal": safe_float(parts[6], 1.0),  # Avoid division by zero
                    "utilizationGpu": safe_float(parts[7]),
                })
        return gpus
    except Exception as e:
        print(f"Error getting GPU metrics: {e}")
        return []


def get_system_metrics() -> Dict[str, Any]:
    """Get system memory and CPU metrics"""
    try:
        memory = psutil.virtual_memory()
        # Use interval=1 to get accurate CPU usage over 1 second
        # This measures total CPU usage across all cores
        cpu_percent = psutil.cpu_percent(interval=1, percpu=False)

        return {
            "memoryUsed": memory.used / (1024 ** 3),  # Convert to GB
            "memoryTotal": memory.total / (1024 ** 3),  # Convert to GB
            "cpuUsage": cpu_percent,
        }
    except Exception as e:
        print(f"Error getting system metrics: {e}")
        return {
            "memoryUsed": 0,
            "memoryTotal": 0,
            "cpuUsage": 0,
        }


@app.get("/api/metrics")
async def get_metrics():
    """Get all system and GPU metrics"""
    gpus = get_gpu_metrics()
    system = get_system_metrics()

    return {
        "gpus": gpus,
        "memoryUsed": system["memoryUsed"],
        "memoryTotal": system["memoryTotal"],
        "cpuUsage": system["cpuUsage"],
        "timestamp": int(time.time() * 1000),
    }


@app.get("/api/models")
async def get_model_status():
    """Check the health status of vLLM model servers"""
    models = [
        {"name": "Qwen3-Coder-30B", "port": 8100},
        {"name": "Qwen2-VL-7B", "port": 8101},
    ]

    results = []
    for model in models:
        try:
            start = time.time()
            response = requests.get(
                f"http://localhost:{model['port']}/health",
                timeout=2
            )
            response_time = int((time.time() - start) * 1000)

            results.append({
                "name": model["name"],
                "port": model["port"],
                "healthy": response.status_code == 200,
                "responseTime": response_time,
            })
        except Exception as e:
            print(f"Error checking {model['name']}: {e}")
            results.append({
                "name": model["name"],
                "port": model["port"],
                "healthy": False,
                "responseTime": None,
            })

    return results


@app.get("/api/containers")
async def get_docker_containers():
    """Get Docker container status"""
    try:
        cmd = [
            "docker", "ps", "-a",
            "--format", "{{.Names}}|{{.Status}}|{{.Ports}}",
            "--filter", "name=vllm"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        containers = []
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("|")
                if len(parts) >= 2:
                    containers.append({
                        "name": parts[0],
                        "status": parts[1],
                        "ports": parts[2] if len(parts) > 2 else "",
                    })

        return containers
    except Exception as e:
        print(f"Error getting Docker containers: {e}")
        return []


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    print("🚀 Starting DGX Spark Metrics API on http://localhost:5174")
    print("📊 Endpoints:")
    print("  - GET /api/metrics     - System and GPU metrics")
    print("  - GET /api/models      - vLLM model server status")
    print("  - GET /api/containers  - Docker container status")
    print("  - GET /health          - Health check")
    uvicorn.run(app, host="0.0.0.0", port=5174)
