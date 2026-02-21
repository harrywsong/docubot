# RAG Chatbot Frontend

Modern React-based web interface for the RAG chatbot with vision processing.

## Features

- **Folder Management**: Add and remove folders to watch for documents
- **Document Processing**: Trigger processing with real-time progress updates
- **Conversation Management**: Create, view, and delete conversations
- **Chat Interface**: ChatGPT-style interface with message history
- **Source Attribution**: View source documents for each answer
- **Health Monitoring**: System health check with dependency status
- **Error Handling**: User-friendly error messages and toast notifications

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start development server:
```bash
npm run dev
```

The frontend will be available at http://localhost:3000

## Build for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## Architecture

- **React 18**: Modern React with hooks
- **Vite**: Fast build tool and dev server
- **Vanilla CSS**: No CSS framework dependencies
- **WebSocket**: Real-time processing updates
- **REST API**: Communication with FastAPI backend

## Components

- `App.jsx`: Main application component
- `ConversationList.jsx`: Sidebar with conversation list
- `ChatInterface.jsx`: Chat message display and input
- `FolderManagement.jsx`: Folder add/remove UI
- `ProcessingPanel.jsx`: Document processing controls
- `HealthCheck.jsx`: System health status display
- `Toast.jsx`: Toast notification component

## API Integration

The frontend communicates with the backend API at `http://127.0.0.1:8000/api`.

All API calls are handled through `src/api.js` which provides:
- Folder management endpoints
- Document processing endpoints
- Conversation CRUD operations
- Query submission
- Health check
- WebSocket connection for real-time updates
