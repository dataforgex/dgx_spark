#!/bin/bash

# Model Manager API Server
# Provides REST API to start/stop/manage LLM model containers

CONTAINER_NAME="model-manager"
PORT=5175
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# Check if container already exists
if [ "$(docker ps -aq -f name=^${CONTAINER_NAME}$)" ]; then
    echo "Container '${CONTAINER_NAME}' already exists."
    if [ "$(docker ps -q -f name=^${CONTAINER_NAME}$)" ]; then
        echo "Container is already running!"
        echo ""
        echo "API: http://localhost:${PORT}"
        echo "Docs: http://localhost:${PORT}/docs"
        echo ""
        echo "To view logs: docker logs -f ${CONTAINER_NAME}"
        echo "To stop: docker stop ${CONTAINER_NAME}"
        exit 0
    else
        echo "Removing stopped container..."
        docker rm ${CONTAINER_NAME}
    fi
fi

# Build image if needed
echo "Building model-manager image..."
docker build -t model-manager:latest "${SCRIPT_DIR}"

echo "=================================================="
echo "Starting Model Manager API"
echo "=================================================="
echo "Container: ${CONTAINER_NAME}"
echo "Port: ${PORT}"
echo "=================================================="

# Run container with access to Docker socket and models.yaml
# Using host network to avoid IPv6 resolution issues
# Mount parent dir for script-based models (engine: "script")
docker run -d \
    --name ${CONTAINER_NAME} \
    --network host \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "${PARENT_DIR}:/app/models:ro" \
    -v "${HOME}/.cache/huggingface:/root/.cache/huggingface" \
    -e HOST_HOME="${HOME}" \
    -e HF_TOKEN="${HF_TOKEN}" \
    -e MODELS_BASE_DIR="/app/models" \
    --restart unless-stopped \
    model-manager:latest

if [ $? -eq 0 ]; then
    echo ""
    echo "Model Manager started successfully!"
    echo ""
    echo "API: http://localhost:${PORT}"
    echo "Docs: http://localhost:${PORT}/docs"
    echo ""
    echo "Commands:"
    echo "  Logs:   docker logs -f ${CONTAINER_NAME}"
    echo "  Stop:   docker stop ${CONTAINER_NAME}"
    echo "  Remove: docker rm ${CONTAINER_NAME}"
    echo ""
    docker logs -f ${CONTAINER_NAME}
else
    echo "Failed to start container"
    exit 1
fi
