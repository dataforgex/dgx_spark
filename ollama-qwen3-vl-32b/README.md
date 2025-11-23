# Ollama Server with Qwen3-VL-32B

This directory contains the configuration to serve the [Qwen3-VL-32B](https://ollama.com/library/qwen3-vl) model using Ollama.

## Model Details
- **Name:** qwen3-vl:32b
- **Type:** Vision-Language Model
- **Parameters:** 32B

## Usage

### Start the Server
```bash
./serve.sh
```

### API Endpoint
- **URL:** `http://localhost:11434/v1` (OpenAI compatible)
- **Port:** 11434

### Resource Usage
- **GPU Memory:** ~20-25 GB (Quantized)
- **Port:** 11434

## Features
- Vision-language understanding
- ARM64 optimized (via Ollama)
- OpenAI-compatible API
