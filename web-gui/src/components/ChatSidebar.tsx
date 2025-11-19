import type { Conversation } from '../types';
import { useNavigate } from 'react-router-dom';

interface ChatSidebarProps {
    conversations: Conversation[];
    currentChatId: string | null;
    onNewChat: () => void;
    onDeleteChat: (id: string, e: React.MouseEvent) => void;
}

export function ChatSidebar({ conversations, currentChatId, onNewChat, onDeleteChat }: ChatSidebarProps) {
    const navigate = useNavigate();

    // Sort conversations by timestamp (newest first)
    const sortedConversations = [...conversations].sort((a, b) => b.timestamp - a.timestamp);

    return (
        <div className="chat-sidebar">
            <button className="new-chat-button" onClick={onNewChat}>
                <span>+</span> New Chat
            </button>

            <div className="conversations-list">
                {sortedConversations.map((conv) => (
                    <div
                        key={conv.id}
                        className={`conversation-item ${conv.id === currentChatId ? 'active' : ''}`}
                        onClick={() => navigate(`/chat/${conv.id}`)}
                    >
                        <div className="conversation-title">{conv.title}</div>
                        <button
                            className="delete-chat-button"
                            onClick={(e) => onDeleteChat(conv.id, e)}
                            title="Delete chat"
                        >
                            ×
                        </button>
                    </div>
                ))}
                {sortedConversations.length === 0 && (
                    <div className="no-conversations">
                        No history yet
                    </div>
                )}
            </div>
        </div>
    );
}
