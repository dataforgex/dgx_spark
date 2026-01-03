#!/bin/bash

CONTAINER_NAME="trtllm-nemotron-3-nano-30b-fp8"

# Check if container exists (stopped)
if [ "$(docker ps -aq -f name=^${CONTAINER_NAME}$)" ]; then
    if [ "$(docker ps -q -f name=^${CONTAINER_NAME}$)" ]; then
        echo "Container is already running!"
        echo "View logs: docker logs -f ${CONTAINER_NAME}"
    else
        echo "Restarting ${CONTAINER_NAME}..."
        docker start ${CONTAINER_NAME}
        echo "Container restarted! (Fast - engine already compiled)"
        echo ""
        docker logs -f ${CONTAINER_NAME}
    fi
else
    echo "Container doesn't exist. Run ./serve.sh first."
fi
