#!/bin/bash
# Start the metrics API server

echo "🚀 Starting DGX Spark Metrics API..."
echo ""

# Check if Python venv exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Start the API server
echo ""
echo "Starting API server on http://localhost:5174"
echo "Press Ctrl+C to stop"
echo ""
python3 metrics-api.py
