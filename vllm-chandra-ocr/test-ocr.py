#!/usr/bin/env python3
"""
Test script for Chandra OCR via vLLM OpenAI-compatible API.

Usage:
    python test-ocr.py                    # Test with sample text image
    python test-ocr.py path/to/image.png  # Test with specific image
    python test-ocr.py path/to/doc.pdf    # Test with PDF (first page)

The Chandra model outputs structured markdown/HTML with layout preservation.
"""

import argparse
import base64
import json
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Please install httpx: pip install httpx")
    sys.exit(1)

# Configuration
VLLM_BASE_URL = "http://localhost:8106/v1"
MODEL_NAME = "datalab-to/chandra"


def encode_image(image_path: str) -> tuple[str, str]:
    """Encode image to base64 and detect media type."""
    path = Path(image_path)
    suffix = path.suffix.lower()

    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }

    media_type = media_types.get(suffix, "image/png")

    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")

    return data, media_type


def create_sample_image() -> str:
    """Create a simple test image with text if no image provided."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("PIL not available. Please provide an image path or install pillow.")
        sys.exit(1)

    # Create a simple test image with text
    img = Image.new('RGB', (800, 400), color='white')
    draw = ImageDraw.Draw(img)

    # Try to use a system font, fall back to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except (OSError, IOError):
        font = ImageFont.load_default()
        font_small = font

    # Draw some test content
    draw.text((50, 30), "Chandra OCR Test Document", fill='black', font=font)
    draw.text((50, 80), "This is a test of the OCR capabilities.", fill='black', font=font_small)
    draw.text((50, 120), "Features tested:", fill='black', font=font_small)
    draw.text((70, 150), "1. Basic text recognition", fill='black', font=font_small)
    draw.text((70, 180), "2. Layout preservation", fill='black', font=font_small)
    draw.text((70, 210), "3. Structured output (Markdown)", fill='black', font=font_small)

    # Draw a simple table
    draw.text((50, 260), "Sample Table:", fill='black', font=font_small)
    draw.rectangle([50, 290, 350, 380], outline='black', width=2)
    draw.line([50, 320, 350, 320], fill='black', width=1)
    draw.line([150, 290, 150, 380], fill='black', width=1)
    draw.text((70, 295), "Item", fill='black', font=font_small)
    draw.text((170, 295), "Value", fill='black', font=font_small)
    draw.text((70, 335), "Test A", fill='black', font=font_small)
    draw.text((170, 335), "123", fill='black', font=font_small)

    # Save to temp file
    temp_path = "/tmp/chandra_test_image.png"
    img.save(temp_path)
    print(f"Created test image: {temp_path}")
    return temp_path


def ocr_image(image_path: str, prompt_type: str = "ocr_with_layout") -> dict:
    """
    Send image to Chandra OCR and get structured output.

    prompt_type options:
        - "ocr_with_layout": Full OCR with layout preservation (default)
        - "ocr": Basic OCR text extraction
        - "describe": Describe the image content
    """

    # Encode the image
    image_data, media_type = encode_image(image_path)

    # Chandra-specific prompts for different output types
    prompts = {
        "ocr_with_layout": "Perform OCR on this image. Extract all text while preserving the layout structure. Output as structured markdown with tables, lists, and formatting preserved.",
        "ocr": "Extract all text from this image.",
        "describe": "Describe what you see in this image, including any text, tables, diagrams, or other elements.",
    }

    prompt = prompts.get(prompt_type, prompts["ocr_with_layout"])

    # Build the request payload (OpenAI vision format)
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_data}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ],
        "max_tokens": 4096,
        "temperature": 0.1,  # Low temperature for accurate OCR
    }

    print(f"Sending request to {VLLM_BASE_URL}/chat/completions...")
    print(f"Image: {image_path}")
    print(f"Prompt type: {prompt_type}")
    print("-" * 50)

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{VLLM_BASE_URL}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError:
        print(f"Error: Cannot connect to {VLLM_BASE_URL}")
        print("Make sure the Chandra vLLM server is running:")
        print("  ./serve.sh")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e.response.status_code}")
        print(e.response.text)
        sys.exit(1)


def check_server_health() -> bool:
    """Check if the vLLM server is healthy."""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{VLLM_BASE_URL.replace('/v1', '')}/health")
            return response.status_code == 200
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Test Chandra OCR via vLLM")
    parser.add_argument("image", nargs="?", help="Path to image or PDF file")
    parser.add_argument(
        "--prompt-type", "-p",
        choices=["ocr_with_layout", "ocr", "describe"],
        default="ocr_with_layout",
        help="Type of OCR prompt to use"
    )
    parser.add_argument(
        "--raw", "-r",
        action="store_true",
        help="Output raw JSON response"
    )
    args = parser.parse_args()

    # Check server health
    print("Checking server health...")
    if not check_server_health():
        print("Warning: Server health check failed. The server may still be starting.")
        print("Continuing anyway...")
    else:
        print("Server is healthy.")
    print()

    # Get or create test image
    if args.image:
        image_path = args.image
        if not Path(image_path).exists():
            print(f"Error: File not found: {image_path}")
            sys.exit(1)
    else:
        print("No image provided. Creating a test image...")
        image_path = create_sample_image()

    # Perform OCR
    result = ocr_image(image_path, args.prompt_type)

    if args.raw:
        print(json.dumps(result, indent=2))
    else:
        # Extract and display the OCR result
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            print("\n" + "=" * 50)
            print("OCR RESULT:")
            print("=" * 50)
            print(content)
            print("=" * 50)

            # Show usage stats
            if "usage" in result:
                usage = result["usage"]
                print(f"\nTokens - Prompt: {usage.get('prompt_tokens', 'N/A')}, "
                      f"Completion: {usage.get('completion_tokens', 'N/A')}, "
                      f"Total: {usage.get('total_tokens', 'N/A')}")
        else:
            print("Unexpected response format:")
            print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
