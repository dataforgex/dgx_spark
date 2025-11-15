# Python Chat Interface

Interactive chat interface for local LLM implemented in Python.

## Prerequisites

- Python 3.8 or higher
- Local LLM server running on `http://localhost:8000`

## Installation

The virtual environment is already set up with the required dependencies (`requests`).

If you need to recreate it:
```bash
python3 -m venv venv
source venv/bin/activate
pip install requests
```

## Usage

### Quick Start
```bash
./start_chat.sh
```

### Manual Start
```bash
source venv/bin/activate
python chat.py
```

## Features

- **Interactive Chat**: Chat with the LLM in real-time
- **Typing Effect**: Responses appear with a typing animation
- **Conversation History**: Maintains context across messages
- **Auto-Discovery**: Fetches model's max context length from API

## Commands

- `/exit` or `/quit` - End the conversation
- `/clear` - Clear conversation history
- `/history` - View full conversation

## Configuration

Edit `chat.py` to customize:
- `api_url` - API endpoint
- `model` - Model name
- `system_message` - System prompt
- `max_tokens` - Maximum response length
- `temperature` - Sampling temperature (0.0-1.0)

## Files

- `chat.py` - Main chat interface
- `start_chat.sh` - Launcher script
- `venv/` - Python virtual environment
