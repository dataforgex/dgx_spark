#!/bin/bash

# Setup script for Transformers server using virtual environment

set -e  # Exit on error

VENV_DIR="venv"
PROJECT_DIR="/home/dan/danProjects/dgx_spark/vllm-qwen3-vl-30b"

cd "$PROJECT_DIR"

echo "=================================================="
echo "Setting up Transformers Server with Virtual Environment"
echo "=================================================="
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
echo "This may take a few minutes..."
echo ""

pip install \
  transformers>=4.57.0 \
  torch \
  torchvision \
  torchaudio \
  accelerate \
  fastapi \
  uvicorn[standard] \
  pillow \
  pydantic

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================================="
    echo "✓ Setup complete!"
    echo "=================================================="
    echo ""
    echo "To use the server:"
    echo "  1. Activate the virtual environment:"
    echo "     source venv/bin/activate"
    echo ""
    echo "  2. Start the server:"
    echo "     python3 serve_transformers.py"
    echo ""
    echo "  3. Or use the helper script:"
    echo "     ./start_transformers.sh"
    echo ""
else
    echo ""
    echo "❌ Failed to install dependencies"
    exit 1
fi
