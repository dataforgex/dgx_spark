#!/bin/bash

# Model Manager API Server (Local Mode)
# Runs directly on host - required for script-based models that use local venvs

PORT=5175
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Check if already running
if lsof -i:${PORT} >/dev/null 2>&1; then
    echo "Model Manager is already running on port ${PORT}"
    echo "To stop: pkill -f 'uvicorn.*server:app'"
    exit 0
fi

# Create venv if needed
if [ ! -d "${SCRIPT_DIR}/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "${SCRIPT_DIR}/venv"
fi

# Activate and install deps
source "${SCRIPT_DIR}/venv/bin/activate"
pip install -q -r "${SCRIPT_DIR}/requirements.txt"

echo "=================================================="
echo "Starting Model Manager API (Local Mode)"
echo "=================================================="
echo "Port: ${PORT}"
echo "=================================================="

# Run directly on host
cd "${SCRIPT_DIR}"
exec uvicorn server:app --host 0.0.0.0 --port ${PORT}
