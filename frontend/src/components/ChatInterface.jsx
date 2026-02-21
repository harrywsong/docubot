import { useState, useEffect, useRef } from 'react';
import { getConversation, submitQuery } from '../api';

export default function ChatInterface({ conversationId, onToast }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationTitle, setConversationTitle] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (conversationId) {
      loadConversation();
    } else {
      setMessages([]);
      setConversationTitle('');
    }
  }, [conversationId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  function scrollToBottom() {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }

  async function loadConversation() {
    try {
      const response = await getConversation(conversationId);
      setMessages(response.conversation.messages);
      setConversationTitle(response.conversation.title || 'New Conversation');
    } catch (error) {
      onToast(error.message, 'error');
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!input.trim() || !conversationId || loading) return;

    const question = input.trim();
    setInput('');
    setLoading(true);

    // Optimistically add user message
    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: question,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await submitQuery(conversationId, question);
      
      // Add assistant response
      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        created_at: new Date().toISOString()
      };
      
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      onToast(error.message, 'error');
      // Remove optimistic user message on error
      setMessages(prev => prev.filter(m => m.id !== userMessage.id));
    } finally {
      setLoading(false);
    }
  }

  if (!conversationId) {
    return (
      <div className="chat-area">
        <div className="empty-state">
          <h3>No conversation selected</h3>
          <p>Create or select a conversation to start chatting</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-area">
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-state">
            <h3>Start a conversation</h3>
            <p>Ask questions about your documents</p>
          </div>
        ) : (
          messages.map((message) => (
            <div key={message.id} className={`message ${message.role}`}>
              <div className="message-role">{message.role}</div>
              <div className="message-content">{message.content}</div>
              
              {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                <div className="message-sources">
                  <h4>Sources</h4>
                  {message.sources.map((source, idx) => (
                    <div key={idx} className="source-item">
                      <div className="source-filename">
                        {source.metadata?.filename || 'Unknown file'}
                      </div>
                      <div className="source-content">
                        {source.content?.substring(0, 100)}...
                      </div>
                      <div className="source-score">
                        Relevance: {(source.score * 100).toFixed(1)}%
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
        
        {loading && (
          <div className="message assistant">
            <div className="message-role">assistant</div>
            <div className="message-content">
              <span className="loading"></span> Thinking...
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        <form onSubmit={handleSubmit} className="input-form">
          <textarea
            className="message-input"
            placeholder="Ask a question about your documents..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            rows={1}
            disabled={loading}
          />
          <button
            type="submit"
            className="send-btn"
            disabled={!input.trim() || loading}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
