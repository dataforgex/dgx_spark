import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ChatAPI } from '../api';
import type { Message, Conversation } from '../types';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { ChatSidebar } from './ChatSidebar';
import './Chat.css';

const SYSTEM_MESSAGE = 'You are a helpful AI assistant. You provide clear, concise, and accurate responses.';

export function Chat() {
  const { chatId } = useParams();
  const navigate = useNavigate();
  const [conversations, setConversations] = useState<Record<string, Conversation>>(() => {
    const saved = localStorage.getItem('chat_conversations');
    return saved ? JSON.parse(saved) : {};
  });

  // If no chatId, or invalid chatId, we might need to redirect or create new
  const currentChat = chatId ? conversations[chatId] : null;

  // Local state for the current view if we are in a "new chat" state (not saved yet)
  // OR just use the currentChat messages.
  // Strategy: If chatId is present, use that conversation. If not, show empty state ready to create new.

  const [isLoading, setIsLoading] = useState(false);
  const [modelInfo, setModelInfo] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const apiRef = useRef(new ChatAPI());

  useEffect(() => {
    apiRef.current.fetchModelInfo().then(setModelInfo);
  }, []);

  useEffect(() => {
    localStorage.setItem('chat_conversations', JSON.stringify(conversations));
  }, [conversations]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentChat?.messages, chatId]);

  // Redirect to a new chat if accessing /chat root and we have history, 
  // OR just stay at /chat as a "new chat" placeholder.
  // Let's go with: /chat is a fresh empty chat.

  const handleSend = async (userInput: string) => {
    setError(null);
    setIsLoading(true);

    let activeChatId = chatId;
    let updatedMessages: Message[] = [];

    if (!activeChatId || !conversations[activeChatId]) {
      // Create new conversation
      const newId = Date.now().toString();
      const newConversation: Conversation = {
        id: newId,
        title: userInput.slice(0, 30) + (userInput.length > 30 ? '...' : ''),
        messages: [
          { role: 'system', content: SYSTEM_MESSAGE },
          { role: 'user', content: userInput }
        ],
        timestamp: Date.now()
      };

      setConversations(prev => ({ ...prev, [newId]: newConversation }));
      activeChatId = newId;
      updatedMessages = newConversation.messages;
      navigate(`/chat/${newId}`);
    } else {
      // Update existing
      const chat = conversations[activeChatId];
      updatedMessages = [...chat.messages, { role: 'user', content: userInput }];

      setConversations(prev => ({
        ...prev,
        [activeChatId!]: {
          ...chat,
          messages: updatedMessages,
          timestamp: Date.now()
        }
      }));
    }

    try {
      const response = await apiRef.current.sendMessage(updatedMessages);
      const assistantMessage: Message = { role: 'assistant', content: response };

      setConversations(prev => ({
        ...prev,
        [activeChatId!]: {
          ...prev[activeChatId!],
          messages: [...updatedMessages, assistantMessage]
        }
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChat = () => {
    navigate('/chat');
  };

  const handleDeleteChat = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setConversations(prev => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    if (chatId === id) {
      navigate('/chat');
    }
  };

  const messages = currentChat ? currentChat.messages : [{ role: 'system' as const, content: SYSTEM_MESSAGE }];

  // Filter out system message for display if desired, or keep it. 
  // Current implementation displays all, but ChatMessage might hide system.

  const api = apiRef.current;

  return (
    <div className="chat-layout">
      <ChatSidebar
        conversations={Object.values(conversations)}
        currentChatId={chatId || null}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
      />

      <div className="chat-main">
        <div className="chat-header">
          <div className="chat-title">
            {currentChat ? currentChat.title : 'New Chat'}
          </div>
          <div className="chat-info">
            <div>Model: {api.getModel()}</div>
            {modelInfo && <div>Ctx: {modelInfo.toLocaleString()}</div>}
          </div>
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
    </div>
  );
}
