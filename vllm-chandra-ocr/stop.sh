#!/bin/bash

# Stop Chandra OCR vLLM server

CONTAINER_NAME="vllm-chandra-ocr"

echo "Stopping ${CONTAINER_NAME}..."

if [ "$(docker ps -q -f name=^${CONTAINER_NAME}$)" ]; then
    docker stop ${CONTAINER_NAME}
    echo "Container stopped."
else
    echo "Container is not running."
fi

if [ "$(docker ps -aq -f name=^${CONTAINER_NAME}$)" ]; then
    docker rm ${CONTAINER_NAME}
    echo "Container removed."
fi

echo "Done."
