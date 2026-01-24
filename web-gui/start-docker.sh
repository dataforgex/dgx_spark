#!/bin/bash
# Start the DGX Spark Web GUI container
# This script will build and start the container with automatic restart on reboot

set -e

echo "🚀 Starting DGX Spark Web GUI Container"
echo "========================================"
echo ""

# Change to the script's directory
cd "$(dirname "$0")"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    echo "Please install Docker first: https://docs.docker.com/engine/install/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed"
    echo "Please install Docker Compose first: https://docs.docker.com/compose/install/"
    exit 1
fi

# Determine which Docker Compose command to use
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="docker compose"
fi

# Check if nvidia-docker runtime is available (for GPU support)
# Use docker info instead of running a test container (avoids orphaned containers)
if ! nvidia-smi &> /dev/null; then
    echo "⚠️  Warning: NVIDIA drivers not found"
    echo "GPU metrics will not work."
    echo ""
elif ! docker info 2>/dev/null | grep -qi "runtimes.*nvidia"; then
    echo "⚠️  Warning: NVIDIA Docker runtime may not be configured"
    echo "GPU metrics may not work inside container."
    echo ""
else
    echo "✅ NVIDIA GPU support detected"
    echo ""
fi

# Check if image exists
IMAGE_EXISTS=$(docker images -q dgx-spark-web-gui 2>/dev/null)

# Stop and remove existing container if running
echo "🛑 Stopping existing container (if any)..."
$DOCKER_COMPOSE down 2>/dev/null || true
# Also remove any orphan container with same name (not started via compose)
docker rm -f dgx-spark-web-gui 2>/dev/null || true
echo ""

# Build only if image doesn't exist or --build/--rebuild flag is passed
if [ -z "$IMAGE_EXISTS" ] || [ "$1" = "--build" ] || [ "$1" = "--rebuild" ]; then
    if [ "$1" = "--rebuild" ]; then
        echo "🔨 Rebuilding Docker image from scratch (no cache)..."
        $DOCKER_COMPOSE build --no-cache
    else
        echo "🔨 Building Docker image..."
        $DOCKER_COMPOSE build
    fi
    echo ""
else
    echo "✓ Using existing Docker image (use '--build' to rebuild, '--rebuild' for fresh build)"
    echo ""
fi

# Start the container
echo "🚀 Starting container..."
$DOCKER_COMPOSE up -d
echo ""

# Wait for the container to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check if container is running
if docker ps | grep -q dgx-spark-web-gui; then
    echo "✅ Container is running!"
    echo ""
    echo "📊 Dashboard: http://localhost:5173"
    echo "💬 Chat:      http://localhost:5173/chat"
    echo "🔧 API:       http://localhost:5174/api/metrics"
    echo ""
    echo "📋 Container Info:"
    echo "   Name:    dgx-spark-web-gui"
    echo "   Restart: unless-stopped (will restart on reboot)"
    echo ""
    echo "💡 Useful commands:"
    echo "   View logs:        docker logs -f dgx-spark-web-gui"
    echo "   Stop container:   $DOCKER_COMPOSE down"
    echo "   Restart:          $DOCKER_COMPOSE restart"
    echo "   Rebuild:          $DOCKER_COMPOSE up -d --build"
else
    echo "❌ Container failed to start"
    echo "Check logs with: docker logs dgx-spark-web-gui"
    exit 1
fi
