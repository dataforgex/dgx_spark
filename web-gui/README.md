# LLM Chat Web GUI

A modern, responsive web-based chat interface for interacting with local LLM models, built with React, TypeScript, and Vite.

## Features

- Real-time chat interface with smooth animations
- Message history management
- Clear conversation history
- Model information display
- Error handling
- Responsive design with beautiful gradients
- Auto-scroll to latest messages
- Loading indicators

## Prerequisites

- Node.js (v18 or higher)
- npm
- A running LLM API server (default: http://localhost:8000)

## Installation

```bash
npm install
```

## Usage

### Development Mode

Start the development server with hot module replacement:

```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Configuration

The default API configuration is set in `src/api.ts`:

- API URL: `http://localhost:8000/v1/chat/completions`
- Model: `Qwen/Qwen3-Coder-30B-A3B-Instruct`
- Max Tokens: 2048
- Temperature: 0.7

You can modify these values in the `ChatAPI` constructor.

## Project Structure

```
src/
├── components/
│   ├── Chat.tsx           # Main chat container
│   ├── Chat.css
│   ├── ChatMessage.tsx    # Individual message component
│   ├── ChatMessage.css
│   ├── ChatInput.tsx      # Message input component
│   └── ChatInput.css
├── api.ts                 # API client
├── types.ts               # TypeScript type definitions
├── App.tsx                # Root component
├── App.css
├── index.css
└── main.tsx               # Entry point
```

## Technologies Used

- **React** - UI framework
- **TypeScript** - Type safety
- **Vite** - Fast build tool and dev server
- **CSS3** - Styling with gradients and animations

## License

MIT
