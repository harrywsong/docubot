# Configuration Checklist ✓

## Models Installed ✓

All required models have been pulled:

```
✓ mxbai-embed-large (669 MB)
✓ qwen2.5vl:7b (6 GB)  
✓ qwen2.5:14b (9 GB)
```

## Configuration Files Updated ✓

### backend/config.py ✓
```python
OLLAMA_MODEL = "qwen2.5:14b"              # Text generation
OLLAMA_VISION_MODEL = "qwen2.5vl:7b"      # Vision processing
EMBEDDING_MODEL = "mxbai-embed-large"     # Embeddings (1024-dim)
CONVERSATIONAL_MODEL = "qwen2.5:3b"       # For Pi export
```

### backend/api.py ✓
- Vision client now uses `Config.OLLAMA_VISION_MODEL`
- Separate clients for text generation and vision processing
- Embedding engine uses `Config.EMBEDDING_MODEL`

### backend/embedding_engine.py ✓
- Supports Ollama API for embeddings
- Falls back to sentence-transformers if Ollama unavailable
- Auto-detects embedding dimensions
- Includes retry logic and error handling

## System Architecture

```
Desktop (RTX 4080):
├── Document Processing
│   ├── Text Extraction
│   ├── Vision Processing (qwen2.5vl:7b)
│   └── Embedding Generation (mxbai-embed-large)
├── Vector Store (ChromaDB)
├── Database (SQLite)
└── Export Package Creation

Raspberry Pi:
├── Load Pre-computed Data
├── Query Processing
│   ├── Embedding Generation (mxbai-embed-large)
│   └── Response Generation (qwen2.5:3b)
└── Web Interface
```

## Ready to Test

Your system is now configured and ready for testing. Follow these steps:

1. **Start Ollama**: `ollama serve`
2. **Start Backend**: `python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000`
3. **Open Browser**: `http://localhost:3000`
4. **Add Folder**: Select a folder with documents
5. **Process**: Click "Process Documents"
6. **Query**: Ask questions about your documents

See `TESTING_GUIDE.md` for detailed testing instructions.

## Model Capabilities

### qwen2.5vl:7b (Vision)
- Best open-source vision model for 2025
- Processes images, receipts, IDs, legal documents
- Extracts structured data automatically
- Handles orientation issues

### qwen2.5:14b (Text Generation)
- High-quality text generation
- Good for complex reasoning
- Optimized for RTX 4080

### mxbai-embed-large (Embeddings)
- 1024-dimensional embeddings
- Beats OpenAI models on benchmarks
- Must be same on desktop and Pi

### qwen2.5:3b (Pi Conversational)
- Lightweight for Raspberry Pi
- 2-3GB RAM usage
- Good quality for conversational responses

## Next Steps

1. Test document processing on desktop
2. Verify GPU utilization with `nvidia-smi`
3. Test querying and responses
4. Export data for Pi deployment
5. Transfer to Raspberry Pi
6. Test on Pi with lightweight model

## Troubleshooting

If you encounter issues:

1. Check Ollama is running: `ollama list`
2. Verify models are loaded: `ollama ps`
3. Check server logs for errors
4. Monitor GPU with `nvidia-smi -l 1`
5. Check `TESTING_GUIDE.md` for common issues
