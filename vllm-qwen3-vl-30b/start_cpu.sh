#!/bin/bash

# Start Qwen3-VL-30B server on CPU
# WARNING: CPU inference will be very slow (1-3 minutes per response)

set -e

PORT=8102
LOG_FILE="server_cpu.log"

echo "=================================================="
echo "Starting Qwen3-VL-30B Server (CPU Mode)"
echo "=================================================="
echo "⚠️  WARNING: CPU inference is SLOW!"
echo "   Expected response time: 1-3 minutes per request"
echo ""

# Check if already running
if lsof -ti:${PORT} > /dev/null 2>&1; then
    echo "❌ Port ${PORT} is already in use!"
    echo "   Stop the existing server first:"
    echo "   lsof -ti:${PORT} | xargs kill"
    exit 1
fi

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Please run: ./setup_transformers.sh"
    exit 1
fi

# Start server in background
echo "Starting server in background..."
source venv/bin/activate
nohup python3 serve_transformers.py --host 0.0.0.0 --port ${PORT} > ${LOG_FILE} 2>&1 &
SERVER_PID=$!

# Wait for startup
echo "Waiting for server to start..."
sleep 5

# Check if server is running
if ps -p ${SERVER_PID} > /dev/null 2>&1; then
    echo "✓ Server started successfully (PID: ${SERVER_PID})"
    echo ""
    echo "API endpoint: http://localhost:${PORT}"
    echo "OpenAI-compatible: http://localhost:${PORT}/v1"
    echo ""
    echo "Health check:"
    curl -s http://localhost:${PORT}/health | jq . 2>/dev/null || echo "  (waiting for health endpoint...)"
    echo ""
    echo "Useful commands:"
    echo "  View logs:     tail -f ${LOG_FILE}"
    echo "  Stop server:   lsof -ti:${PORT} | xargs kill"
    echo "  Test server:   curl http://localhost:${PORT}/v1/models"
    echo ""
    echo "Log file: ${LOG_FILE}"
else
    echo "✗ Server failed to start!"
    echo "Check logs: tail ${LOG_FILE}"
    exit 1
fi
