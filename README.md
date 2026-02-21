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

## Quick Start

> **New User?** See [QUICK_START.md](QUICK_START.md) for the simplest way to get started!

### Prerequisites

- **Python 3.10+** with pip
- **Node.js 18+** with npm
- **Ollama** with qwen2.5-vl:7b model

### Installation

1. **Install Ollama and the vision model:**
   ```bash
   # macOS
   brew install ollama
   
   # Windows: Download from https://ollama.ai
   
   # Then pull the model
   ollama serve
   ollama pull qwen2.5-vl:7b
   ```

2. **Install dependencies:**
   ```bash
   # Backend
   pip install -r requirements.txt
   
   # Frontend
   cd frontend
   npm install
   cd ..
   ```

3. **Start the application:**
   ```bash
   # Windows
   start.bat
   
   # macOS/Linux
   ./start.sh
   ```

4. **Open your browser:** http://localhost:5173

5. **Stop the application:**
   ```bash
   # Windows
   stop.bat
   
   # macOS/Linux
   ./stop.sh
   ```

## Usage

1. **Add folders** containing your documents (PDFs, text files, images)
2. **Click "Process Documents"** to index your files
3. **Create a conversation** and start asking questions
4. **View sources** to see which documents were used for each answer

For detailed usage instructions, see the in-app help or [QUICK_START.md](QUICK_START.md).

## Supported File Types

- **Text Documents**: PDF, TXT
- **Images**: PNG, JPG, JPEG (receipts, invoices)

## API Documentation

Full API documentation is available at http://localhost:8000/docs when the backend is running.

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/folders/add` | POST | Add a watched folder |
| `/api/folders/remove` | DELETE | Remove a watched folder |
| `/api/folders/list` | GET | List all watched folders |
| `/api/process/start` | POST | Start document processing |
| `/api/process/status` | GET | Get processing status |
| `/api/conversations/create` | POST | Create new conversation |
| `/api/conversations/list` | GET | List all conversations |
| `/api/query` | POST | Submit a question |
| `/api/health` | GET | System health check |

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
├── start.sh              # macOS/Linux startup script
├── start.bat             # Windows startup script
├── stop.sh               # macOS/Linux shutdown script
├── stop.bat              # Windows shutdown script
└── README.md             # This file
```

## Development

### Running Tests
```bash
pytest                          # Run all tests
pytest --cov=backend tests/     # Run with coverage
pytest tests/test_api.py        # Run specific test file
```

### Development Mode
```bash
# Backend with auto-reload
python -m uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000

# Frontend with hot reload
cd frontend
npm run dev
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Ollama is not running" | Run `ollama serve` in a terminal |
| "Model not found" | Run `ollama pull qwen2.5-vl:7b` |
| Port already in use | Run the stop script first |
| Browser doesn't open | Manually go to http://localhost:5173 |

For more troubleshooting help, see [QUICK_START.md](QUICK_START.md).

## Performance

- Image Processing: <5s on GTX 4080, <10s on Apple Silicon
- Query Response: <5s on GTX 4080, <10s on Apple Silicon

## Privacy & Security

- All processing happens locally on your machine
- No internet connectivity required (except initial model download)
- All data stored in local `data/` directory
- No authentication or user accounts needed

## Acknowledgments

- [Ollama](https://ollama.ai) - Local LLM inference
- [Qwen2.5-VL](https://github.com/QwenLM/Qwen2-VL) - Vision-language model
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [FastAPI](https://fastapi.tiangolo.com/) - Python web framework
- [React](https://react.dev/) - Frontend framework
- [Vite](https://vitejs.dev/) - Build tool
