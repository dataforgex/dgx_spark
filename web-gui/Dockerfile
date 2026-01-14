# Multi-stage build for web-gui application
# Stage 1: Build the frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# Build-time environment variables for Vite (embedded in JS bundle)
ARG VITE_METRICS_API_PORT=5174
ARG VITE_MODEL_MANAGER_PORT=5175
ARG VITE_SANDBOX_PORT=5176
ARG VITE_SEARXNG_PORT=8080

# Pass to environment for Vite build
ENV VITE_METRICS_API_PORT=$VITE_METRICS_API_PORT
ENV VITE_MODEL_MANAGER_PORT=$VITE_MODEL_MANAGER_PORT
ENV VITE_SANDBOX_PORT=$VITE_SANDBOX_PORT
ENV VITE_SEARXNG_PORT=$VITE_SEARXNG_PORT

# Copy package files
COPY web-gui/package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY web-gui/ .

# Build the frontend (Vite will embed VITE_* env vars)
RUN npm run build

# Stage 2: Production image with NVIDIA tools for nvidia-smi
FROM nvidia/cuda:12.6.3-base-ubuntu24.04

WORKDIR /app

# Install Python, pip, and system dependencies including Docker CLI
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    ca-certificates \
    gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu noble stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements and install dependencies
COPY web-gui/requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Copy the shared module
COPY shared/ /app/shared/

# Copy the Python API
COPY web-gui/metrics-api.py .

# Copy the built frontend from the builder stage
COPY --from=frontend-builder /app/dist /app/dist

# Install aiofiles for async file serving
RUN pip install --no-cache-dir --break-system-packages aiofiles

# Create SPA-aware static file server
RUN echo 'import http.server\n\
import os\n\
\n\
class SPAHandler(http.server.SimpleHTTPRequestHandler):\n\
    def __init__(self, *args, **kwargs):\n\
        super().__init__(*args, directory="/app/dist", **kwargs)\n\
\n\
    def do_GET(self):\n\
        path = self.translate_path(self.path)\n\
        # If file exists, serve it; otherwise serve index.html for SPA routing\n\
        if os.path.exists(path) and not os.path.isdir(path):\n\
            return super().do_GET()\n\
        elif os.path.isdir(path) and os.path.exists(os.path.join(path, "index.html")):\n\
            return super().do_GET()\n\
        else:\n\
            self.path = "/index.html"\n\
            return super().do_GET()\n\
\n\
if __name__ == "__main__":\n\
    from http.server import HTTPServer\n\
    server = HTTPServer(("0.0.0.0", 5173), SPAHandler)\n\
    print("SPA server running on http://0.0.0.0:5173")\n\
    server.serve_forever()\n\
' > /app/spa_server.py

# Create a startup script that runs both the API and serves the frontend
RUN echo '#!/bin/bash\n\
set -e\n\
echo "🚀 Starting DGX Spark Dashboard"\n\
echo "================================"\n\
echo ""\n\
echo "🔧 Starting metrics API server on http://0.0.0.0:5174"\n\
python3 metrics-api.py &\n\
API_PID=$!\n\
echo "✅ Metrics API started (PID: $API_PID)"\n\
echo ""\n\
echo "🌐 Starting web interface on http://0.0.0.0:5173"\n\
python3 /app/spa_server.py &\n\
GUI_PID=$!\n\
echo ""\n\
echo "✨ Dashboard is ready!"\n\
echo "📊 Dashboard: http://localhost:5173"\n\
echo "🔧 API:       http://localhost:5174/api/metrics"\n\
echo ""\n\
# Wait for both processes\n\
wait -n\n\
# Exit with status of process that exited first\n\
exit $?\n\
' > /app/start.sh && chmod +x /app/start.sh

# Expose ports
EXPOSE 5173 5174

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5174/health || exit 1

# Start the application
CMD ["/app/start.sh"]
