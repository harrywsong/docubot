# RAG Chatbot with Vision Processing

A local RAG (Retrieval Augmented Generation) chatbot web application that processes both text documents and images to answer user questions. The system runs entirely on your local machine with no internet connectivity required.

## Features

- 📁 **Folder-Based Document Management**: Specify folders containing your documents
- 📄 **Text Document Processing**: Extract and index content from PDF and TXT files
- 🖼️ **Image Processing with Vision**: Extract information from receipts and invoices using Qwen2.5-VL 7B
- 💬 **ChatGPT-Style Interface**: Modern web interface with conversation management
- 🔍 **Smart Retrieval**: Find relevant information across all your documents
- 📊 **Source Attribution**: See which documents were used to answer each question
- 🔒 **Privacy-First**: All data stays local, no cloud services required
- ⚡ **Incremental Processing**: Only processes new or modified files

## Architecture

- **Backend**: Python with FastAPI, ChromaDB, SQLite
- **Frontend**: React with Vite
- **Vision Model**: Qwen2.5-VL 7B via Ollama
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Vector Store**: ChromaDB for local embedding storage

## Prerequisites

### Required

- **Python 3.8+** with pip
- **Node.js 18+** with npm
- **Ollama** for vision model inference

### Hardware

- **Windows**: NVIDIA GPU with CUDA support (tested on GTX 4080)
- **macOS**: Apple Silicon (M1/M2/M3)

## Quick Start

### 1. Install Ollama and Vision Model

**macOS:**
```bash
brew install ollama
ollama serve
ollama pull qwen2.5-vl:7b
```

**Windows:**
Download from https://ollama.ai and install, then:
```bash
ollama serve
ollama pull qwen2.5-vl:7b
```

### 2. Clone and Setup

```bash
git clone <repository-url>
cd rag-chatbot-with-vision
```

### 3. Install Backend Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

### 5. Start the Application

**Option A: Use startup scripts (recommended)**

Linux/macOS:
```bash
chmod +x start.sh
./start.sh
```

Windows:
```bash
start.bat
```

**Option B: Start manually**

Terminal 1 (Backend):
```bash
source venv/bin/activate
python -m uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

### 6. Access the Application

Open your browser and navigate to:
```
http://localhost:3000
```

## Usage

### 1. Add Folders

- Enter a folder path in the "Watched Folders" section
- Click "Add Folder" to start watching that directory
- Add multiple folders to index documents from different locations

### 2. Process Documents

- Click "Process Documents" to scan and index all files in watched folders
- Processing is incremental - only new or modified files are processed
- View real-time progress updates during processing

### 3. Start Chatting

- Click "+ New Conversation" to create a conversation
- Type your question in the input field
- Press Enter or click "Send" to submit
- View the answer along with source document references

### 4. Manage Conversations

- Select conversations from the sidebar to view history
- Delete conversations you no longer need
- All conversations are persisted across application restarts

## Supported File Types

- **Text Documents**: PDF, TXT
- **Images**: PNG, JPG, JPEG (receipts, invoices)

## API Documentation

The backend API provides comprehensive documentation at:
```
http://127.0.0.1:8000/docs
```

### Key Endpoints

- `POST /api/folders/add` - Add a watched folder
- `DELETE /api/folders/remove` - Remove a watched folder
- `GET /api/folders/list` - List all watched folders
- `POST /api/process/start` - Start document processing
- `GET /api/process/status` - Get processing status
- `WS /api/process/stream` - WebSocket for real-time updates
- `POST /api/conversations/create` - Create new conversation
- `GET /api/conversations/list` - List all conversations
- `GET /api/conversations/:id` - Get conversation with messages
- `DELETE /api/conversations/:id` - Delete conversation
- `POST /api/query` - Submit a question
- `GET /api/health` - System health check

## Project Structure

```
rag-chatbot-with-vision/
├── backend/                 # Python backend
│   ├── api.py              # FastAPI application
│   ├── config.py           # Configuration
│   ├── database.py         # SQLite database manager
│   ├── models.py           # Data models
│   ├── folder_manager.py   # Folder management
│   ├── text_processor.py   # Text extraction and chunking
│   ├── image_processor.py  # Image processing with vision model
│   ├── ollama_client.py    # Ollama API client
│   ├── embedding_engine.py # Embedding generation
│   ├── vector_store.py     # ChromaDB wrapper
│   ├── processing_state.py # Processing state tracking
│   ├── document_processor.py # Document processing orchestrator
│   ├── conversation_manager.py # Conversation management
│   └── query_engine.py     # Query processing and RAG
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── api.js        # API client
│   │   ├── App.jsx       # Main app component
│   │   └── main.jsx      # Entry point
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── tests/                 # Test suite
├── data/                  # Local data storage
│   ├── chromadb/         # Vector embeddings
│   └── rag_chatbot.db    # SQLite database
├── requirements.txt       # Python dependencies
├── start.sh              # Linux/macOS startup script
├── start.bat             # Windows startup script
└── README.md             # This file
```

## Development

### Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest

# Run with coverage
pytest --cov=backend tests/

# Run specific test file
pytest tests/test_api.py
```

### Backend Development

The backend uses FastAPI with automatic reload:
```bash
python -m uvicorn backend.api:app --reload --host 127.0.0.1 --port 8000
```

### Frontend Development

The frontend uses Vite with hot module replacement:
```bash
cd frontend
npm run dev
```

## Troubleshooting

### Ollama Not Running

**Error**: "Ollama is not running"

**Solution**:
```bash
ollama serve
```

### Model Not Found

**Error**: "Qwen2.5-VL 7B model not found"

**Solution**:
```bash
ollama pull qwen2.5-vl:7b
```

### Port Already in Use

**Backend (8000)**:
```bash
# Find and kill process using port 8000
lsof -ti:8000 | xargs kill -9  # macOS/Linux
netstat -ano | findstr :8000   # Windows
```

**Frontend (3000)**: Vite will automatically use the next available port

### Database Locked

If you see "database is locked" errors, ensure only one backend instance is running.

### WebSocket Connection Failed

Check that:
1. Backend is running on port 8000
2. No firewall is blocking WebSocket connections
3. Browser console for specific error messages

## Performance

- **Image Processing**: <5s on GTX 4080, <10s on Apple Silicon
- **Query Response**: <5s on GTX 4080, <10s on Apple Silicon
- **Folder Scanning**: <1s per 100 files
- **Embedding Generation**: <2s per 100 chunks

## Privacy & Security

- All data processing happens locally on your machine
- No internet connectivity required (except for initial Ollama model download)
- No authentication or user accounts
- All sensitive information remains on your local storage
- Documents and conversations are stored in the `data/` directory

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues and questions:
- Check the troubleshooting section above
- Review API documentation at http://127.0.0.1:8000/docs
- Check backend logs for detailed error messages
- Verify Ollama is running and model is installed

## Acknowledgments

- **Ollama**: Local LLM inference platform
- **Qwen2.5-VL**: Vision-language model by Alibaba Cloud
- **ChromaDB**: Vector database for embeddings
- **FastAPI**: Modern Python web framework
- **React**: Frontend UI library
- **Vite**: Fast frontend build tool
