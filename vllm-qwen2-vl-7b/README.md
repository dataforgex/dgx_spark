# vLLM Qwen2-VL-7B Server (Vision Model)

This directory contains scripts and configuration for running the **Qwen2-VL-7B-Instruct** vision-language model with vLLM.

**Container Name:** `vllm-qwen2-vl-7b`
**Default Port:** `8101`
**Model:** `Qwen/Qwen2-VL-7B-Instruct`
**Type:** Vision-Language Model (VLM)

## Quick Start

### Start the Vision Model Server

```bash
./serve.sh
```

The server will be available at `http://localhost:8101` with OpenAI-compatible vision API endpoints.

### Managing the Server

```bash
# Stop the server
docker stop vllm-qwen2-vl-7b

# Start the server (fast - model already cached)
docker start vllm-qwen2-vl-7b

# Restart the server
docker restart vllm-qwen2-vl-7b

# View logs
docker logs -f vllm-qwen2-vl-7b

# Remove container (to start fresh)
docker rm -f vllm-qwen2-vl-7b
```

## Capabilities

This vision model can:
- **Understand images**: Describe scenes, objects, people, actions
- **OCR**: Extract text from images and documents
- **Visual Q&A**: Answer questions about images
- **PDF Processing**: Read text from PDF screenshots
- **Table Understanding**: Interpret Excel/CSV data from screenshots
- **Multi-turn conversations**: Discuss images across multiple messages

## Configuration

Edit the variables at the top of `serve.sh` to customize your setup:

### Memory & Concurrency
- `MAX_MODEL_LEN=32768` - Maximum context length
- `MAX_NUM_SEQS=64` - Maximum concurrent sequences (lower than text models)
- `GPU_MEMORY_UTILIZATION=0.25` - 25% GPU memory (for multi-model setup)

### Performance Options
- `ENABLE_PREFIX_CACHING=true` - Cache common prefixes
- `ENABLE_CHUNKED_PREFILL=true` - Reduce latency for long prompts

## Testing the Server

### Test Script

Run the comprehensive test suite:

```bash
python3 test-vision.py
```

This will test:
1. Image understanding from URLs
2. OCR capabilities
3. Multi-turn conversations

### Manual Testing with curl

```bash
curl http://localhost:8101/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2-VL-7B-Instruct",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "image_url",
            "image_url": {
              "url": "https://example.com/image.jpg"
            }
          },
          {
            "type": "text",
            "text": "What do you see in this image?"
          }
        ]
      }
    ],
    "max_tokens": 300
  }'
```

## Usage with Python

### From URL

```python
import requests

response = requests.post(
    "http://localhost:8101/v1/chat/completions",
    json={
        "model": "Qwen/Qwen2-VL-7B-Instruct",
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": "https://example.com/image.jpg"}
                },
                {
                    "type": "text",
                    "text": "Describe this image"
                }
            ]
        }],
        "max_tokens": 300
    }
)

print(response.json()['choices'][0]['message']['content'])
```

### From Local File (Base64)

```python
import base64
import requests

# Encode image to base64
with open("image.jpg", "rb") as f:
    image_base64 = base64.b64encode(f.read()).decode('utf-8')

response = requests.post(
    "http://localhost:8101/v1/chat/completions",
    json={
        "model": "Qwen/Qwen2-VL-7B-Instruct",
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                },
                {
                    "type": "text",
                    "text": "Extract all text from this image"
                }
            ]
        }],
        "max_tokens": 500
    }
)

print(response.json()['choices'][0]['message']['content'])
```

## Use Cases

### 1. PDF Text Extraction

```python
from pdf2image import convert_from_path
import base64
import requests

# Convert PDF to images
images = convert_from_path('document.pdf')

for i, image in enumerate(images):
    # Save to temp file and encode
    image.save(f'page_{i}.jpg', 'JPEG')
    with open(f'page_{i}.jpg', 'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode()

    # Extract text from page
    response = requests.post(
        "http://localhost:8101/v1/chat/completions",
        json={
            "model": "Qwen/Qwen2-VL-7B-Instruct",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    {"type": "text", "text": "Extract all text from this PDF page"}
                ]
            }]
        }
    )

    print(f"Page {i+1}:", response.json()['choices'][0]['message']['content'])
```

### 2. Excel/Table Understanding

Screenshot an Excel file, then:

```python
# Send screenshot to vision model
response = requests.post(
    "http://localhost:8101/v1/chat/completions",
    json={
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{excel_screenshot_b64}"}},
                {"type": "text", "text": "Convert this table to JSON format"}
            ]
        }]
    }
)
```

### 3. Combined Pipeline with Qwen3-Coder

```python
# Step 1: Extract text from image with Qwen2-VL (port 8101)
vision_response = requests.post("http://localhost:8101/v1/chat/completions", ...)
extracted_text = vision_response.json()['choices'][0]['message']['content']

# Step 2: Generate mind map from extracted text with Qwen3-Coder (port 8100)
mindmap_response = requests.post(
    "http://localhost:8100/v1/chat/completions",
    json={
        "messages": [{
            "role": "user",
            "content": f"Create a mind map in Markdown from this text:\n\n{extracted_text}"
        }]
    }
)
```

## Multi-Model Setup

This vision model runs alongside Qwen3-Coder-30B:

| Model | Port | GPU Memory | Use Case |
|-------|------|------------|----------|
| Qwen3-Coder-30B | 8100 | 55% (~65 GB) | Text/code generation |
| Qwen2-VL-7B | 8101 | 25% (~26 GB) | Vision understanding |
| **Total** | | **80%** | **20% safety margin** |

## Troubleshooting

### Out of Memory Errors
If running alongside other models:
- Current allocation: 25% (for 80% total with Qwen3-Coder at 55%)
- Reduce to 20% if adding more models
- Stop other GPU processes

### Slow Vision Processing
- Vision models are slower than text-only models
- Reduce image resolution before sending
- Use smaller `MAX_MODEL_LEN` if not needed

### Image Format Issues
- Supported formats: JPEG, PNG, WebP
- Use base64 encoding for local files
- Use direct URLs for web images

## Performance Notes

**Model Size:** ~15 GB
**Startup Time:**
- First run (download): ~3-4 minutes
- Cached runs: ~1-2 minutes (much faster than 30B model)

**Concurrency:**
- Default: 64 concurrent sequences
- Vision processing is more memory-intensive than text
- Adjust `MAX_NUM_SEQS` based on your needs

## References

- [Qwen2-VL Model Card](https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct)
- [vLLM Vision Documentation](https://docs.vllm.ai/en/latest/models/vlm.html)
- [OpenAI Vision API Format](https://platform.openai.com/docs/guides/vision)
