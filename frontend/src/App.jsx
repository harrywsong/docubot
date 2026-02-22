import { useState, useEffect } from 'react';
import { MessageSquare, FolderOpen, LogOut } from 'lucide-react';
import ChatInterface from './components/ChatInterface';
import ConversationList from './components/ConversationList';
import DocumentManager from './components/DocumentManager';
import HealthCheck from './components/HealthCheck';
import Toast from './components/Toast';
import LoginScreen from './components/LoginScreen';
import './index.css';

// Import logo - you can replace this with your actual logo file
// Place your logo image in frontend/src/assets/ folder
// Supported formats: .png, .jpg, .svg, .webp
// Example: import logo from './assets/logo.png';
import logo from './assets/logo.png';

function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [activeView, setActiveView] = useState('chat');
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [toast, setToast] = useState(null);
  const [healthStatus, setHealthStatus] = useState(null);

  // Check for stored user on mount
  useEffect(() => {
    const storedUser = localStorage.getItem('currentUser');
    if (storedUser) {
      try {
        setCurrentUser(JSON.parse(storedUser));
      } catch (error) {
        console.error('Failed to parse stored user:', error);
        localStorage.removeItem('currentUser');
      }
    }
  }, []);

  // Show toast notification
  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // Handle login
  const handleLogin = (user) => {
    setCurrentUser(user);
    showToast(`Welcome back, ${user.username}!`, 'success');
  };

  // Handle logout
  const handleLogout = () => {
    localStorage.removeItem('currentUser');
    setCurrentUser(null);
    setSelectedConversation(null);
    showToast('Logged out successfully', 'info');
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

  // Show login screen if no user is logged in
  if (!currentUser) {
    return (
      <>
        <LoginScreen onLogin={handleLogin} />
        {toast && (
          <Toast
            message={toast.message}
            type={toast.type}
            onClose={() => setToast(null)}
          />
        )}
      </>
    );
  }

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
              onClick={() => setActiveView('documents')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                activeView === 'documents'
                  ? 'bg-white/[0.08] text-foreground shadow-inner-highlight'
                  : 'text-foreground-muted hover:bg-white/[0.05] hover:text-foreground'
              }`}
            >
              <FolderOpen className="w-5 h-5" />
              <span className="font-medium">Documents</span>
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
                  userId={currentUser.id}
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

          {/* User Profile with Logout */}
          <div className="p-4 border-t border-white/[0.06]">
            <div className="glass-card p-4">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-accent to-indigo-600 flex items-center justify-center flex-shrink-0">
                  {currentUser.profile_picture ? (
                    <img 
                      src={`/assets/profiles/${currentUser.profile_picture}`} 
                      alt={currentUser.username}
                      className="w-full h-full object-cover rounded-lg"
                    />
                  ) : (
                    <span className="text-white font-semibold">
                      {currentUser.username.charAt(0).toUpperCase()}
                    </span>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-foreground truncate">
                    {currentUser.username}
                  </p>
                  <p className="text-xs text-foreground-muted">
                    Logged in
                  </p>
                </div>
              </div>
              <button
                onClick={handleLogout}
                className="w-full btn-ghost text-sm py-2 flex items-center justify-center gap-2"
              >
                <LogOut className="w-4 h-4" />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {activeView === 'chat' && (
            <ChatInterface
              conversationId={selectedConversation}
              userId={currentUser.id}
              onToast={showToast}
            />
          )}
          
          {activeView === 'documents' && (
            <div className="flex-1 overflow-y-auto custom-scrollbar p-8">
              <div className="max-w-4xl mx-auto">
                <div className="mb-8 animate-fade-up">
                  <h2 className="text-4xl font-semibold gradient-text mb-3">
                    Documents
                  </h2>
                  <p className="text-lg text-foreground-muted">
                    Manage your folders and process documents
                  </p>
                </div>
                <DocumentManager userId={currentUser.id} onToast={showToast} />
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
