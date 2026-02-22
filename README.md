# DocuBot - Multilingual RAG Chatbot with Vision Processing

A privacy-focused RAG (Retrieval Augmented Generation) chatbot that processes documents and images to answer questions in multiple languages. Designed for local deployment with excellent Korean-English cross-lingual support.

## Features

- 🌏 **Multilingual Support**: Native Korean and English support with cross-lingual semantic search
- 📁 **Smart Document Management**: Folder-based organization with incremental processing
- 🖼️ **Vision Processing**: Extract structured data from receipts, invoices, and documents using qwen3-vl:8b
- 💬 **Modern Chat Interface**: ChatGPT-style conversation management
- 🔍 **Semantic Search**: Find relevant information across documents regardless of language
- 📊 **Source Attribution**: See which documents were used for each answer
- 🔒 **Privacy-First**: All data stays local, no cloud services required
- ⚡ **Optimized Performance**: Fast embedding generation and query processing

## Architecture

### Core Stack
- **Backend**: Python with FastAPI, ChromaDB, SQLite
- **Frontend**: React with Vite
- **Embedding Model**: qwen3-embedding:8b (4096-dim, multilingual)
- **Conversational Model**: qwen2.5:7b (better reading comprehension)
- **Vision Model**: qwen3-vl:8b (document extraction)
- **Vector Store**: ChromaDB for persistent embeddings

### Key Design Decisions
- **Multilingual Embeddings**: qwen3-embedding:8b supports Korean, English, Chinese, and 100+ languages
- **Flexible Metadata**: No hardcoded fields - vision model dynamically extracts document-specific data
- **Split Architecture**: Separate models for embedding, conversation, and vision processing
- **Raspberry Pi Ready**: Optimized for deployment on Pi 5 (8GB RAM)

## Quick Start

> **New User?** See [QUICK_START.md](QUICK_START.md) for the simplest way to get started!

### Prerequisites

- **Python 3.10+** with pip
- **Node.js 18+** with npm
- **Ollama** with required models:
  - `qwen3-embedding:8b` - Multilingual embedding model (4096-dim)
  - `qwen2.5:7b` - Conversational model for response generation
  - `qwen3-vl:8b` - Vision model for image/document processing

### Installation

1. **Install Ollama and pull the required models:**
   ```bash
   # macOS
   brew install ollama
   
   # Windows: Download from https://ollama.ai
   
   # Start Ollama and pull models
   ollama serve
   ollama pull qwen3-embedding:8b
   ollama pull qwen2.5:7b
   ollama pull qwen3-vl:8b
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
   scripts\start.bat
   
   # macOS/Linux
   ./scripts/start.sh
   ```

4. **Open your browser:** http://localhost:5173

5. **Stop the application:**
   ```bash
   # Windows
   scripts\stop.bat
   
   # macOS/Linux
   ./scripts/stop.sh
   ```

## Usage

1. **Add folders** containing your documents (PDFs, text files, images)
2. **Click "Process Documents"** to index your files
3. **Create a conversation** and start asking questions
4. **View sources** to see which documents were used for each answer

For detailed usage instructions, see the in-app help or [QUICK_START.md](QUICK_START.md).

## Supported File Types

- **Text Documents**: PDF, TXT
- **Images**: PNG, JPG, JPEG, GIF, BMP, TIFF, WEBP
- **Document Types**: Receipts, invoices, ID cards, legal documents, forms

## Multilingual Support

The system is optimized for Korean-English bilingual use:
- **Query in Korean**: "2월에 코스트코에서 얼마나 썼어?"
- **Query in English**: "How much did I spend at Costco in February?"
- **Documents in any language**: Automatically extracts and indexes content
- **Cross-lingual search**: Korean queries can find English documents and vice versa

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
docubot/
├── backend/                    # Python backend
│   ├── api.py                 # FastAPI application
│   ├── config.py              # Configuration management
│   ├── database.py            # SQLite database manager
│   ├── models.py              # Data models
│   ├── folder_manager.py      # Folder management
│   ├── text_processor.py      # Text extraction and chunking
│   ├── image_processor.py     # Vision-based document extraction
│   ├── ollama_client.py       # Ollama API client
│   ├── embedding_engine.py    # Multilingual embedding generation
│   ├── vector_store.py        # ChromaDB wrapper
│   ├── document_processor.py  # Document processing orchestrator
│   ├── conversation_manager.py # Conversation management
│   ├── llm_generator.py       # LLM response generation
│   └── query_engine.py        # RAG query processing
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── api.js            # API client
│   │   ├── App.jsx           # Main app component
│   │   └── main.jsx          # Entry point
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── scripts/                    # Utility scripts
│   ├── test_*.py              # Testing scripts
│   ├── check_*.py             # Diagnostic scripts
│   └── migrate_*.py           # Migration scripts
├── tests/                      # Test suite
├── docs/                       # Documentation
│   ├── DEPLOYMENT.md          # Deployment guide
│   ├── PERFORMANCE_ANALYSIS.md # Performance metrics
│   └── SPLIT_ARCHITECTURE.md  # Architecture details
├── data/                       # Local data storage
│   ├── chromadb/              # Vector embeddings
│   └── app.db                 # SQLite database
├── requirements.txt            # Python dependencies
└── README.md                   # This file
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
| "Model not found" | Run `ollama pull qwen2.5vl:7b` |
| Port already in use | Run the stop script first |
| Browser doesn't open | Manually go to http://localhost:5173 |

For more troubleshooting help, see [QUICK_START.md](QUICK_START.md).

## Performance

### Desktop (NVIDIA RTX 4080)
- Vision Processing: 2-5s per image
- Embedding Generation: <1s per document
- Query Response: 3-8s

### Raspberry Pi 5 (8GB RAM)
- Vision Processing: Not recommended (use desktop for processing)
- Embedding Generation: 2-3s per document
- Query Response: 15-25s with qwen2.5:7b

### Optimization Tips
- Use desktop for initial document processing
- Export processed data to Pi for querying
- qwen2.5:7b provides good balance of speed and quality on Pi
- Consider qwen2.5:3b for faster responses (lower quality)

## Privacy & Security

- All processing happens locally on your machine
- No internet connectivity required (except initial model download)
- All data stored in local `data/` directory
- No authentication or user accounts needed

## Acknowledgments

- [Ollama](https://ollama.ai) - Local LLM inference
- [Qwen](https://github.com/QwenLM) - Qwen2.5 and Qwen3 model families
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [FastAPI](https://fastapi.tiangolo.com/) - Python web framework
- [React](https://react.dev/) - Frontend framework
- [Vite](https://vitejs.dev/) - Build tool

## License

MIT License - See LICENSE file for details
