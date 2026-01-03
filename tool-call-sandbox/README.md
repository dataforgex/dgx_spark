# Tool Call Sandbox

A modular system for defining and executing LLM tools in sandboxed environments.

## Architecture

```
tool-call-sandbox/
├── tools/                    # Tool definitions (skills-like pattern)
│   ├── code-execution/
│   │   └── TOOL.md          # Tool definition with YAML frontmatter
│   ├── bash-command/
│   │   └── TOOL.md
│   └── file-analysis/
│       └── TOOL.md
├── sandbox/                  # Docker sandbox environment
│   └── Dockerfile
├── server.py                 # FastAPI server
├── tool_loader.py            # Loads tools from TOOL.md files
├── executor.py               # Sandboxed execution engine
└── serve.sh                  # Startup script
```

## Tool Definition Format (Skills-like Pattern)

Each tool is defined in a `TOOL.md` file with YAML frontmatter:

```yaml
---
name: code-execution
description: Execute Python, JavaScript, or bash code in a sandbox
version: 1.0.0
enabled: true
sandbox:
  image: sandbox-executor:latest
  timeout: 30
  memory: 256m
  network: false
parameters:
  - name: code
    type: string
    required: true
    description: The code to execute
  - name: language
    type: string
    enum: [python, bash, node]
    default: python
---

# Code Execution Tool

## Purpose
Execute code snippets in a secure sandboxed environment...
```

## Quick Start

```bash
# Build the sandbox image
cd sandbox && docker build -t sandbox-executor:latest .

# Start the API server
./serve.sh

# API available at http://localhost:5176
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tools` | GET | List all available tools |
| `/api/tools/{name}` | GET | Get tool definition |
| `/api/execute/{tool}` | POST | Execute a tool |
| `/health` | GET | Health check |

## Adding New Tools

1. Create a directory under `tools/`
2. Add a `TOOL.md` with YAML frontmatter
3. Tools are auto-discovered on server startup

## Security

All code execution happens in Docker containers with:
- Network disabled (configurable)
- Memory limits (default 256MB)
- CPU limits (50%)
- Read-only filesystem
- Non-root user
- Execution timeout (default 30s)
