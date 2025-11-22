#!/usr/bin/env python3
"""
Metrics API Server for DGX Spark Dashboard

Provides real-time system metrics, GPU information, vLLM model status,
and Docker container information.
"""

import json
import subprocess
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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
        {"name": "Qwen3-Coder-30B", "port": 8100, "health_endpoint": "/health"},
        {"name": "Qwen2-VL-7B", "port": 8101, "health_endpoint": "/health"},
        {"name": "Qwen3-VL-30B", "port": 8102, "health_endpoint": "/health"},
        {"name": "Qwen3-32B (NGC)", "port": 8103, "health_endpoint": "/v1/health/ready"},
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
    """Perform web search using DuckDuckGo"""
    try:
        from ddgs import DDGS

        print(f"🔍 Search Request: '{request.query}'")

        results = []
        with DDGS() as ddgs:
            search_results = ddgs.text(
                request.query,
                max_results=request.max_results
            )

            # Convert generator to list to inspect
            search_results_list = list(search_results)
            print(f"🔍 Found {len(search_results_list)} raw results")

            for i, result in enumerate(search_results_list):
                url = result.get("href", "")
                snippet = result.get("body", "")

                # For the top 2 results, try to fetch more detailed content
                # This makes the search work for ANY topic, not just hardcoded ones
                if url and i < 2:
                    page_summary = fetch_page_summary(url)
                    if page_summary:
                        snippet = f"Page Content: {page_summary} ... {snippet}"

                results.append({
                    "title": result.get("title", ""),
                    "url": url,
                    "snippet": snippet,
                })

        return {
            "query": request.query,
            "results": results,
            "count": len(results)
        }
    except ImportError:
        # Fallback to simple HTTP search if duckduckgo_search not available
        try:
            response = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": request.query},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10
            )

            # Simple parsing (basic fallback)
            from html.parser import HTMLParser

            class SimpleSearchParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.results = []
                    self.current_result = {}
                    self.in_result = False
                    self.in_title = False
                    self.in_snippet = False

                def handle_starttag(self, tag, attrs):
                    attrs_dict = dict(attrs)
                    if tag == "div" and attrs_dict.get("class") == "result":
                        self.in_result = True
                        self.current_result = {}
                    elif self.in_result and tag == "a" and "href" in attrs_dict:
                        self.current_result["url"] = attrs_dict["href"]
                        self.in_title = True
                    elif self.in_result and tag == "a" and attrs_dict.get("class") == "result__snippet":
                        self.in_snippet = True

                def handle_data(self, data):
                    if self.in_title:
                        self.current_result["title"] = data.strip()
                    elif self.in_snippet:
                        self.current_result["snippet"] = data.strip()

                def handle_endtag(self, tag):
                    if tag == "a" and self.in_title:
                        self.in_title = False
                    elif tag == "a" and self.in_snippet:
                        self.in_snippet = False
                        if self.current_result:
                            self.results.append(self.current_result)
                            self.current_result = {}
                        self.in_result = False

            parser = SimpleSearchParser()
            parser.feed(response.text)

            return {
                "query": request.query,
                "results": parser.results[:request.max_results],
                "count": len(parser.results[:request.max_results])
            }
        except Exception as e:
            print(f"Fallback search error: {e}")
            return {
                "query": request.query,
                "results": [],
                "count": 0,
                "error": "Search temporarily unavailable"
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


if __name__ == "__main__":
    print("🚀 Starting DGX Spark Metrics API on http://localhost:5174")
    print("📊 Endpoints:")
    print("  - GET /api/metrics     - System and GPU metrics")
    print("  - GET /api/models      - vLLM model server status")
    print("  - GET /api/containers  - Docker container status")
    print("  - POST /api/search     - Web search (DuckDuckGo) with page scraping for time queries")
    print("  - GET /health          - Health check")
    uvicorn.run(app, host="0.0.0.0", port=5174)
