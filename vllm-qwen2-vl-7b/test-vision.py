#!/usr/bin/env python3
"""
Test script for Qwen2-VL-7B vision model
Demonstrates image understanding, OCR, and multimodal capabilities
"""

import base64
import requests
import json
from pathlib import Path

# API endpoint
API_URL = "http://localhost:8101/v1/chat/completions"

def encode_image_to_base64(image_path):
    """Encode image file to base64 string"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def test_vision_with_url():
    """Test 1: Analyze an image from URL"""
    print("=" * 60)
    print("TEST 1: Analyzing image from URL")
    print("=" * 60)

    payload = {
        "model": "Qwen/Qwen2-VL-7B-Instruct",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
                        }
                    },
                    {
                        "type": "text",
                        "text": "Describe this image in detail. What do you see?"
                    }
                ]
            }
        ],
        "max_tokens": 300
    }

    response = requests.post(API_URL, json=payload)
    if response.status_code == 200:
        result = response.json()
        print(f"\n✓ Response:\n{result['choices'][0]['message']['content']}\n")
    else:
        print(f"\n✗ Error: {response.status_code}\n{response.text}\n")

def test_vision_with_local_image(image_path):
    """Test 2: Analyze a local image"""
    print("=" * 60)
    print(f"TEST 2: Analyzing local image: {image_path}")
    print("=" * 60)

    if not Path(image_path).exists():
        print(f"\n⚠️ Image not found: {image_path}")
        print("Skipping this test. Provide your own image path to test.\n")
        return

    base64_image = encode_image_to_base64(image_path)

    payload = {
        "model": "Qwen/Qwen2-VL-7B-Instruct",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    },
                    {
                        "type": "text",
                        "text": "What's in this image? Describe in detail."
                    }
                ]
            }
        ],
        "max_tokens": 300
    }

    response = requests.post(API_URL, json=payload)
    if response.status_code == 200:
        result = response.json()
        print(f"\n✓ Response:\n{result['choices'][0]['message']['content']}\n")
    else:
        print(f"\n✗ Error: {response.status_code}\n{response.text}\n")

def test_ocr_capability():
    """Test 3: OCR from image with text"""
    print("=" * 60)
    print("TEST 3: OCR - Extract text from image")
    print("=" * 60)

    payload = {
        "model": "Qwen/Qwen2-VL-7B-Instruct",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "https://raw.githubusercontent.com/openai/openai-python/main/examples/data/example-image.png"
                        }
                    },
                    {
                        "type": "text",
                        "text": "Read and extract all text visible in this image. List each piece of text you can see."
                    }
                ]
            }
        ],
        "max_tokens": 500
    }

    response = requests.post(API_URL, json=payload)
    if response.status_code == 200:
        result = response.json()
        print(f"\n✓ Response:\n{result['choices'][0]['message']['content']}\n")
    else:
        print(f"\n✗ Error: {response.status_code}\n{response.text}\n")

def test_multi_turn_conversation():
    """Test 4: Multi-turn conversation about an image"""
    print("=" * 60)
    print("TEST 4: Multi-turn conversation")
    print("=" * 60)

    # First turn
    payload = {
        "model": "Qwen/Qwen2-VL-7B-Instruct",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
                        }
                    },
                    {
                        "type": "text",
                        "text": "What's the main subject of this image?"
                    }
                ]
            }
        ],
        "max_tokens": 100
    }

    response = requests.post(API_URL, json=payload)
    if response.status_code == 200:
        result = response.json()
        first_response = result['choices'][0]['message']['content']
        print(f"\n✓ Turn 1 Response:\n{first_response}\n")

        # Second turn - follow up question
        payload["messages"].append({"role": "assistant", "content": first_response})
        payload["messages"].append({
            "role": "user",
            "content": "What time of day does it appear to be?"
        })

        response = requests.post(API_URL, json=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Turn 2 Response:\n{result['choices'][0]['message']['content']}\n")
    else:
        print(f"\n✗ Error: {response.status_code}\n{response.text}\n")

def main():
    print("\n" + "=" * 60)
    print("Qwen2-VL-7B Vision Model Test Suite")
    print("API: http://localhost:8101")
    print("=" * 60 + "\n")

    try:
        # Test 1: Image from URL
        test_vision_with_url()

        # Test 2: Local image (provide your own path)
        # test_vision_with_local_image("/path/to/your/image.jpg")

        # Test 3: OCR capabilities
        test_ocr_capability()

        # Test 4: Multi-turn conversation
        test_multi_turn_conversation()

        print("=" * 60)
        print("✓ All tests completed!")
        print("=" * 60)

        print("\n📝 Next Steps:")
        print("1. Try with your own images: test_vision_with_local_image('your_image.jpg')")
        print("2. Test PDF screenshots for document processing")
        print("3. Test Excel screenshots for table understanding")
        print("4. Build a document processing pipeline!")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")

if __name__ == "__main__":
    main()
