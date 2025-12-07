# Multi-stage build for web-gui application
# Stage 1: Build the frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the frontend
RUN npm run build

# Stage 2: Production image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python API
COPY metrics-api.py .

# Copy the built frontend from the builder stage
COPY --from=frontend-builder /app/dist /app/dist

# Install aiofiles for async file serving
RUN pip install --no-cache-dir aiofiles

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
