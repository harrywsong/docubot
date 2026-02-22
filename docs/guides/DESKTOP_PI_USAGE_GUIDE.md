# Desktop-Pi RAG Pipeline Usage Guide

## Overview

This system splits RAG processing into two parts:
- **Desktop (RTX 4080)**: Heavy document processing and embedding generation
- **Raspberry Pi**: Lightweight query serving and conversational responses

## System Architecture

```
Desktop (Your PC)                    Raspberry Pi
├─ Process documents          →      ├─ Load processed data
├─ Generate embeddings (14b)  →      ├─ Serve web interface
├─ Create export package      →      ├─ Handle queries (3b model)
└─ Transfer to Pi             →      └─ Generate responses
```

---

## Part 1: Desktop Setup (Your PC with RTX 4080)

### Prerequisites

1. **Python 3.10+** installed
2. **Ollama** installed with models:
   ```bash
   # Install Ollama from https://ollama.ai
   
   # Pull the 14b model for processing (better embeddings)
   ollama pull qwen2.5:14b
   
   # Pull the vision model for image processing
   ollama pull qwen2.5vl:7b
   ```

3. **Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

Edit `backend/config.py` on your desktop:

```python
# Desktop configuration
ENABLE_DOCUMENT_PROCESSING = True  # Enable processing on desktop

# Use 14b model for better quality embeddings
OLLAMA_MODEL = "qwen2.5:14b"  # For text embeddings
CONVERSATIONAL_MODEL = "qwen2.5:3b"  # For export manifest

# Vision model for images
OLLAMA_VISION_MODEL = "qwen2.5vl:7b"

# Embedding model (sentence-transformers)
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Paths
CHROMADB_PATH = "data/chromadb"
SQLITE_PATH = "data/rag_chatbot.db"
```

### Step 1: Add Documents to Process

Place your documents in a folder, then add it to the watched folders:

```bash
# Start the backend server
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000

# In another terminal or via the web interface:
# Add a folder to watch
curl -X POST http://localhost:8000/api/folders \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/your/documents"}'
```

Or use the web interface at `http://localhost:8000` to add folders.

### Step 2: Process Documents

The system will automatically process documents in watched folders:

```bash
# Trigger processing manually
curl -X POST http://localhost:8000/api/process
```

**What happens during processing:**
- Scans all watched folders for new/modified files
- Extracts text from documents (PDF, TXT, DOCX, etc.)
- Processes images with vision model
- Chunks documents into manageable pieces
- Generates embeddings using the 14b model (GPU accelerated)
- Stores everything in ChromaDB and SQLite

**Monitor progress:**
```bash
# Check processing status
curl http://localhost:8000/api/folders
```

### Step 3: Validate Processing

Before exporting, validate that all documents processed correctly:

```bash
# Get processing report
curl http://localhost:8000/api/processing/report
```

**Expected output:**
```json
{
  "total_documents": 150,
  "total_chunks": 1250,
  "total_embeddings": 1250,
  "failed_documents": [],
  "missing_embeddings": [],
  "incomplete_metadata": [],
  "validation_passed": true
}
```

### Step 4: Create Export Package

Once processing is complete and validated, create an export package:

```bash
# Create full export
curl -X POST http://localhost:8000/api/export \
  -H "Content-Type: application/json" \
  -d '{"incremental": false}'
```

**What gets exported:**
- `chromadb/` - Vector store with all embeddings
- `app.db` - SQLite database with metadata
- `manifest.json` - Model requirements and statistics
- `config_pi.py` - Pi configuration template
- `DEPLOYMENT.md` - Deployment instructions

**Output:**
```json
{
  "success": true,
  "package_path": "pi_export",
  "archive_path": "pi_export_20240115_103000.tar.gz",
  "size_bytes": 47185920,
  "statistics": {
    "total_documents": 150,
    "total_chunks": 1250,
    "vector_store_size_mb": 45.2,
    "database_size_mb": 2.1
  }
}
```

### Step 5: Transfer to Raspberry Pi

Transfer the export package to your Pi:

```bash
# Option 1: Using SCP
scp pi_export_20240115_103000.tar.gz pi@raspberrypi.local:~/

# Option 2: Using rsync (better for large files)
rsync -avz --progress pi_export_20240115_103000.tar.gz pi@raspberrypi.local:~/
```

---

## Part 2: Raspberry Pi Setup

### Prerequisites on Pi

1. **Raspberry Pi 4** (4GB+ RAM recommended)
2. **Raspberry Pi OS** (64-bit)
3. **Python 3.10+**
4. **Ollama** with lightweight model:

```bash
# Install Ollama on Pi
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the lightweight 3b model (optimized for Pi)
ollama pull qwen2.5:3b
```

5. **Python dependencies**:
```bash
pip install -r requirements.txt
```

### Step 1: Extract Export Package

SSH into your Pi and extract the package:

```bash
ssh pi@raspberrypi.local

# Extract the archive
tar -xzf pi_export_20240115_103000.tar.gz

# Navigate to package
cd pi_export
```

### Step 2: Set Up Directory Structure

Copy the data to your application directory:

```bash
# Create application directory
mkdir -p ~/rag-chatbot/data

# Copy vector store
cp -r chromadb ~/rag-chatbot/data/

# Copy database
cp app.db ~/rag-chatbot/data/

# Copy manifest
cp manifest.json ~/rag-chatbot/data/

# Copy your application code (if not already there)
# You'll need to transfer your backend/ and frontend/ directories
```

### Step 3: Configure Pi

Create or update `backend/config.py` on the Pi:

```python
# Pi configuration
ENABLE_DOCUMENT_PROCESSING = False  # CRITICAL: Disable processing on Pi

# Use lightweight model for responses
OLLAMA_MODEL = "qwen2.5:3b"
CONVERSATIONAL_MODEL = "qwen2.5:3b"

# Use same embedding model as desktop (for compatibility)
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Paths
CHROMADB_PATH = "/home/pi/rag-chatbot/data/chromadb"
SQLITE_PATH = "/home/pi/rag-chatbot/data/app.db"
MANIFEST_PATH = "/home/pi/rag-chatbot/data/manifest.json"
```

Or use the provided template:

```bash
# Copy the Pi config template
cp config_pi.py ~/rag-chatbot/backend/config.py
```

### Step 4: Start Pi Server

Start the server on your Pi:

```bash
cd ~/rag-chatbot

# Start the server
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
```

**What happens on startup:**
- Loads vector store in read-only mode
- Loads database in read-only mode
- Validates manifest for model compatibility
- Initializes resource monitoring
- Starts serving web interface

**Check health:**
```bash
curl http://localhost:8000/api/health
```

**Expected output:**
```json
{
  "status": "healthy",
  "memory_usage_percent": 45.2,
  "memory_available_mb": 3200.5,
  "model_loaded": true,
  "vector_store_loaded": true,
  "total_chunks": 1250
}
```

### Step 5: Access Web Interface

From any device on your network:

```
http://raspberrypi.local:8000
```

Or use the Pi's IP address:

```
http://192.168.1.100:8000
```

---

## Part 3: Using the System

### Querying Documents

Once the Pi server is running, you can query your documents:

**Via Web Interface:**
1. Open `http://raspberrypi.local:8000`
2. Type your question
3. Get AI-generated responses with source citations

**Via API:**
```bash
curl -X POST http://raspberrypi.local:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Python?",
    "conversation_id": "test-123"
  }'
```

**Response:**
```json
{
  "response": "Python is a high-level programming language...",
  "sources": [
    {
      "content": "Python is a high-level programming language...",
      "filename": "python.txt",
      "similarity": 0.92
    }
  ],
  "conversation_id": "test-123"
}
```

---

## Part 4: Incremental Updates

When you add new documents on your desktop, you don't need to re-export everything.

### On Desktop

1. **Add new documents** to watched folders
2. **Process new documents**:
   ```bash
   curl -X POST http://localhost:8000/api/process
   ```

3. **Create incremental export**:
   ```bash
   curl -X POST http://localhost:8000/api/export \
     -H "Content-Type: application/json" \
     -d '{
       "incremental": true,
       "since": "2024-01-15T10:30:00Z"
     }'
   ```

4. **Transfer incremental package**:
   ```bash
   scp pi_export_incremental_20240120_140000.tar.gz pi@raspberrypi.local:~/
   ```

### On Raspberry Pi

1. **Stop the server**:
   ```bash
   # Press Ctrl+C or
   pkill -f "uvicorn backend.api:app"
   ```

2. **Extract incremental package**:
   ```bash
   tar -xzf pi_export_incremental_20240120_140000.tar.gz
   ```

3. **Merge incremental data**:
   ```bash
   curl -X POST http://localhost:8000/api/data/merge \
     -H "Content-Type: application/json" \
     -d '{"package_path": "pi_export_incremental"}'
   ```

4. **Restart server**:
   ```bash
   python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
   ```

---

## Part 5: Automation & Best Practices

### Desktop Automation

Create a script `process_and_export.sh`:

```bash
#!/bin/bash

# Process documents
echo "Processing documents..."
curl -X POST http://localhost:8000/api/process

# Wait for processing to complete
sleep 10

# Validate processing
echo "Validating..."
curl http://localhost:8000/api/processing/report

# Create export
echo "Creating export..."
curl -X POST http://localhost:8000/api/export \
  -H "Content-Type: application/json" \
  -d '{"incremental": false}'

# Transfer to Pi
echo "Transferring to Pi..."
LATEST_EXPORT=$(ls -t pi_export_*.tar.gz | head -1)
rsync -avz --progress $LATEST_EXPORT pi@raspberrypi.local:~/

echo "Done! Extract and restart Pi server."
```

### Pi Systemd Service

Create `/etc/systemd/system/rag-chatbot.service`:

```ini
[Unit]
Description=RAG Chatbot Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/rag-chatbot
ExecStart=/usr/bin/python3 -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable rag-chatbot
sudo systemctl start rag-chatbot
sudo systemctl status rag-chatbot
```

### Monitoring

**Check Pi health:**
```bash
curl http://raspberrypi.local:8000/api/health
```

**Check data statistics:**
```bash
curl http://raspberrypi.local:8000/api/data/stats
```

**View logs:**
```bash
# On Pi
tail -f ~/rag-chatbot/logs/app.log
```

---

## Troubleshooting

### Desktop Issues

**Problem: Processing is slow**
- Check GPU is being used: `nvidia-smi`
- Reduce batch size in config
- Use smaller model temporarily

**Problem: Export fails**
- Check disk space: `df -h`
- Validate processing first
- Check logs for errors

### Pi Issues

**Problem: Server won't start**
- Check Ollama is running: `systemctl status ollama`
- Verify model is available: `ollama list`
- Check data files exist
- Review logs: `tail -f logs/app.log`

**Problem: Queries are slow**
- Check memory usage: `free -h`
- Consider using 1.5b model instead of 3b
- Reduce top-k retrieval parameter
- Use SSD instead of microSD card

**Problem: Out of memory**
- Restart Pi: `sudo reboot`
- Use smaller model: `ollama pull qwen2.5:1.5b`
- Reduce concurrent requests

### Model Compatibility

**Problem: Embedding dimension mismatch**
- Ensure same embedding model on both systems
- Check manifest.json for required dimensions
- Re-export from desktop if needed

---

## Quick Reference

### Desktop Commands

```bash
# Start server
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000

# Add folder
curl -X POST http://localhost:8000/api/folders -H "Content-Type: application/json" -d '{"path": "/path/to/docs"}'

# Process documents
curl -X POST http://localhost:8000/api/process

# Validate
curl http://localhost:8000/api/processing/report

# Export
curl -X POST http://localhost:8000/api/export -H "Content-Type: application/json" -d '{"incremental": false}'

# Transfer
scp pi_export_*.tar.gz pi@raspberrypi.local:~/
```

### Pi Commands

```bash
# Extract
tar -xzf pi_export_*.tar.gz

# Start server
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000

# Check health
curl http://localhost:8000/api/health

# View logs
tail -f logs/app.log
```

---

## Summary

1. **Desktop**: Process documents with 14b model → Create export → Transfer to Pi
2. **Pi**: Extract data → Start server with 3b model → Serve queries
3. **Updates**: Create incremental export → Transfer → Merge on Pi
4. **Access**: Web interface at `http://raspberrypi.local:8000`

The system is now ready to use! Your desktop does the heavy lifting once, and your Pi serves queries efficiently.
