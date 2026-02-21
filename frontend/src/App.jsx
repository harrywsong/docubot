import { useState } from 'react';
import './App.css';
import ConversationList from './components/ConversationList';
import ChatInterface from './components/ChatInterface';
import FolderManagement from './components/FolderManagement';
import ProcessingPanel from './components/ProcessingPanel';
import HealthCheck from './components/HealthCheck';
import Toast from './components/Toast';

export default function App() {
  const [selectedConversationId, setSelectedConversationId] = useState(null);
  const [toasts, setToasts] = useState([]);

  function showToast(message, type = 'info') {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
  }

  function removeToast(id) {
    setToasts(prev => prev.filter(t => t.id !== id));
  }

  return (
    <div className="app">
      <ConversationList
        selectedId={selectedConversationId}
        onSelect={setSelectedConversationId}
        onToast={showToast}
      />

      <div className="main-content">
        <div className="main-header">
          <h2>Document Management</h2>
          
          <HealthCheck />
          
          <FolderManagement onToast={showToast} />
          
          <ProcessingPanel onToast={showToast} />
        </div>

        <ChatInterface
          conversationId={selectedConversationId}
          onToast={showToast}
        />
      </div>

      <div className="toast-container">
        {toasts.map(toast => (
          <Toast
            key={toast.id}
            message={toast.message}
            type={toast.type}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </div>
    </div>
  );
}
