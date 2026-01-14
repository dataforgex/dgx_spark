import type { Conversation } from '../types';
import { useNavigate } from 'react-router-dom';

interface ChatSidebarProps {
    conversations: Conversation[];
    currentChatId: string | null;
    onNewChat: () => void;
    onDeleteChat: (id: string, e: React.MouseEvent) => void;
    onSelectChat?: () => void;
    isOpen?: boolean;
}

export function ChatSidebar({ conversations, currentChatId, onNewChat, onDeleteChat, onSelectChat, isOpen }: ChatSidebarProps) {
    const navigate = useNavigate();

    // Sort conversations by timestamp (newest first)
    const sortedConversations = [...conversations].sort((a, b) => b.timestamp - a.timestamp);

    const handleSelectChat = (id: string) => {
        navigate(`/chat/${id}`);
        onSelectChat?.();
    };

    return (
        <div className={`chat-sidebar ${isOpen ? 'open' : ''}`}>
            <button className="new-chat-button" onClick={onNewChat}>
                <span>+</span> New Chat
            </button>

            <div className="conversations-list">
                {sortedConversations.map((conv) => (
                    <div
                        key={conv.id}
                        className={`conversation-item ${conv.id === currentChatId ? 'active' : ''}`}
                        onClick={() => handleSelectChat(conv.id)}
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
