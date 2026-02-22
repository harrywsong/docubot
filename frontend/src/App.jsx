import { useState, useEffect } from 'react';
import { MessageSquare, FolderOpen, Settings } from 'lucide-react';
import ChatInterface from './components/ChatInterface';
import ConversationList from './components/ConversationList';
import FolderManagement from './components/FolderManagement';
import ProcessingPanel from './components/ProcessingPanel';
import HealthCheck from './components/HealthCheck';
import Toast from './components/Toast';
import './index.css';

// Import logo - you can replace this with your actual logo file
// Place your logo image in frontend/src/assets/ folder
// Supported formats: .png, .jpg, .svg, .webp
// Example: import logo from './assets/logo.png';
import logo from './assets/logo.png';

function App() {
  const [activeView, setActiveView] = useState('chat');
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [toast, setToast] = useState(null);
  const [healthStatus, setHealthStatus] = useState(null);

  // Show toast notification
  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // Check health on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/health');
        const data = await response.json();
        setHealthStatus(data);
      } catch (error) {
        console.error('Health check failed:', error);
      }
    };
    checkHealth();
  }, []);

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Ambient Background System */}
      <div className="ambient-background">
        {/* Animated gradient blobs */}
        <div className="gradient-blob gradient-blob-1" />
        <div className="gradient-blob gradient-blob-2" />
        <div className="gradient-blob gradient-blob-3" />
        
        {/* Grid overlay */}
        <div className="grid-overlay" />
      </div>

      {/* Main Container */}
      <div className="relative z-10 flex h-screen">
        {/* Sidebar */}
        <aside className="w-80 border-r border-white/[0.06] bg-gradient-to-b from-white/[0.03] to-transparent backdrop-blur-xl flex flex-col">
          {/* Logo/Header */}
          <div className="p-6 border-b border-white/[0.06]">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-indigo-600 flex items-center justify-center shadow-accent-glow overflow-hidden">
                <img 
                  src={logo} 
                  alt="DocuBot Logo" 
                  className="w-full h-full object-cover"
                />
              </div>
              <div>
                <h1 className="text-xl font-semibold gradient-text">DocuBot</h1>
                <p className="text-xs text-foreground-muted">RIASP</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="p-4 space-y-2">
            <button
              onClick={() => setActiveView('chat')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                activeView === 'chat'
                  ? 'bg-white/[0.08] text-foreground shadow-inner-highlight'
                  : 'text-foreground-muted hover:bg-white/[0.05] hover:text-foreground'
              }`}
            >
              <MessageSquare className="w-5 h-5" />
              <span className="font-medium">Chat</span>
            </button>
            
            <button
              onClick={() => setActiveView('folders')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                activeView === 'folders'
                  ? 'bg-white/[0.08] text-foreground shadow-inner-highlight'
                  : 'text-foreground-muted hover:bg-white/[0.05] hover:text-foreground'
              }`}
            >
              <FolderOpen className="w-5 h-5" />
              <span className="font-medium">Documents</span>
            </button>
            
            <button
              onClick={() => setActiveView('processing')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                activeView === 'processing'
                  ? 'bg-white/[0.08] text-foreground shadow-inner-highlight'
                  : 'text-foreground-muted hover:bg-white/[0.05] hover:text-foreground'
              }`}
            >
              <Settings className="w-5 h-5" />
              <span className="font-medium">Processing</span>
            </button>
          </nav>

          {/* Conversation List (only show in chat view) */}
          {activeView === 'chat' && (
            <div className="flex-1 overflow-hidden flex flex-col">
              <div className="px-4 py-3 border-t border-b border-white/[0.06]">
                <h2 className="text-sm font-semibold text-foreground-muted uppercase tracking-wider">
                  Conversations
                </h2>
              </div>
              <div className="flex-1 overflow-y-auto custom-scrollbar">
                <ConversationList
                  selectedConversation={selectedConversation}
                  onSelectConversation={setSelectedConversation}
                  onToast={showToast}
                />
              </div>
            </div>
          )}

          {/* Health Status */}
          <div className="p-4 border-t border-white/[0.06]">
            <HealthCheck status={healthStatus} />
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {activeView === 'chat' && (
            <ChatInterface
              conversationId={selectedConversation}
              onToast={showToast}
            />
          )}
          
          {activeView === 'folders' && (
            <div className="flex-1 overflow-y-auto custom-scrollbar p-8">
              <div className="max-w-4xl mx-auto">
                <div className="mb-8 animate-fade-up">
                  <h2 className="text-4xl font-semibold gradient-text mb-3">
                    Document Management
                  </h2>
                  <p className="text-lg text-foreground-muted">
                    Add folders containing your documents to process and index
                  </p>
                </div>
                <FolderManagement onToast={showToast} />
              </div>
            </div>
          )}
          
          {activeView === 'processing' && (
            <div className="flex-1 overflow-y-auto custom-scrollbar p-8">
              <div className="max-w-4xl mx-auto">
                <div className="mb-8 animate-fade-up">
                  <h2 className="text-4xl font-semibold gradient-text mb-3">
                    Document Processing
                  </h2>
                  <p className="text-lg text-foreground-muted">
                    Process documents to extract and index their content
                  </p>
                </div>
                <ProcessingPanel onToast={showToast} />
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Toast Notifications */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}

export default App;
