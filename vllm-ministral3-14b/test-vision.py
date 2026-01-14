#!/usr/bin/env python3
"""
Test script for Ministral-3-14B vision model
Demonstrates image understanding, tool calling, and multimodal capabilities
"""

import base64
import requests
import json
from pathlib import Path

# API endpoint
API_URL = "http://localhost:8103/v1/chat/completions"
MODEL_NAME = "mistralai/Ministral-3-14B-Instruct-2512"


def encode_image_to_base64(image_path):
    """Encode image file to base64 string"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def test_text_generation():
    """Test 1: Basic text generation"""
    print("=" * 60)
    print("TEST 1: Basic text generation")
    print("=" * 60)

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": "What are the key features of the Mistral AI models? Keep it brief."
            }
        ],
        "max_tokens": 300,
        "temperature": 0.1
    }

    response = requests.post(API_URL, json=payload)
    if response.status_code == 200:
        result = response.json()
        print(f"\nResponse:\n{result['choices'][0]['message']['content']}\n")
    else:
        print(f"\nError: {response.status_code}\n{response.text}\n")


def test_vision_with_url():
    """Test 2: Analyze an image from URL"""
    print("=" * 60)
    print("TEST 2: Analyzing image from URL")
    print("=" * 60)

    payload = {
        "model": MODEL_NAME,
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
        "max_tokens": 300,
        "temperature": 0.1
    }

    response = requests.post(API_URL, json=payload)
    if response.status_code == 200:
        result = response.json()
        print(f"\nResponse:\n{result['choices'][0]['message']['content']}\n")
    else:
        print(f"\nError: {response.status_code}\n{response.text}\n")


def test_vision_with_local_image(image_path):
    """Test 3: Analyze a local image"""
    print("=" * 60)
    print(f"TEST 3: Analyzing local image: {image_path}")
    print("=" * 60)

    if not Path(image_path).exists():
        print(f"\nImage not found: {image_path}")
        print("Skipping this test. Provide your own image path to test.\n")
        return

    base64_image = encode_image_to_base64(image_path)

    payload = {
        "model": MODEL_NAME,
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
        "max_tokens": 300,
        "temperature": 0.1
    }

    response = requests.post(API_URL, json=payload)
    if response.status_code == 200:
        result = response.json()
        print(f"\nResponse:\n{result['choices'][0]['message']['content']}\n")
    else:
        print(f"\nError: {response.status_code}\n{response.text}\n")


def test_tool_calling():
    """Test 4: Function calling / tool use"""
    print("=" * 60)
    print("TEST 4: Function calling / tool use")
    print("=" * 60)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA"
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "The temperature unit"
                        }
                    },
                    "required": ["location"]
                }
            }
        }
    ]

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": "What's the weather like in Paris, France?"
            }
        ],
        "tools": tools,
        "tool_choice": "auto",
        "max_tokens": 300,
        "temperature": 0.1
    }

    response = requests.post(API_URL, json=payload)
    if response.status_code == 200:
        result = response.json()
        message = result['choices'][0]['message']
        if 'tool_calls' in message and message['tool_calls']:
            print(f"\nTool calls detected:")
            for tool_call in message['tool_calls']:
                print(f"  Function: {tool_call['function']['name']}")
                print(f"  Arguments: {tool_call['function']['arguments']}")
        else:
            print(f"\nResponse:\n{message.get('content', 'No content')}\n")
    else:
        print(f"\nError: {response.status_code}\n{response.text}\n")


def test_json_output():
    """Test 5: JSON structured output"""
    print("=" * 60)
    print("TEST 5: JSON structured output")
    print("=" * 60)

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": "List 3 programming languages with their main use cases. Respond in JSON format with an array of objects containing 'name' and 'use_case' fields."
            }
        ],
        "max_tokens": 500,
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }

    response = requests.post(API_URL, json=payload)
    if response.status_code == 200:
        result = response.json()
        content = result['choices'][0]['message']['content']
        print(f"\nResponse:\n{content}\n")
        try:
            parsed = json.loads(content)
            print("JSON parsed successfully!")
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}")
    else:
        print(f"\nError: {response.status_code}\n{response.text}\n")


def test_multi_turn_conversation():
    """Test 6: Multi-turn conversation"""
    print("=" * 60)
    print("TEST 6: Multi-turn conversation")
    print("=" * 60)

    messages = [
        {"role": "user", "content": "My name is Alice. I'm a software engineer."}
    ]

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "max_tokens": 100,
        "temperature": 0.1
    }

    response = requests.post(API_URL, json=payload)
    if response.status_code == 200:
        result = response.json()
        first_response = result['choices'][0]['message']['content']
        print(f"\nTurn 1 Response:\n{first_response}\n")

        # Second turn - follow up question
        messages.append({"role": "assistant", "content": first_response})
        messages.append({"role": "user", "content": "What's my name and profession?"})
        payload["messages"] = messages

        response = requests.post(API_URL, json=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"Turn 2 Response:\n{result['choices'][0]['message']['content']}\n")
    else:
        print(f"\nError: {response.status_code}\n{response.text}\n")


def main():
    print("\n" + "=" * 60)
    print("Ministral-3-14B Vision Model Test Suite")
    print(f"API: {API_URL}")
    print("=" * 60 + "\n")

    try:
        # Test 1: Basic text generation
        test_text_generation()

        # Test 2: Image from URL
        test_vision_with_url()

        # Test 3: Local image (provide your own path)
        # test_vision_with_local_image("/path/to/your/image.jpg")

        # Test 4: Tool calling
        test_tool_calling()

        # Test 5: JSON output
        test_json_output()

        # Test 6: Multi-turn conversation
        test_multi_turn_conversation()

        print("=" * 60)
        print("All tests completed!")
        print("=" * 60)

        print("\nNext Steps:")
        print("1. Try with your own images: test_vision_with_local_image('your_image.jpg')")
        print("2. Build function calling pipelines with the tool use feature")
        print("3. Use JSON output mode for structured data extraction")

    except requests.exceptions.ConnectionError:
        print("\nConnection Error: Could not connect to the server.")
        print(f"Make sure the server is running at {API_URL}")
        print("Start the server with: ./serve.sh")
    except Exception as e:
        print(f"\nTest failed: {e}")


if __name__ == "__main__":
    main()
