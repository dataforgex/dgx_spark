#!/bin/bash

# Model Manager API Server - Host Mode
# Runs directly on the host instead of in Docker
# This avoids Docker-in-Docker security and reliability issues

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
PORT=5175
VENV_DIR="${SCRIPT_DIR}/venv"

# Check if already running
if pgrep -f "uvicorn.*model-manager.*server:app" > /dev/null; then
    echo "Model Manager is already running!"
    echo "API: http://localhost:${PORT}"
    echo "To stop: pkill -f 'uvicorn.*server:app.*${PORT}'"
    exit 0
fi

# Create venv if it doesn't exist
if [ ! -d "${VENV_DIR}" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "${VENV_DIR}"
    "${VENV_DIR}/bin/pip" install -q -r "${SCRIPT_DIR}/requirements.txt"
fi

# Activate venv
source "${VENV_DIR}/bin/activate"

echo "=================================================="
echo "Starting Model Manager API (Host Mode)"
echo "=================================================="
echo "Port: ${PORT}"
echo "Config: ${PARENT_DIR}/models.yaml"
echo "Venv: ${VENV_DIR}"
echo "=================================================="

# Set environment variables
export MODELS_BASE_DIR="${PARENT_DIR}"
export HOST_HOME="${HOME}"
export HF_TOKEN="${HF_TOKEN:-}"

# Run uvicorn directly
cd "${SCRIPT_DIR}"
exec python3 -m uvicorn server:app --host 0.0.0.0 --port ${PORT}
