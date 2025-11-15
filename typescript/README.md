# TypeScript Chat Interface

Interactive chat interface for local LLM implemented in TypeScript.

## Prerequisites

- Node.js 18+ and npm
- Local LLM server running on `http://localhost:8000`

## Installation

Install dependencies:
```bash
npm install
```

This will install:
- `typescript` - TypeScript compiler
- `tsx` - TypeScript executor (no build needed)
- `@types/node` - Node.js type definitions

## Usage

### Quick Start
```bash
npm run chat
```

Or use the launcher script:
```bash
./start_chat.sh
```

### Build and Run (optional)
```bash
npm run build
npm start
```

## Features

- **Type Safety**: Full TypeScript type checking
- **Modern Syntax**: Uses async/await and native fetch API
- **Interactive Chat**: Chat with the LLM in real-time
- **Typing Effect**: Responses appear with a typing animation
- **Conversation History**: Maintains context across messages
- **Auto-Discovery**: Fetches model's max context length from API

## Commands

- `/exit` or `/quit` - End the conversation
- `/clear` - Clear conversation history
- `/history` - View full conversation

## Configuration

Edit `chat.ts` to customize:
- `apiUrl` - API endpoint
- `model` - Model name
- `systemMessage` - System prompt
- `maxTokens` - Maximum response length
- `temperature` - Sampling temperature (0.0-1.0)

## Files

- `chat.ts` - Main chat interface (TypeScript)
- `package.json` - Node.js project configuration
- `tsconfig.json` - TypeScript compiler configuration
- `start_chat.sh` - Launcher script
- `dist/` - Compiled JavaScript output (after build)

## Development

The project uses:
- **ES Modules** - Modern JavaScript module system
- **Native Fetch API** - Built-in HTTP client
- **Readline/Promises** - Async readline interface
- **Strict Mode** - Full TypeScript strict type checking
