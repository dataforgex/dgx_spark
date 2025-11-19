#!/bin/bash
# Start both the metrics API and the web GUI

echo "🚀 Starting DGX Spark Dashboard"
echo "================================"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    kill $API_PID $GUI_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
    echo ""
fi

# Check if Python venv exists
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
    echo ""
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt
echo ""

# Start the API server in the background
echo "🔧 Starting metrics API server on http://localhost:5174"
python3 metrics-api.py > /tmp/metrics-api.log 2>&1 &
API_PID=$!

# Wait for API to be ready
sleep 2
echo "✅ Metrics API started (PID: $API_PID)"
echo ""

# Start the web GUI
echo "🌐 Starting web interface on http://localhost:5173"
echo ""
npm run dev &
GUI_PID=$!

echo ""
echo "✨ Dashboard is ready!"
echo "📊 Dashboard: http://localhost:5173/dashboard"
echo "💬 Chat:      http://localhost:5173/chat"
echo "🔧 API:       http://localhost:5174/api/metrics"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for both processes
wait
