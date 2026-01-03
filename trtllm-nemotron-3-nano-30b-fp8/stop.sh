#!/bin/bash

CONTAINER_NAME="trtllm-nemotron-3-nano-30b-fp8"

if [ "$(docker ps -q -f name=^${CONTAINER_NAME}$)" ]; then
    echo "Stopping ${CONTAINER_NAME}..."
    docker stop ${CONTAINER_NAME}
    echo "Container stopped (preserved for fast restart)."
    echo ""
    echo "To restart quickly: docker start ${CONTAINER_NAME} && docker logs -f ${CONTAINER_NAME}"
    echo "To remove completely: docker rm ${CONTAINER_NAME}"
else
    echo "Container ${CONTAINER_NAME} is not running."
fi
