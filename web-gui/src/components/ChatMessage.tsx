import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import type { Message } from '../types';
import './ChatMessage.css';
import 'highlight.js/styles/github-dark.css';

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

      <div className={`message-layout ${message.search_results && message.search_results.length > 0 ? 'with-search' : ''}`}>
        <div className="message-main">
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
            <ReactMarkdown rehypePlugins={[rehypeHighlight]}>
              {message.content}
            </ReactMarkdown>
          </div>
        </div>

        {message.search_results && message.search_results.length > 0 && (
          <div className="search-results-sidebar">
            <div className="search-results-header">🔍 Sources</div>
            <div className="search-results-list">
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
      </div>
    </div>
  );
}
