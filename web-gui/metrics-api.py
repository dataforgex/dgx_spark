#!/usr/bin/env python3
"""
Metrics API Server for DGX Spark Dashboard

Provides real-time system metrics, GPU information, vLLM model status,
and Docker container information.
"""

import json
import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import requests
import psutil

# Add parent directory to path for shared module
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.auth import add_auth_middleware

# Initialize CPU percent on startup to establish baseline
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize psutil CPU percent with a baseline reading"""
    psutil.cpu_percent(interval=None)
    yield

app = FastAPI(title="DGX Spark Metrics API", lifespan=lifespan)

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for network access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication and rate limiting (optional, enabled via DGX_API_KEY env var)
add_auth_middleware(app)


def get_gpu_process_memory() -> Dict[int, float]:
    """Get GPU memory usage by summing per-process memory (for GPUs that don't report total)"""
    try:
        # First try direct nvidia-smi
        cmd = [
            "nvidia-smi",
            "--query-compute-apps=gpu_uuid,used_memory",
            "--format=csv,noheader,nounits",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        total_memory = 0.0
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2:
                    try:
                        total_memory += float(parts[1])
                    except ValueError:
                        pass

        # If no processes found, try via docker with host PID namespace
        # This is needed when running inside a container
        if total_memory == 0.0:
            docker_cmd = [
                "docker", "run", "--rm", "--pid=host", "--gpus", "all",
                "nvidia/cuda:12.0.0-base-ubuntu20.04",
                "nvidia-smi", "--query-compute-apps=pid,used_memory",
                "--format=csv,noheader,nounits"
            ]
            result = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        parts = [p.strip() for p in line.split(",")]
                        if len(parts) >= 2:
                            try:
                                total_memory += float(parts[1])
                            except ValueError:
                                pass

        return {0: total_memory}  # Return dict keyed by GPU index
    except Exception as e:
        print(f"Error getting GPU process memory: {e}")
        return {}


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
        process_memory = None  # Lazy load only if needed

        for line in result.stdout.strip().split("\n"):
            if line:
                parts = [p.strip() for p in line.split(",")]
                gpu_index = int(parts[0])
                memory_used = safe_float(parts[5])
                memory_total = safe_float(parts[6], 0.0)

                # If memory reports N/A, try to get it from process list
                if memory_used == 0.0 and memory_total == 0.0:
                    if process_memory is None:
                        process_memory = get_gpu_process_memory()
                    memory_used = process_memory.get(gpu_index, 0.0)
                    # GB10 has 128GB unified memory, use that as total
                    if "GB10" in parts[1]:
                        memory_total = 128 * 1024  # 128 GB in MiB
                    else:
                        memory_total = 1.0  # Fallback

                gpus.append({
                    "index": gpu_index,
                    "name": parts[1],
                    "temperature": safe_float(parts[2]),
                    "powerDraw": safe_float(parts[3]),
                    "powerLimit": safe_float(parts[4], 999.0),  # Default high value for limit
                    "memoryUsed": memory_used,
                    "memoryTotal": memory_total,
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
        {"name": "Qwen3-Coder-30B", "port": 8100, "health_endpoint": "/health"},
        {"name": "Qwen2-VL-7B", "port": 8101, "health_endpoint": "/health"},
        {"name": "Qwen3-VL-30B", "port": 8102, "health_endpoint": "/health"},
        {"name": "Ministral-3-14B", "port": 8103, "health_endpoint": "/health"},
    ]

    results = []
    for model in models:
        try:
            start = time.time()
            response = requests.get(
                f"http://localhost:{model['port']}{model['health_endpoint']}",
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


class SearchRequest(BaseModel):
    query: str
    max_results: int = 5


@app.post("/api/search")
async def web_search(request: SearchRequest):
    """Perform web search using SearXNG"""
    # SearXNG endpoint - configurable via environment variable
    SEARXNG_URL = os.getenv('SEARXNG_URL', 'http://localhost:8080')

    try:
        print(f"🔍 Search Request: '{request.query}'")

        # Query SearXNG API
        response = requests.get(
            f"{SEARXNG_URL}/search",
            params={
                'q': request.query,
                'format': 'json',
                'pageno': 1
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        search_results_list = data.get('results', [])
        print(f"🔍 Found {len(search_results_list)} results from SearXNG")

        results = []
        for i, result in enumerate(search_results_list[:request.max_results]):
            url = result.get('url', '')
            snippet = result.get('content', '')

            # For the top 2 results, try to fetch more detailed content
            # This makes the search work for ANY topic, not just hardcoded ones
            if url and i < 2:
                page_summary = fetch_page_summary(url)
                if page_summary:
                    snippet = f"Page Content: {page_summary} ... {snippet}"

            results.append({
                'title': result.get('title', ''),
                'url': url,
                'snippet': snippet,
            })

        return {
            "query": request.query,
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        print(f"Error performing search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def fetch_page_summary(url: str) -> Optional[str]:
    """Fetch a webpage and extract a summary of its content"""
    try:
        from bs4 import BeautifulSoup

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        # Short timeout to keep search fast
        response = requests.get(url, headers=headers, timeout=3)

        if not response.ok:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        # Get text
        text = soup.get_text()

        # Break into lines and remove leading/trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = ' '.join(chunk for chunk in chunks if chunk)

        # Get meta description if available
        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if meta_desc:
            description = meta_desc.get("content", "")

        # Combine description and first part of text
        summary = f"{description} {text}"
        
        # Limit to reasonable length (e.g. 1000 chars) to avoid overwhelming context
        return summary[:1000]

    except Exception as e:
        print(f"Error fetching page summary for {url}: {e}")
        return None


@app.post("/api/chat/proxy/{port}")
async def proxy_chat(port: int, request: dict):
    """Proxy chat requests to model servers to avoid browser CORS issues"""
    target_url = f"http://127.0.0.1:{port}/v1/chat/completions"

    try:
        print(f"🔀 Proxying chat request to port {port} (payload size: {len(json.dumps(request))} bytes)")
        response = requests.post(
            target_url,
            json=request,
            headers={"Content-Type": "application/json"},
            timeout=300.0
        )
        print(f"🔀 Proxy response: {response.status_code}")
        return response.json()
    except requests.Timeout:
        print(f"🔀 Proxy timeout to port {port}")
        raise HTTPException(status_code=504, detail="Request to model server timed out")
    except Exception as e:
        print(f"🔀 Proxy error: {e}")
        raise HTTPException(status_code=502, detail=str(e))


if __name__ == "__main__":
    print("Starting DGX Spark Metrics API on http://localhost:5174")
    print("Endpoints:")
    print("  - GET /api/metrics     - System and GPU metrics")
    print("  - GET /api/models      - Model server status")
    print("  - GET /api/containers  - Docker container status")
    print("  - POST /api/search     - Web search (SearXNG)")
    print("  - POST /api/chat/proxy/{port} - Proxy chat to model")
    print("  - GET /health          - Health check")
    uvicorn.run(app, host="0.0.0.0", port=5174)
