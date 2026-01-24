#!/bin/bash
# Start all DGX Spark services
# Usage: ./start-all.sh [--stop]

set -e
cd "$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}✓${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

# Stop all services
stop_all() {
    echo "Stopping all services..."

    # Stop web-gui
    if docker ps -q -f name=dgx-spark-web-gui | grep -q .; then
        cd web-gui && docker compose down 2>/dev/null || true
        cd ..
        log_info "Web GUI stopped"
    fi

    # Stop model-manager
    if pgrep -f "model-manager/server.py" > /dev/null; then
        pkill -f "model-manager/server.py" || true
        log_info "Model Manager stopped"
    fi

    # Stop tool-sandbox
    if pgrep -f "tool-call-sandbox/server.py" > /dev/null; then
        pkill -f "tool-call-sandbox/server.py" || true
        log_info "Tool Sandbox stopped"
    fi

    # Stop searxng
    if docker ps -q -f name=searxng | grep -q .; then
        cd searxng-docker && docker compose down 2>/dev/null || true
        cd ..
        log_info "SearXNG stopped"
    fi

    echo "All services stopped."
    exit 0
}

# Handle --stop flag
if [[ "$1" == "--stop" ]]; then
    stop_all
fi

echo "=========================================="
echo "  DGX Spark - Starting All Services"
echo "=========================================="
echo ""

# 1. Start SearXNG (web search)
echo "Starting SearXNG..."
if docker ps -q -f name=searxng | grep -q .; then
    log_info "SearXNG already running (port 8080)"
else
    cd searxng-docker
    docker compose up -d 2>/dev/null
    cd ..
    log_info "SearXNG started (port 8080)"
fi

# 2. Start Model Manager
echo "Starting Model Manager..."
if curl -s http://localhost:5175/health > /dev/null 2>&1; then
    log_info "Model Manager already running (port 5175)"
else
    cd model-manager
    if [[ -d "venv" ]]; then
        source venv/bin/activate
    fi
    nohup python3 server.py > /tmp/model-manager.log 2>&1 &
    cd ..
    sleep 2
    if curl -s http://localhost:5175/health > /dev/null 2>&1; then
        log_info "Model Manager started (port 5175)"
    else
        log_error "Model Manager failed to start - check /tmp/model-manager.log"
    fi
fi

# 3. Start Tool Sandbox
echo "Starting Tool Sandbox..."
if curl -s http://localhost:5176/health > /dev/null 2>&1; then
    log_info "Tool Sandbox already running (port 5176)"
else
    cd tool-call-sandbox
    if [[ -d "venv" ]]; then
        source venv/bin/activate
    fi
    nohup python3 server.py > /tmp/tool-sandbox.log 2>&1 &
    cd ..
    sleep 2
    if curl -s http://localhost:5176/health > /dev/null 2>&1; then
        log_info "Tool Sandbox started (port 5176)"
    else
        log_error "Tool Sandbox failed to start - check /tmp/tool-sandbox.log"
    fi
fi

# 4. Start Web GUI
echo "Starting Web GUI..."
if docker ps -q -f name=dgx-spark-web-gui | grep -q .; then
    log_info "Web GUI already running (port 5173)"
else
    cd web-gui
    ./start-docker.sh > /tmp/web-gui.log 2>&1
    cd ..
    log_info "Web GUI started (port 5173)"
fi

echo ""
echo "=========================================="
echo "  All Services Started"
echo "=========================================="
echo ""
echo "  Dashboard: http://localhost:5173"
echo "  Chat:      http://localhost:5173/chat"
echo ""
echo "  Next: Start a model from the Dashboard"
echo ""
echo "  Stop all: ./start-all.sh --stop"
echo "=========================================="
