#!/bin/bash

# Tool Call Sandbox Server Startup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PORT="${PORT:-5176}"
SANDBOX_IMAGE="sandbox-executor:latest"

echo "=== Tool Call Sandbox Server ==="

# Check if sandbox image exists, build if not
if ! docker image inspect "$SANDBOX_IMAGE" &> /dev/null; then
    echo "Building sandbox Docker image..."
    docker build -t "$SANDBOX_IMAGE" sandbox/
    echo "Sandbox image built successfully."
else
    echo "Sandbox image already exists."
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate and install dependencies
source venv/bin/activate
pip install -q -r requirements.txt

# Load tools and show what's available
echo ""
echo "Loading tools..."
python3 -c "
from tool_loader import ToolLoader
loader = ToolLoader('tools')
tools = loader.load_all()
print(f'\\nLoaded {len(tools)} tools:')
for name, tool in tools.items():
    print(f'  - {name}: {tool.description[:60]}...')
"

echo ""
echo "Starting server on port $PORT..."
echo "API docs: http://localhost:$PORT/docs"
echo ""

# Run the server
TOOLS_DIR=tools PORT=$PORT python3 server.py
