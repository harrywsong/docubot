import { useState, useEffect } from 'react';
import { listConversations, deleteConversation, createConversation } from '../api';

export default function ConversationList({ selectedId, onSelect, onToast }) {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadConversations();
  }, []);

  async function loadConversations() {
    try {
      const response = await listConversations();
      setConversations(response.conversations);
    } catch (error) {
      onToast(`Failed to load conversations: ${error.message}`, 'error');
    }
  }

  async function handleNewConversation() {
    setLoading(true);
    try {
      const response = await createConversation();
      await loadConversations();
      onSelect(response.conversation.id);
      onToast('New conversation created', 'success');
    } catch (error) {
      onToast(`Failed to create conversation: ${error.message}`, 'error');
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteConversation(id, e) {
    e.stopPropagation();
    
    if (!confirm('Are you sure you want to delete this conversation?')) {
      return;
    }

    try {
      await deleteConversation(id);
      await loadConversations();
      
      if (selectedId === id) {
        onSelect(null);
      }
      
      onToast('Conversation deleted', 'success');
    } catch (error) {
      onToast(`Failed to delete conversation: ${error.message}`, 'error');
    }
  }

  function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString();
  }

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1>RAG Chatbot</h1>
        <button
          className="new-conversation-btn"
          onClick={handleNewConversation}
          disabled={loading}
        >
          {loading ? 'Creating...' : '+ New Conversation'}
        </button>
      </div>

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <p style={{ padding: '12px', fontSize: '13px', color: '#666', textAlign: 'center' }}>
            No conversations yet. Create one to get started!
          </p>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${selectedId === conv.id ? 'active' : ''}`}
              onClick={() => onSelect(conv.id)}
            >
              <div className="conversation-title">
                {conv.title || 'New Conversation'}
              </div>
              <div className="conversation-date">
                {formatDate(conv.updated_at)}
              </div>
              {selectedId === conv.id && (
                <div className="conversation-actions">
                  <button
                    className="delete-btn"
                    onClick={(e) => handleDeleteConversation(conv.id, e)}
                  >
                    Delete
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
