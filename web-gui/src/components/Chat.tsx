import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ChatAPI, AVAILABLE_MODELS } from '../api';
import { SERVICES } from '../config';
import type { Message, Conversation } from '../types';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { ChatSidebar } from './ChatSidebar';
import './Chat.css';

const getSystemMessage = (hasSearch: boolean, hasSandbox: boolean) => {
  let msg = 'You are a helpful AI assistant.';
  if (hasSearch) {
    msg += ' You have access to a web_search tool for current information, news, weather, or any data that might have changed recently.';
  }
  if (hasSandbox) {
    msg += ' You have access to sandbox tools for executing code (Python, bash, Node.js), analyzing files, and storing data. Use code_execution when calculations, data processing, or programming tasks are requested. Use data_storage to save and retrieve data between interactions.';
  }
  if (hasSearch || hasSandbox) {
    msg += ' Always prefer using your tools when appropriate rather than saying you cannot do something.';
  }
  return msg;
};

// Use centralized service URL from config
const MODEL_MANAGER_API = SERVICES.MODEL_MANAGER;

interface ManagedModel {
  id: string;
  name: string;
  status: string;
}

export function Chat() {
  const { chatId } = useParams();
  const navigate = useNavigate();
  const [conversations, setConversations] = useState<Record<string, Conversation>>(() => {
    const saved = localStorage.getItem('chat_conversations');
    return saved ? JSON.parse(saved) : {};
  });
  const [selectedModel, setSelectedModel] = useState<string>(() => {
    const saved = localStorage.getItem('selected_model');
    return saved || 'qwen3-coder-30b';
  });
  const [enableSearch, setEnableSearch] = useState<boolean>(() => {
    const saved = localStorage.getItem('enable_search');
    return saved === 'true';
  });
  const [enableSandbox, setEnableSandbox] = useState<boolean>(() => {
    const saved = localStorage.getItem('enable_sandbox');
    return saved === 'true';
  });
  const [sandboxAvailable, setSandboxAvailable] = useState(false);

  // If no chatId, or invalid chatId, we might need to redirect or create new
  const currentChat = chatId ? conversations[chatId] : null;

  // Local state for the current view if we are in a "new chat" state (not saved yet)
  // OR just use the currentChat messages.
  // Strategy: If chatId is present, use that conversation. If not, show empty state ready to create new.

  const [isLoading, setIsLoading] = useState(false);
  const [modelInfo, setModelInfo] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [runningModels, setRunningModels] = useState<Set<string>>(new Set());
  const [modelsLoaded, setModelsLoaded] = useState(false);
  const [contextInfo, setContextInfo] = useState<{ tokens: number; maxContext: number; percentUsed: number } | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const apiRef = useRef(new ChatAPI(selectedModel));

  useEffect(() => {
    apiRef.current = new ChatAPI(selectedModel);
    apiRef.current.fetchModelInfo().then(setModelInfo);
    // Also fetch sandbox tools
    apiRef.current.fetchSandboxTools().then(tools => {
      setSandboxAvailable(tools.length > 0);
    });
  }, [selectedModel]);

  // Fetch running models from model-manager API
  useEffect(() => {
    const fetchRunningModels = async () => {
      try {
        const response = await fetch(`${MODEL_MANAGER_API}/api/models`);
        if (response.ok) {
          const models: ManagedModel[] = await response.json();
          const running = new Set(
            models.filter(m => m.status === 'running').map(m => m.id)
          );
          setRunningModels(running);
          setModelsLoaded(true);

          // If currently selected model is not running, select first running model
          if (running.size > 0 && !running.has(selectedModel)) {
            const firstRunning = Array.from(running)[0];
            setSelectedModel(firstRunning);
          }
        }
      } catch (err) {
        console.error('Failed to fetch running models:', err);
      }
    };

    fetchRunningModels();
    const interval = setInterval(fetchRunningModels, 5000);
    return () => clearInterval(interval);
  }, [selectedModel]);

  useEffect(() => {
    localStorage.setItem('chat_conversations', JSON.stringify(conversations));
  }, [conversations]);

  useEffect(() => {
    localStorage.setItem('selected_model', selectedModel);
  }, [selectedModel]);

  useEffect(() => {
    localStorage.setItem('enable_search', enableSearch.toString());
  }, [enableSearch]);

  useEffect(() => {
    localStorage.setItem('enable_sandbox', enableSandbox.toString());
  }, [enableSandbox]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentChat?.messages, chatId]);

  // Update context/token info when messages change
  useEffect(() => {
    if (currentChat?.messages && currentChat.messages.length > 0) {
      const info = apiRef.current.getContextInfo(currentChat.messages);
      setContextInfo(info);
    } else {
      setContextInfo(null);
    }
  }, [currentChat?.messages]);

  // Redirect to a new chat if accessing /chat root and we have history, 
  // OR just stay at /chat as a "new chat" placeholder.
  // Let's go with: /chat is a fresh empty chat.

  const handleSend = async (userInput: string, image?: string) => {
    setError(null);
    setIsLoading(true);

    let activeChatId = chatId;
    let updatedMessages: Message[] = [];

    const userMessage: Message = {
      role: 'user',
      content: userInput,
      image: image
    };

    const systemMessage = getSystemMessage(enableSearch, enableSandbox && sandboxAvailable);

    if (!activeChatId || !conversations[activeChatId]) {
      // Create new conversation
      const newId = Date.now().toString();
      const newConversation: Conversation = {
        id: newId,
        title: userInput.slice(0, 30) + (userInput.length > 30 ? '...' : ''),
        messages: [
          { role: 'system', content: systemMessage },
          userMessage
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
      updatedMessages = [...chat.messages, userMessage];

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
      // Ensure we use the latest system message
      const messagesToSend = updatedMessages.map(msg =>
        msg.role === 'system' ? { ...msg, content: systemMessage } : msg
      );

      // Start API call - this continues even if component unmounts
      const responsePromise = apiRef.current.sendMessage(messagesToSend, enableSearch, enableSandbox && sandboxAvailable);

      responsePromise.then(response => {
        const assistantMessage: Message = {
          role: 'assistant',
          content: response.content,
          reasoning_content: response.reasoning_content,
          search_results: response.search_results
        };

        // Critical: Read localStorage at the moment of update to avoid race conditions
        // This ensures we don't overwrite updates from other chats
        const updateConversation = () => {
          const savedConversations = localStorage.getItem('chat_conversations');
          const currentConversations = savedConversations ? JSON.parse(savedConversations) : {};

          if (currentConversations[activeChatId!]) {
            // Append assistant message to the current messages in localStorage
            const existingMessages = currentConversations[activeChatId!].messages;

            // Only append if assistant message isn't already there (prevent duplicates)
            const hasResponse = existingMessages.some((msg: Message) =>
              msg.role === 'assistant' && msg.content === assistantMessage.content
            );

            if (!hasResponse) {
              currentConversations[activeChatId!] = {
                ...currentConversations[activeChatId!],
                messages: [...existingMessages, assistantMessage],
                timestamp: Date.now()
              };
              localStorage.setItem('chat_conversations', JSON.stringify(currentConversations));
            }
          }

          // Also update React state if component is still mounted
          setConversations(prev => {
            // Check if already updated to prevent duplicates
            if (prev[activeChatId!]?.messages.some(msg =>
              msg.role === 'assistant' && msg.content === assistantMessage.content
            )) {
              return prev;
            }

            return {
              ...prev,
              [activeChatId!]: {
                ...prev[activeChatId!],
                messages: [...prev[activeChatId!].messages, assistantMessage],
                timestamp: Date.now()
              }
            };
          });
        };

        updateConversation();
      }).catch(err => {
        console.error('Chat error:', err);
        setError(err instanceof Error ? err.message : 'An error occurred');
      }).finally(() => {
        setIsLoading(false);
      });

      // Don't await here - let it run in background
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
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

  const defaultSystemMessage = getSystemMessage(enableSearch, enableSandbox && sandboxAvailable);
  const messages = currentChat ? currentChat.messages : [{ role: 'system' as const, content: defaultSystemMessage }];

  // Filter out system message for display if desired, or keep it.
  // Current implementation displays all, but ChatMessage might hide system.

  return (
    <div className="chat-layout">
      <div
        className={`sidebar-overlay ${sidebarOpen ? 'open' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />
      <ChatSidebar
        conversations={Object.values(conversations)}
        currentChatId={chatId || null}
        onNewChat={() => { handleNewChat(); setSidebarOpen(false); }}
        onDeleteChat={handleDeleteChat}
        onSelectChat={() => setSidebarOpen(false)}
        isOpen={sidebarOpen}
      />

      <div className="chat-main">
        <div className="chat-header">
          <button className="menu-button" onClick={() => setSidebarOpen(true)}>
            ☰
          </button>
          <div className="chat-title">
            {currentChat ? currentChat.title : 'New Chat'}
          </div>
          <div className="chat-info">
            <div className="model-selector">
              <label htmlFor="model-select">Model:</label>
              <select
                id="model-select"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="model-select-dropdown"
                disabled={!modelsLoaded || runningModels.size === 0}
              >
                {!modelsLoaded ? (
                  <option value="">Loading models...</option>
                ) : runningModels.size === 0 ? (
                  <option value="">No models running</option>
                ) : (
                  Object.entries(AVAILABLE_MODELS)
                    .filter(([key]) => runningModels.has(key))
                    .map(([key, config]) => (
                      <option key={key} value={key}>
                        {config.name}
                      </option>
                    ))
                )}
              </select>
            </div>
            <div className="search-toggle">
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={enableSearch}
                  onChange={(e) => setEnableSearch(e.target.checked)}
                />
                <span className="toggle-slider"></span>
              </label>
              <span className="toggle-label">🔍 Search</span>
            </div>
            <div className="search-toggle">
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={enableSandbox}
                  onChange={(e) => setEnableSandbox(e.target.checked)}
                  disabled={!sandboxAvailable}
                />
                <span className="toggle-slider"></span>
              </label>
              <span className="toggle-label" title={sandboxAvailable ? 'Code execution sandbox' : 'Sandbox API not available'}>
                {sandboxAvailable ? '🔧 Sandbox' : '🔧 Sandbox (N/A)'}
              </span>
            </div>
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

        {contextInfo && (
          <div className="context-info">
            <span className={`token-count ${contextInfo.percentUsed > 70 ? 'warning' : ''} ${contextInfo.percentUsed > 90 ? 'critical' : ''}`}>
              {contextInfo.tokens.toLocaleString()} / {contextInfo.maxContext.toLocaleString()} tokens ({contextInfo.percentUsed}%)
            </span>
          </div>
        )}
        <ChatInput onSend={handleSend} disabled={isLoading} />
      </div>
    </div>
  );
}
