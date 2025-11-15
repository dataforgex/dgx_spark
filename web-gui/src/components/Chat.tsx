import { useState, useEffect, useRef } from 'react';
import { ChatAPI } from '../api';
import type { Message } from '../types';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import './Chat.css';

const SYSTEM_MESSAGE = 'You are a helpful AI assistant. You provide clear, concise, and accurate responses.';

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'system', content: SYSTEM_MESSAGE }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [modelInfo, setModelInfo] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const apiRef = useRef(new ChatAPI());

  useEffect(() => {
    // Fetch model info on mount
    apiRef.current.fetchModelInfo().then(setModelInfo);
  }, []);

  useEffect(() => {
    // Auto-scroll to bottom when messages change
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (userInput: string) => {
    setError(null);
    const newUserMessage: Message = { role: 'user', content: userInput };
    const updatedMessages = [...messages, newUserMessage];
    setMessages(updatedMessages);
    setIsLoading(true);

    try {
      const response = await apiRef.current.sendMessage(updatedMessages);
      const assistantMessage: Message = { role: 'assistant', content: response };
      setMessages([...updatedMessages, assistantMessage]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      // Remove the failed user message
      setMessages(messages);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setMessages([{ role: 'system', content: SYSTEM_MESSAGE }]);
    setError(null);
  };

  const api = apiRef.current;

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="chat-title">🤖 Interactive Chat with Local LLM</div>
        <div className="chat-info">
          <div>Model: {api.getModel()}</div>
          <div>API: {api.getApiUrl()}</div>
          {modelInfo && <div>Max Context: {modelInfo.toLocaleString()} tokens</div>}
          <div>Max Output: {api.getMaxTokens().toLocaleString()} tokens</div>
          <div>Temperature: {api.getTemperature()}</div>
        </div>
        <button className="clear-button" onClick={handleClear}>
          Clear History 🗑️
        </button>
      </div>

      <div className="messages-container">
        {messages.map((msg, idx) => (
          <ChatMessage key={idx} message={msg} />
        ))}
        {isLoading && (
          <div className="loading-indicator">
            <div className="loading-dots">
              <span>.</span><span>.</span><span>.</span>
            </div>
            Thinking...
          </div>
        )}
        {error && (
          <div className="error-message">
            ❌ Error: {error}
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      <ChatInput onSend={handleSend} disabled={isLoading} />
    </div>
  );
}
