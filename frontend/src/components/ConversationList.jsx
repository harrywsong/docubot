import { useState, useEffect } from 'react';
import { Plus, MessageSquare, Trash2 } from 'lucide-react';
import { listConversations, createConversation, deleteConversation } from '../api';

export default function ConversationList({ selectedConversation, userId, onSelectConversation, onToast }) {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (userId) {
      loadConversations();
    }
  }, [userId]);

  async function loadConversations() {
    try {
      setLoading(true);
      const data = await listConversations(userId);
      setConversations(data.conversations || []);
    } catch (error) {
      onToast(error.message, 'error');
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate() {
    try {
      const data = await createConversation(userId);
      setConversations(prev => [data.conversation, ...prev]);
      onSelectConversation(data.conversation.id);
      onToast('Conversation created', 'success');
    } catch (error) {
      onToast(error.message, 'error');
    }
  }

  async function handleDelete(id, e) {
    e.stopPropagation();
    if (!confirm('Delete this conversation?')) return;

    try {
      await deleteConversation(id);
      setConversations(prev => prev.filter(c => c.id !== id));
      if (selectedConversation === id) {
        onSelectConversation(null);
      }
      onToast('Conversation deleted', 'success');
    } catch (error) {
      onToast(error.message, 'error');
    }
  }

  function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  }

  return (
    <div className="flex flex-col h-full">
      {/* New Conversation Button */}
      <div className="p-4">
        <button
          onClick={handleCreate}
          className="btn-primary w-full flex items-center justify-center gap-2"
        >
          <Plus className="w-4 h-4" />
          New Conversation
        </button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-2">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="flex gap-1">
              <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />
              <div className="w-2 h-2 rounded-full bg-accent animate-pulse animation-delay-100" />
              <div className="w-2 h-2 rounded-full bg-accent animate-pulse animation-delay-200" />
            </div>
          </div>
        ) : conversations.length === 0 ? (
          <div className="text-center py-8 px-4">
            <MessageSquare className="w-8 h-8 mx-auto mb-3 text-foreground-muted opacity-50" />
            <p className="text-sm text-foreground-muted">No conversations yet</p>
          </div>
        ) : (
          <div className="space-y-1">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                onClick={() => onSelectConversation(conv.id)}
                className={`w-full text-left p-3 rounded-lg transition-all duration-200 group cursor-pointer ${
                  selectedConversation === conv.id
                    ? 'bg-white/[0.08] border border-white/[0.1]'
                    : 'hover:bg-white/[0.05] border border-transparent'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate mb-1">
                      {conv.title || 'New Conversation'}
                    </p>
                    <p className="text-xs text-foreground-muted">
                      {formatDate(conv.created_at)}
                    </p>
                  </div>
                  <button
                    onClick={(e) => handleDelete(conv.id, e)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-red-500/20 rounded"
                    title="Delete conversation"
                  >
                    <Trash2 className="w-3 h-3 text-red-400" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
