# Quick Start Guide - Desktop-Pi RAG Pipeline

## TL;DR

**Desktop (RTX 4080)**: Process documents with 14b model → Export → Transfer to Pi  
**Raspberry Pi**: Load data → Serve queries with 3b model

---

## Prerequisites

### Desktop (Your PC)
- Python 3.10+
- Ollama with models: `qwen2.5:14b`, `qwen2.5vl:7b`
- NVIDIA GPU (RTX 4080)

### Raspberry Pi
- Raspberry Pi 4 (4GB+ RAM)
- Python 3.10+
- Ollama with model: `qwen2.5:3b`

---

## Installation

### 1. Install Ollama

**Desktop:**
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull embedding model (best for RAG)
ollama pull mxbai-embed-large

# Pull vision model (best for images/documents)
ollama pull qwen2.5vl:7b

# Optional: Pull text generation model for testing
ollama pull qwen2.5:14b
```

**Raspberry Pi:**
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull lightweight conversational model
ollama pull qwen2.5:3b

# Pull embedding model (must match desktop)
ollama pull mxbai-embed-large
```

### 2. Install Python Dependencies

**Both systems:**
```bash
pip install -r requirements.txt
```

---

## Usage - 3 Simple Steps

### Step 1: Process on Desktop

```bash
# 1. Start server
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000

# 2. Add your documents folder (via web UI or API)
# Open http://localhost:8000 and add folders

# 3. Run the export script
chmod +x scripts/desktop_export.sh
./scripts/desktop_export.sh
```

**What this does:**
- Processes all documents with GPU acceleration
- Generates high-quality embeddings (14b model)
- Creates export package
- Transfers to your Pi

### Step 2: Setup on Pi

```bash
# SSH into your Pi
ssh pi@raspberrypi.local

# Extract the package
tar -xzf pi_export_*.tar.gz
cd pi_export_*

# Run setup script
chmod +x setup_pi.sh
./setup_pi.sh
```

**What this does:**
- Copies data to correct locations
- Configures Pi settings
- Validates everything is ready
- Optionally creates systemd service

### Step 3: Use the System

Access from any device on your network:
```
http://raspberrypi.local:8000
```

Or use the Pi's IP address:
```
http://192.168.1.100:8000
```

**That's it!** Ask questions and get AI-powered answers from your documents.

---

## Configuration

### Desktop Config (`backend/config.py`)

```python
ENABLE_DOCUMENT_PROCESSING = True  # Enable processing
EMBEDDING_MODEL = "mxbai-embed-large"  # Best embedding model (1024-dim)
OLLAMA_VISION_MODEL = "qwen2.5vl:7b"  # Best vision model
OLLAMA_MODEL = "qwen2.5:14b"  # For testing (optional)
```

### Pi Config (auto-generated in export)

```python
ENABLE_DOCUMENT_PROCESSING = False  # Disable processing
OLLAMA_MODEL = "qwen2.5:3b"  # Lightweight conversational model
EMBEDDING_MODEL = "mxbai-embed-large"  # Must match desktop (1024-dim)
```

---

## Adding New Documents (Incremental Update)

When you add new documents, you don't need to re-export everything:

**Desktop:**
```bash
# Process new documents
curl -X POST http://localhost:8000/api/process

# Create incremental export
./scripts/desktop_export.sh incremental
```

**Pi:**
```bash
# Extract incremental package
tar -xzf pi_export_incremental_*.tar.gz

# Merge with existing data
curl -X POST http://localhost:8000/api/data/merge \
  -H "Content-Type: application/json" \
  -d '{"package_path": "pi_export_incremental"}'

# Restart server
sudo systemctl restart rag-chatbot
```

---

## Manual Commands

### Desktop

```bash
# Start server
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000

# Add folder
curl -X POST http://localhost:8000/api/folders \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/documents"}'

# Process documents
curl -X POST http://localhost:8000/api/process

# Validate
curl http://localhost:8000/api/processing/report

# Export
curl -X POST http://localhost:8000/api/export \
  -H "Content-Type: application/json" \
  -d '{"incremental": false}'

# Transfer to Pi
scp pi_export_*.tar.gz pi@raspberrypi.local:~/
```

### Raspberry Pi

```bash
# Start server
cd ~/rag-chatbot
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000

# Or with systemd
sudo systemctl start rag-chatbot

# Check health
curl http://localhost:8000/api/health

# Check stats
curl http://localhost:8000/api/data/stats

# View logs
tail -f logs/app.log
# Or with systemd
sudo journalctl -u rag-chatbot -f
```

---

## Troubleshooting

### Desktop Issues

**Processing is slow:**
- Check GPU usage: `nvidia-smi`
- Verify Ollama is using GPU
- Reduce batch size

**Export fails:**
- Check disk space: `df -h`
- Validate processing first: `curl http://localhost:8000/api/processing/report`

### Pi Issues

**Server won't start:**
- Check Ollama: `systemctl status ollama`
- Verify model: `ollama list`
- Check data files exist in `~/rag-chatbot/data/`

**Queries are slow:**
- Check memory: `free -h`
- Consider using `qwen2.5:1.5b` instead of 3b
- Use SSD instead of microSD card

**Out of memory:**
- Restart Pi: `sudo reboot`
- Use smaller model: `ollama pull qwen2.5:1.5b`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Desktop (RTX 4080)                       │
├─────────────────────────────────────────────────────────────┤
│  1. Add documents to watched folders                        │
│  2. Process with qwen2.5:14b (GPU accelerated)             │
│  3. Generate embeddings (384-dim)                           │
│  4. Store in ChromaDB + SQLite                              │
│  5. Create export package                                   │
│  6. Transfer to Pi                                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Transfer (SCP/rsync)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Raspberry Pi                             │
├─────────────────────────────────────────────────────────────┤
│  1. Load ChromaDB (read-only)                               │
│  2. Load SQLite (read-only)                                 │
│  3. Serve web interface                                     │
│  4. Process queries with qwen2.5:3b (CPU)                  │
│  5. Return AI-generated responses                           │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
rag-chatbot/
├── backend/
│   ├── api.py              # FastAPI server
│   ├── config.py           # Configuration (different for desktop/Pi)
│   ├── vector_store.py     # ChromaDB interface
│   ├── export_manager.py   # Desktop export functionality
│   ├── data_loader.py      # Pi data loading
│   └── ...
├── frontend/               # Web interface
├── data/
│   ├── chromadb/          # Vector store (exported from desktop)
│   ├── rag_chatbot.db     # SQLite database (exported from desktop)
│   └── manifest.json      # Model requirements (exported from desktop)
├── scripts/
│   ├── desktop_export.sh  # Desktop export automation
│   └── pi_setup.sh        # Pi setup automation
└── requirements.txt
```

---

## Performance Expectations

### Desktop Processing
- **Speed**: ~10-50 documents/minute (depends on size)
- **GPU Usage**: 80-100% during embedding generation
- **Memory**: 4-8GB RAM, 4-6GB VRAM

### Pi Query Serving
- **Retrieval**: <2 seconds
- **Response Generation**: <10 seconds
- **Memory**: 2-4GB RAM
- **Concurrent Users**: 10+ simultaneous queries

---

## Next Steps

1. **Read the full guide**: See `DESKTOP_PI_USAGE_GUIDE.md` for detailed instructions
2. **Configure your system**: Edit `backend/config.py` on both systems
3. **Add your documents**: Place documents in folders and add them via the web UI
4. **Process and export**: Run `./scripts/desktop_export.sh`
5. **Setup Pi**: Run `./scripts/pi_setup.sh` on your Raspberry Pi
6. **Start querying**: Access the web interface and ask questions!

---

## Support

For issues or questions:
- Check logs: `tail -f logs/app.log`
- Review manifest: `cat data/manifest.json`
- Verify health: `curl http://localhost:8000/api/health`
- Check the troubleshooting section in `DESKTOP_PI_USAGE_GUIDE.md`

---

**Enjoy your Desktop-Pi RAG Pipeline!** 🚀
