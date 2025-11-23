import { useState } from 'react';
import type { Message } from '../types';
import './ChatMessage.css';

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const [showThinking, setShowThinking] = useState(false);

  if (message.role === 'system') {
    return null;
  }

  return (
    <div className={`message ${message.role}`}>
      <div className="message-header">
        {message.role === 'user' ? '💬 You' : '🤖 Assistant'}
      </div>

      {message.image && (
        <div className="message-image">
          <img src={message.image} alt="User upload" />
        </div>
      )}

      {message.search_results && message.search_results.length > 0 && (
        <div className="search-results-section">
          <div className="search-results-header">🔍 Search Results</div>
          <div className="search-results-grid">
            {message.search_results.map((result, idx) => (
              <a
                key={idx}
                href={result.url}
                target="_blank"
                rel="noopener noreferrer"
                className="search-result-card"
              >
                <div className="search-result-title">{result.title}</div>
                <div className="search-result-snippet">{result.snippet}</div>
                <div className="search-result-url">{new URL(result.url).hostname}</div>
              </a>
            ))}
          </div>
        </div>
      )}

      {message.reasoning_content && (
        <div className="thinking-section">
          <button
            className="thinking-toggle"
            onClick={() => setShowThinking(!showThinking)}
          >
            {showThinking ? '▼' : '▶'} Thinking Process
          </button>
          {showThinking && (
            <div className="thinking-content">
              {message.reasoning_content}
            </div>
          )}
        </div>
      )}

      <div className="message-content">
        {message.content}
      </div>
    </div>
  );
}
