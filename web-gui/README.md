# DGX Spark Web GUI

A modern, responsive web-based interface for the DGX Spark multi-model LLM system. It provides a unified dashboard for monitoring system metrics and an interactive chat interface with web search capabilities.

## Features

### 💬 Chat Interface
- **Multi-Model Support**: Switch seamlessly between Qwen3-Coder (Text/Code), Qwen2-VL (Vision), and Qwen3-VL (Advanced Vision).
- **Web Search**: Real-time internet access using DuckDuckGo with intelligent page scraping for up-to-date answers.
- **History**: Persistent conversation history stored locally.
- **Rich UI**: Markdown support, code highlighting, and responsive design.

### 📊 System Dashboard
- **GPU Monitoring**: Real-time tracking of GPU temperature, power usage, and memory utilization.
- **System Stats**: CPU and RAM usage monitoring.
- **Service Status**: Health checks for all vLLM model servers.
- **Container Status**: Live status of Docker containers.

## Quick Start

The easiest way to start the entire web stack (Frontend + Backend API) is using the helper script:

```bash
./start-all.sh
```

This will:
1. Install Node.js dependencies (if missing).
2. Create a Python virtual environment and install backend dependencies (if missing).
3. Start the Metrics/Search API on port **5174**.
4. Start the Web UI on port **5173**.

Access the interface at: **http://localhost:5173**

## Architecture

The project consists of two main components:

### 1. Frontend (React + Vite)
- **Port**: 5173
- **Tech Stack**: React, TypeScript, Vite, Chart.js
- **Key Files**:
  - `src/components/Chat.tsx`: Main chat logic and UI.
  - `src/components/Dashboard.tsx`: System monitoring dashboard.
  - `src/api.ts`: Client for communicating with LLMs and the backend API.

### 2. Backend API (Python FastAPI)
- **Port**: 5174
- **Tech Stack**: FastAPI, Uvicorn, DuckDuckGo Search (`ddgs`), BeautifulSoup4
- **Key File**: `metrics-api.py`
- **Responsibilities**:
  - Proxying system metrics (GPU/CPU/RAM).
  - Performing web searches and scraping page content for the LLM.
  - Checking health status of vLLM endpoints.

## Configuration

### Model Endpoints
The application is configured to talk to local vLLM servers on specific ports:

| Model | Port | Endpoint |
|-------|------|----------|
| **Qwen3-Coder-30B** | 8100 | `http://localhost:8100/v1/chat/completions` |
| **Qwen2-VL-7B** | 8101 | `http://localhost:8101/v1/chat/completions` |
| **Qwen3-VL-30B** | 8102 | `http://localhost:8102/v1/chat/completions` |

These can be modified in `src/api.ts`.

### Web Search
The web search feature is documented in detail in [SEARCH_DOCUMENTATION.md](./SEARCH_DOCUMENTATION.md).

## Manual Installation

If you prefer to run components manually:

### 1. Backend API
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 metrics-api.py
```

### 2. Frontend
```bash
npm install
npm run dev
```

## License

MIT
