# Desktop-Pi RAG Pipeline - Complete Setup Summary

## Quick Overview

This system splits RAG processing between your desktop PC (RTX 4080) and Raspberry Pi for optimal performance and cost efficiency.

---

## What You Need

### Hardware
- **Desktop**: PC with RTX 4080 GPU
- **Raspberry Pi**: Pi 4 with 4GB+ RAM (8GB recommended)
- **Network**: Both on same network for file transfer

### Software (Both Systems)
- Python 3.10+
- Ollama
- This codebase

---

## Installation Steps

### 1. Desktop Setup (5 minutes)

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the best models for quality
ollama pull mxbai-embed-large      # Best embedding model (1024-dim)
ollama pull qwen2.5vl:7b          # Best vision model for images
ollama pull qwen2.5:14b            # Optional: for testing

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Raspberry Pi Setup (5 minutes)

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull lightweight models
ollama pull qwen2.5:3b             # Conversational model (efficient)
ollama pull mxbai-embed-large      # Must match desktop!

# Install Python dependencies
pip install -r requirements.txt
```

---

## How to Use

### Step 1: Process Documents on Desktop

```bash
# Start the server
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000

# Open web interface
# http://localhost:8000

# Add your document folders through the UI
# The system will automatically:
# - Extract text from PDFs, DOCX, TXT, etc.
# - Process images with vision model (OCR, understanding)
# - Generate high-quality embeddings
# - Store everything in ChromaDB
```

### Step 2: Export for Pi

```bash
# Run the automated export script
chmod +x scripts/desktop_export.sh
./scripts/desktop_export.sh

# This will:
# - Validate all processed data
# - Create export package
# - Transfer to your Pi automatically
```

### Step 3: Setup on Pi

```bash
# SSH into your Pi
ssh pi@raspberrypi.local

# Extract and setup
tar -xzf pi_export_*.tar.gz
cd pi_export_*
chmod +x setup_pi.sh
./setup_pi.sh

# The script will:
# - Copy data to correct locations
# - Configure Pi settings
# - Optionally create systemd service
# - Start the server
```

### Step 4: Use the System

Access from any device:
```
http://raspberrypi.local:8000
```

Ask questions and get AI-powered answers from your documents!

---

## What Each System Does

### Desktop (Heavy Lifting - One Time)

**Processing:**
- Extracts text from documents (PDF, DOCX, TXT, etc.)
- Processes images with `qwen2.5vl:7b` (OCR, understanding)
- Generates embeddings with `mxbai-embed-large` (1024-dim, GPU accelerated)
- Chunks documents intelligently
- Stores in ChromaDB vector database

**Performance:**
- Text: ~500-1000 chunks/minute
- Images: ~10-15 images/minute
- GPU utilization: 80-100%

### Raspberry Pi (Lightweight - Continuous)

**Serving:**
- Loads pre-computed embeddings (read-only)
- Handles user queries
- Retrieves relevant chunks via vector search
- Generates responses with `qwen2.5:3b` (CPU-only)
- Serves web interface

**Performance:**
- Query processing: 3-7 seconds total
- Concurrent users: 5-10 simultaneous
- Memory usage: 2-3GB
- Always available, low power

---

## Model Choices Explained

### Why These Models?

**Desktop Embedding: `mxbai-embed-large`**
- State-of-the-art for RAG (MTEB benchmark leader)
- Outperforms OpenAI's text-embedding-3-large
- 1024 dimensions = high quality retrieval
- Perfect for GPU acceleration

**Desktop Vision: `qwen2.5vl:7b`**
- Best open-source vision model for 2025
- Excellent OCR (29 languages)
- Strong document understanding
- Handles charts, diagrams, scanned docs
- Dynamic resolution (no image distortion)

**Pi Conversational: `qwen2.5:3b`**
- Optimized for Raspberry Pi
- Excellent quality-to-size ratio
- Fast CPU inference (2-5 seconds)
- Multilingual (29+ languages including Korean)
- Only 2-3GB RAM

---

## File Flow

```
Desktop                          Raspberry Pi
├─ Documents/                    ├─ data/
│  ├─ PDFs                       │  ├─ chromadb/      (loaded from export)
│  ├─ Images                     │  ├─ app.db         (loaded from export)
│  └─ Text files                 │  └─ manifest.json  (loaded from export)
│                                │
├─ Process with GPU              ├─ Load in read-only mode
│  ├─ Extract text               │
│  ├─ OCR images                 ├─ Serve web interface
│  ├─ Generate embeddings        │
│  └─ Store in ChromaDB          ├─ Process queries
│                                │  ├─ Generate query embedding
├─ Export package                │  ├─ Search vector store
│  ├─ chromadb/                  │  ├─ Retrieve top chunks
│  ├─ app.db                     │  └─ Generate response
│  ├─ manifest.json              │
│  └─ config_pi.py               └─ Return answers
│
└─ Transfer to Pi ──────────────>
```

---

## Adding New Documents

When you add new documents, use incremental updates:

```bash
# Desktop: Process new docs
curl -X POST http://localhost:8000/api/process

# Desktop: Create incremental export
./scripts/desktop_export.sh incremental

# Pi: Merge incremental data
tar -xzf pi_export_incremental_*.tar.gz
cd pi_export_incremental_*
chmod +x ../scripts/pi_merge_incremental.sh
../scripts/pi_merge_incremental.sh

# Done! New documents are now searchable
```

---

## Configuration Files

### Desktop: `backend/config.py`

```python
# Enable processing
ENABLE_DOCUMENT_PROCESSING = True

# Best models for quality
EMBEDDING_MODEL = "mxbai-embed-large"  # 1024-dim embeddings
OLLAMA_VISION_MODEL = "qwen2.5vl:7b"  # Vision processing
OLLAMA_MODEL = "qwen2.5:14b"  # Optional testing

# Paths
CHROMADB_PATH = "data/chromadb"
SQLITE_PATH = "data/rag_chatbot.db"
```

### Pi: `backend/config.py` (auto-generated)

```python
# Disable processing (read-only)
ENABLE_DOCUMENT_PROCESSING = False

# Lightweight models
OLLAMA_MODEL = "qwen2.5:3b"  # Conversational
EMBEDDING_MODEL = "mxbai-embed-large"  # Must match desktop!

# Paths
CHROMADB_PATH = "data/chromadb"
SQLITE_PATH = "data/app.db"
MANIFEST_PATH = "data/manifest.json"
```

---

## Troubleshooting

### Desktop Issues

**GPU not being used:**
```bash
nvidia-smi  # Check GPU is visible
ollama ps   # Check Ollama is using GPU
```

**Processing is slow:**
- Check GPU utilization with `nvidia-smi`
- Reduce batch size in config
- Ensure Ollama is using GPU

**Export fails:**
```bash
# Check disk space
df -h

# Validate processing first
curl http://localhost:8000/api/processing/report
```

### Pi Issues

**Server won't start:**
```bash
# Check Ollama is running
systemctl status ollama

# Verify models are available
ollama list

# Check data files exist
ls -la ~/rag-chatbot/data/
```

**Out of memory:**
```bash
# Check memory usage
free -h

# Switch to lighter model
ollama pull qwen2.5:1.5b
# Update config to use qwen2.5:1.5b
```

**Queries are slow:**
- Use `qwen2.5:1.5b` instead of 3b
- Reduce TOP_K from 5 to 3 in config
- Use SSD instead of microSD card

---

## Performance Expectations

### Desktop Processing
- **Text documents**: 500-1000 chunks/minute
- **Images**: 10-15 images/minute (with qwen2.5vl:7b)
- **GPU usage**: 80-100%
- **Memory**: 4-6GB VRAM, 8-12GB RAM

### Pi Query Serving
- **Query embedding**: <500ms
- **Vector search**: <1s
- **Response generation**: 2-5s
- **Total query time**: 3-7s
- **Concurrent users**: 5-10 simultaneous

---

## Key Features

### Image Processing
- **OCR**: Extract text from images in 29 languages
- **Document understanding**: Charts, diagrams, tables
- **Scanned documents**: High-quality text extraction
- **Handwriting**: Basic handwriting recognition
- **Multilingual**: Korean, English, Chinese, Japanese, etc.

### Text Processing
- **Multiple formats**: PDF, DOCX, TXT, MD, etc.
- **Smart chunking**: Preserves context
- **Metadata preservation**: Filename, date, type
- **Incremental updates**: Only process new/changed files

### Query Features
- **Semantic search**: Understands meaning, not just keywords
- **Source attribution**: Shows where answers come from
- **Multilingual**: Ask in any language
- **Conversation history**: Maintains context
- **Fast responses**: 3-7 seconds end-to-end

---

## Cost & Resource Comparison

### Traditional Cloud RAG
- **Processing**: $0.10-0.50 per 1000 documents
- **Storage**: $0.10-0.30 per GB/month
- **Queries**: $0.001-0.01 per query
- **Monthly cost**: $50-500+ depending on usage

### Desktop-Pi RAG (This System)
- **Processing**: One-time electricity cost (~$0.50)
- **Storage**: Free (local)
- **Queries**: Free (unlimited)
- **Monthly cost**: ~$5 (Pi electricity)
- **Savings**: 90-99% compared to cloud

---

## Next Steps

1. **Read detailed guides:**
   - `QUICK_START.md` - Fast setup guide
   - `DESKTOP_PI_USAGE_GUIDE.md` - Complete usage instructions
   - `MODEL_RECOMMENDATIONS.md` - Model details and alternatives

2. **Configure your system:**
   - Edit `backend/config.py` on both systems
   - Adjust chunk size, batch size, TOP_K as needed

3. **Add your documents:**
   - Place documents in folders
   - Add folders via web UI
   - Let the system process

4. **Export and deploy:**
   - Run `./scripts/desktop_export.sh`
   - Setup Pi with `./scripts/pi_setup.sh`

5. **Start using:**
   - Access web interface
   - Ask questions
   - Get AI-powered answers!

---

## Support & Resources

- **Ollama Models**: https://ollama.com/library
- **Model Benchmarks**: See `MODEL_RECOMMENDATIONS.md`
- **Troubleshooting**: See `DESKTOP_PI_USAGE_GUIDE.md`
- **Scripts**: Check `scripts/` directory

---

**You're all set!** Your Desktop-Pi RAG Pipeline is ready to transform how you interact with your documents. 🚀
