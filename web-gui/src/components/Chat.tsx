import { useState, useEffect, useRef, Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ChatAPI, AVAILABLE_MODELS } from '../api';
import { SERVICES, getApiHost } from '../config';
import type { Message, Conversation } from '../types';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { ChatSidebar } from './ChatSidebar';
import './Chat.css';

// Error boundary to catch rendering errors
class ChatErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean; error: string }> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: '' };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error: error.message };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Chat error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '2rem', color: 'white', background: '#1e293b', minHeight: '50vh' }}>
          <h2>Something went wrong</h2>
          <p style={{ color: '#ef4444' }}>{this.state.error}</p>
          <button onClick={() => window.location.reload()} style={{ marginTop: '1rem', padding: '0.5rem 1rem' }}>
            Reload Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const getSystemMessage = (hasSearch: boolean, hasSandbox: boolean, hasVision: boolean = false) => {
  let msg = 'You are a helpful AI assistant.';
  if (hasVision) {
    msg += ' You have vision capabilities and CAN see and analyze images that users share with you. When a user sends an image, describe what you actually see in the image directly - do not claim you cannot see images.';
  }
  if (hasSearch) {
    msg += ' You have access to a web_search tool. Only use it when the user explicitly asks for current news, weather, prices, or real-time information that you cannot answer from your training data.';
  }
  if (hasSandbox) {
    msg += ' You have access to sandbox tools for executing code (Python, bash, Node.js). Only use these when the user explicitly asks for code execution, calculations, or data processing.';
  }
  if (hasSearch || hasSandbox) {
    msg += ' Do NOT use tools for simple greetings or conversational messages.';
  }
  return msg;
};

// Use centralized service URL from config
const MODEL_MANAGER_API = SERVICES.MODEL_MANAGER;

// Memory management limits to prevent browser crashes
const MAX_CONVERSATIONS = 50;  // Keep last 50 conversations
const MAX_MESSAGES_PER_CONVERSATION = 200;  // Keep last 200 messages per conversation

// Prune old conversations, keeping most recent by timestamp
const pruneConversations = (convs: Record<string, Conversation>): Record<string, Conversation> => {
  const entries = Object.entries(convs);
  if (entries.length <= MAX_CONVERSATIONS) return convs;

  // Sort by timestamp descending (newest first)
  entries.sort((a, b) => (b[1].timestamp || 0) - (a[1].timestamp || 0));

  // Keep only the most recent conversations
  const pruned = entries.slice(0, MAX_CONVERSATIONS);
  console.log(`Pruned ${entries.length - MAX_CONVERSATIONS} old conversations`);
  return Object.fromEntries(pruned);
};

// Prune old messages in a conversation, keeping system message and most recent
const pruneMessages = (messages: Message[]): Message[] => {
  if (messages.length <= MAX_MESSAGES_PER_CONVERSATION) return messages;

  // Keep system message (first) and most recent messages
  const systemMsg = messages.find(m => m.role === 'system');
  const nonSystemMsgs = messages.filter(m => m.role !== 'system');

  // Keep the most recent messages (excluding system)
  const keptMessages = nonSystemMsgs.slice(-(MAX_MESSAGES_PER_CONVERSATION - 1));

  console.log(`Pruned ${nonSystemMsgs.length - keptMessages.length} old messages`);
  return systemMsg ? [systemMsg, ...keptMessages] : keptMessages;
};

// Safe localStorage access for mobile browsers
const safeGetItem = (key: string): string | null => {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
};

const safeSetItem = (key: string, value: string): void => {
  try {
    localStorage.setItem(key, value);
  } catch {
    console.warn('localStorage not available');
  }
};

interface ManagedModel {
  id: string;
  name: string;
  status: string;
  port: number;
}

function ChatInner() {
  const { chatId } = useParams();
  const navigate = useNavigate();
  const [conversations, setConversations] = useState<Record<string, Conversation>>(() => {
    const saved = safeGetItem('chat_conversations');
    if (!saved) return {};
    const parsed = JSON.parse(saved);
    // Prune on load to clean up any accumulated data
    return pruneConversations(parsed);
  });
  const [selectedModel, setSelectedModel] = useState<string>(() => {
    const saved = safeGetItem('selected_model');
    return saved || 'qwen3-coder-30b';
  });
  const [enableSearch, setEnableSearch] = useState<boolean>(() => {
    const saved = safeGetItem('enable_search');
    return saved === 'true';
  });
  const [enableSandbox, setEnableSandbox] = useState<boolean>(() => {
    const saved = safeGetItem('enable_sandbox');
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

  // Fetch running models from model-manager API and check endpoint health
  useEffect(() => {
    const checkModelHealth = async (port: number): Promise<boolean> => {
      try {
        const response = await fetch(`http://${getApiHost()}:${port}/v1/models`, {
          signal: AbortSignal.timeout(2000),
        });
        return response.ok;
      } catch {
        return false;
      }
    };

    const fetchRunningModels = async () => {
      try {
        const response = await fetch(`${MODEL_MANAGER_API}/api/models`);
        if (response.ok) {
          const models: ManagedModel[] = await response.json();

          // Check both model-manager status AND actual endpoint health
          const healthChecks = await Promise.all(
            models.map(async (m) => {
              // If model-manager says running, trust it
              if (m.status === 'running') return { id: m.id, running: true };
              // Otherwise, check if endpoint is actually responding (for externally managed models)
              const isHealthy = await checkModelHealth(m.port);
              return { id: m.id, running: isHealthy };
            })
          );

          const running = new Set(
            healthChecks.filter(h => h.running).map(h => h.id)
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
    safeSetItem('chat_conversations', JSON.stringify(conversations));
  }, [conversations]);

  useEffect(() => {
    safeSetItem('selected_model', selectedModel);
  }, [selectedModel]);

  useEffect(() => {
    safeSetItem('enable_search', enableSearch.toString());
  }, [enableSearch]);

  useEffect(() => {
    safeSetItem('enable_sandbox', enableSandbox.toString());
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

    const systemMessage = getSystemMessage(enableSearch, enableSandbox && sandboxAvailable, selectedModel.toLowerCase().includes('vl'));

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

      setConversations(prev => pruneConversations({ ...prev, [newId]: newConversation }));
      activeChatId = newId;
      updatedMessages = newConversation.messages;
      navigate(`/chat/${newId}`);
    } else {
      // Update existing
      const chat = conversations[activeChatId];
      updatedMessages = pruneMessages([...chat.messages, userMessage]);

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
          const savedConversations = safeGetItem('chat_conversations');
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
                messages: pruneMessages([...existingMessages, assistantMessage]),
                timestamp: Date.now()
              };
              safeSetItem('chat_conversations', JSON.stringify(pruneConversations(currentConversations)));
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
                messages: pruneMessages([...prev[activeChatId!].messages, assistantMessage]),
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

  const defaultSystemMessage = getSystemMessage(enableSearch, enableSandbox && sandboxAvailable, selectedModel.toLowerCase().includes('vl'));
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

// Export wrapped with error boundary
export function Chat() {
  return (
    <ChatErrorBoundary>
      <ChatInner />
    </ChatErrorBoundary>
  );
}
