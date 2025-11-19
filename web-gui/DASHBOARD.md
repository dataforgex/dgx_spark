# DGX Spark Dashboard

Real-time monitoring dashboard for your vLLM servers, GPU metrics, and system resources.

## Features

- **GPU Monitoring**: Real-time GPU utilization, memory usage, temperature, and power consumption
- **System Metrics**: CPU usage and system memory monitoring
- **vLLM Server Status**: Health checks for both model servers (Qwen3-Coder-30B and Qwen2-VL-7B)
- **Docker Containers**: Status of running vLLM containers
- **Auto-refresh**: Metrics update every 5 seconds
- **Dark Theme**: Consistent with the chat interface
- **Navigation**: Easy switching between Chat and Dashboard views

## Quick Start

### 1. Start the Metrics API Server

In a terminal, run:

```bash
cd web-gui
./start-metrics-api.sh
```

The API server will start on `http://localhost:5174` and provide:
- `/api/metrics` - GPU and system metrics
- `/api/models` - vLLM model server health status
- `/api/containers` - Docker container information

### 2. Start the Web GUI

In another terminal, run:

```bash
cd web-gui
npm run dev
```

The web interface will start on `http://localhost:5173`

### 3. Access the Dashboard

Open your browser to:
- **Dashboard**: http://localhost:5173/dashboard (default)
- **Chat**: http://localhost:5173/chat

## Dashboard Layout

### System Memory
- Doughnut chart showing used vs free memory
- Total system memory and CPU usage metrics

### GPU Utilization
- Line chart tracking GPU utilization over time (last 30 data points)
- Power consumption for each GPU

### GPU Temperature
- Line chart tracking temperature for each GPU
- Updates every 5 seconds

### vLLM Model Servers
- Health status for each model server
- Response time monitoring
- Port information

### Docker Containers
- Table showing all vLLM-related containers
- Status (Running/Stopped)
- Port mappings

## Architecture

### Frontend (React + TypeScript)
- `src/components/Dashboard.tsx` - Main dashboard component
- `src/components/Navigation.tsx` - Navigation header
- Chart.js + react-chartjs-2 for visualizations
- React Router for navigation

### Backend (Python + FastAPI)
- `metrics-api.py` - FastAPI server
- Collects GPU metrics via `nvidia-smi`
- Checks vLLM server health via HTTP requests
- Queries Docker container status via Docker CLI
- CORS enabled for localhost development

## API Endpoints

### GET /api/metrics
Returns system and GPU metrics:
```json
{
  "gpus": [
    {
      "index": 0,
      "name": "NVIDIA H100",
      "temperature": 45.0,
      "powerDraw": 350.5,
      "powerLimit": 700.0,
      "memoryUsed": 65536.0,
      "memoryTotal": 98304.0,
      "utilizationGpu": 85.0
    }
  ],
  "memoryUsed": 64.5,
  "memoryTotal": 128.0,
  "cpuUsage": 25.5,
  "timestamp": 1699564800000
}
```

### GET /api/models
Returns vLLM model server status:
```json
[
  {
    "name": "Qwen3-Coder-30B",
    "port": 8100,
    "healthy": true,
    "responseTime": 45
  },
  {
    "name": "Qwen2-VL-7B",
    "port": 8101,
    "healthy": true,
    "responseTime": 38
  }
]
```

### GET /api/containers
Returns Docker container information:
```json
[
  {
    "name": "vllm-qwen3-coder-30b",
    "status": "Up 2 hours",
    "ports": "0.0.0.0:8100->8000/tcp"
  }
]
```

## Troubleshooting

### "Connection Error" on Dashboard

1. Make sure the metrics API is running:
   ```bash
   cd web-gui
   ./start-metrics-api.sh
   ```

2. Check if the API is accessible:
   ```bash
   curl http://localhost:5174/health
   ```

### No GPU Data Showing

1. Verify `nvidia-smi` works:
   ```bash
   nvidia-smi
   ```

2. Check the API logs for errors

### Model Servers Show as Offline

1. Verify the vLLM servers are running:
   ```bash
   docker ps | grep vllm
   ```

2. Check if the health endpoints are accessible:
   ```bash
   curl http://localhost:8100/health
   curl http://localhost:8101/health
   ```

### Docker Container Information Not Showing

1. Verify Docker is accessible:
   ```bash
   docker ps
   ```

2. Make sure your user has Docker permissions or run the API with appropriate access

## Development

### Running in Development Mode

1. Install frontend dependencies:
   ```bash
   cd web-gui
   npm install
   ```

2. Install backend dependencies:
   ```bash
   cd web-gui
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Start both servers (in separate terminals):
   ```bash
   # Terminal 1: Backend API
   ./start-metrics-api.sh

   # Terminal 2: Frontend dev server
   npm run dev
   ```

### Building for Production

```bash
cd web-gui
npm run build
```

The production build will be in `web-gui/dist/`

## Tech Stack

### Frontend
- React 19
- TypeScript
- React Router 7
- Chart.js 4
- Vite

### Backend
- Python 3
- FastAPI
- uvicorn
- psutil
- requests

## Reference

This dashboard layout is inspired by [DanTup/dgx_dashboard](https://github.com/DanTup/dgx_dashboard), adapted for vLLM server monitoring with a dark theme.
