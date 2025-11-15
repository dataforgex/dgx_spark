import type { Message } from '../types';
import './ChatMessage.css';

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  if (message.role === 'system') {
    return null;
  }

  return (
    <div className={`message ${message.role}`}>
      <div className="message-header">
        {message.role === 'user' ? '💬 You' : '🤖 Assistant'}
      </div>
      <div className="message-content">
        {message.content}
      </div>
    </div>
  );
}
