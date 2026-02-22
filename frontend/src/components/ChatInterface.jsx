import { useState, useEffect, useRef } from 'react';
import { Send, Folder, ChevronDown, ChevronUp } from 'lucide-react';
import { getConversation, submitQuery, openFolder } from '../api';

export default function ChatInterface({ conversationId, onToast }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [expandedSources, setExpandedSources] = useState({});
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    if (conversationId) {
      loadConversation();
    } else {
      setMessages([]);
    }
  }, [conversationId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Auto-resize textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [input]);

  function scrollToBottom() {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }

  async function loadConversation() {
    try {
      const response = await getConversation(conversationId);
      setMessages(response.conversation.messages);
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

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: question,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await submitQuery(conversationId, question);
      
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
      setMessages(prev => prev.filter(m => m.id !== userMessage.id));
    } finally {
      setLoading(false);
    }
  }

  function toggleSources(messageId) {
    setExpandedSources(prev => ({
      ...prev,
      [messageId]: !prev[messageId]
    }));
  }

  if (!conversationId) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center animate-fade-up">
          <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-accent/20 to-indigo-600/20 flex items-center justify-center border border-accent/30">
            <Send className="w-10 h-10 text-accent" />
          </div>
          <h3 className="text-2xl font-semibold gradient-text mb-2">No conversation selected</h3>
          <p className="text-foreground-muted">Create or select a conversation to start chatting</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center animate-fade-up">
              <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-accent/20 to-indigo-600/20 flex items-center justify-center border border-accent/30">
                <Send className="w-10 h-10 text-accent" />
              </div>
              <h3 className="text-2xl font-semibold gradient-text mb-2">Start a conversation</h3>
              <p className="text-foreground-muted">Ask questions about your documents</p>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message, idx) => (
              <div
                key={message.id}
                className="animate-fade-up"
                style={{ animationDelay: `${idx * 50}ms` }}
              >
                {/* Message */}
                <div className={`flex gap-4 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-3xl ${message.role === 'user' ? 'order-2' : 'order-1'}`}>
                    {/* Role Badge */}
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs font-mono uppercase tracking-widest text-foreground-muted">
                        {message.role}
                      </span>
                      <div className="h-px flex-1 bg-gradient-to-r from-white/10 to-transparent" />
                    </div>
                    
                    {/* Content */}
                    <div className={`glass-card p-4 ${
                      message.role === 'user' 
                        ? 'bg-gradient-to-br from-accent/10 to-accent/5 border-accent/20' 
                        : ''
                    }`}>
                      <p className="text-foreground leading-relaxed whitespace-pre-wrap">
                        {message.content}
                      </p>
                    </div>

                    {/* Sources - Show top 3 with expand option */}
                    {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                      <div className="mt-3">
                        <button
                          onClick={() => toggleSources(message.id)}
                          className="flex items-center gap-2 text-xs text-foreground-muted hover:text-foreground transition-colors mb-2"
                        >
                          {expandedSources[message.id] ? (
                            <ChevronUp className="w-3 h-3" />
                          ) : (
                            <ChevronDown className="w-3 h-3" />
                          )}
                          <span className="uppercase tracking-wider font-semibold">
                            Sources ({message.sources.length})
                          </span>
                        </button>
                        
                        {expandedSources[message.id] && (
                          <div className="space-y-2">
                            {message.sources.slice(0, 3).map((source, idx) => (
                              <div key={idx} className="glass-card p-3 text-sm">
                                <div className="flex items-center justify-between mb-2">
                                  <span className="font-medium text-foreground text-xs">
                                    {source.filename || source.metadata?.filename || 'Unknown file'}
                                  </span>
                                  {source.metadata?.folder_path && (
                                    <button
                                      onClick={async () => {
                                        try {
                                          await openFolder(source.metadata.folder_path);
                                          onToast('Opened folder location', 'success');
                                        } catch (error) {
                                          onToast(`Failed to open folder: ${error.message}`, 'error');
                                        }
                                      }}
                                      className="btn-ghost text-xs py-1 px-2"
                                      title="Open folder location"
                                    >
                                      <Folder className="w-3 h-3 inline mr-1" />
                                      Open
                                    </button>
                                  )}
                                </div>
                                <p className="text-foreground-muted text-xs mb-2 line-clamp-2">
                                  {source.chunk?.substring(0, 150) || source.content?.substring(0, 150)}...
                                </p>
                                <div className="flex items-center gap-2">
                                  <div className="h-1 flex-1 bg-white/5 rounded-full overflow-hidden">
                                    <div 
                                      className="h-full bg-gradient-to-r from-accent to-indigo-500"
                                      style={{ width: `${(source.score || 0) * 100}%` }}
                                    />
                                  </div>
                                  <span className="text-xs text-foreground-muted">
                                    {((source.score || 0) * 100).toFixed(0)}%
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            
            {loading && (
              <div className="flex gap-4 animate-fade-up">
                <div className="max-w-3xl">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-mono uppercase tracking-widest text-foreground-muted">
                      assistant
                    </span>
                    <div className="h-px flex-1 bg-gradient-to-r from-white/10 to-transparent" />
                  </div>
                  <div className="glass-card p-4">
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />
                        <div className="w-2 h-2 rounded-full bg-accent animate-pulse animation-delay-100" />
                        <div className="w-2 h-2 rounded-full bg-accent animate-pulse animation-delay-200" />
                      </div>
                      <span className="text-foreground-muted">Thinking...</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-white/[0.06] bg-gradient-to-b from-transparent to-white/[0.02] backdrop-blur-xl p-6">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
          <div className="glass-card p-2 flex items-end gap-2">
            <textarea
              ref={textareaRef}
              className="flex-1 bg-transparent border-none outline-none text-foreground placeholder-foreground-subtle resize-none px-3 py-2"
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
              style={{ minHeight: '40px', maxHeight: '200px' }}
            />
            <button
              type="submit"
              className="btn-primary px-4 py-2 disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
              disabled={!input.trim() || loading}
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-foreground-subtle mt-2 text-center">
            Press Enter to send, Shift+Enter for new line
          </p>
        </form>
      </div>
    </div>
  );
}
