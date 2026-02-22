# Quick Reference - Desktop-Pi RAG Pipeline

## Model Installation Commands

### Desktop (Your PC with RTX 4080)

```bash
# Best embedding model for RAG (1024-dim)
ollama pull mxbai-embed-large

# Best vision model for images/OCR (7B)
ollama pull qwen2.5vl:7b

# Text generation for testing (optional)
ollama pull qwen2.5:14b
```

### Raspberry Pi

```bash
# Lightweight conversational model (3B)
ollama pull qwen2.5:3b

# Embedding model (must match desktop!)
ollama pull mxbai-embed-large

# Alternative if memory is tight (1.5B)
ollama pull qwen2.5:1.5b
```

---

## Desktop Commands

```bash
# Start server
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000

# Add folder
curl -X POST http://localhost:8000/api/folders \
  -H "Content-Type: application/json" \
  -d '{"path": "C:/path/to/documents"}'

# Process documents
curl -X POST http://localhost:8000/api/process

# Check status
curl http://localhost:8000/api/folders

# Validate processing
curl http://localhost:8000/api/processing/report

# Create export
curl -X POST http://localhost:8000/api/export \
  -H "Content-Type: application/json" \
  -d '{"incremental": false}'

# Or use automated script
./scripts/desktop_export.sh

# Transfer to Pi
scp pi_export_*.tar.gz pi@raspberrypi.local:~/
```

---

## Raspberry Pi Commands

```bash
# Extract package
tar -xzf pi_export_*.tar.gz
cd pi_export_*

# Run setup
chmod +x setup_pi.sh
./setup_pi.sh

# Start server manually
cd ~/rag-chatbot
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000

# Or with systemd
sudo systemctl start rag-chatbot
sudo systemctl status rag-chatbot
sudo systemctl stop rag-chatbot

# Check health
curl http://localhost:8000/api/health

# View logs
sudo journalctl -u rag-chatbot -f
```

---

## Incremental Updates

### Desktop
```bash
# Process new documents
curl -X POST http://localhost:8000/api/process

# Create incremental export
./scripts/desktop_export.sh incremental

# Transfer to Pi
scp pi_export_incremental_*.tar.gz pi@raspberrypi.local:~/
```

### Pi
```bash
# Extract incremental package
tar -xzf pi_export_incremental_*.tar.gz
cd pi_export_incremental_*

# Merge updates
chmod +x ../scripts/pi_merge_incremental.sh
../scripts/pi_merge_incremental.sh
```

---

## Configuration Files

### Desktop: `backend/config.py`
```python
ENABLE_DOCUMENT_PROCESSING = True
EMBEDDING_MODEL = "mxbai-embed-large"
OLLAMA_VISION_MODEL = "qwen2.5vl:7b"
OLLAMA_MODEL = "qwen2.5:14b"
```

### Pi: `backend/config.py`
```python
ENABLE_DOCUMENT_PROCESSING = False
OLLAMA_MODEL = "qwen2.5:3b"
EMBEDDING_MODEL = "mxbai-embed-large"
```

---

## Troubleshooting

### Check GPU
```bash
nvidia-smi
```

### Check Ollama
```bash
ollama list
ollama ps
```

### Check Memory (Pi)
```bash
free -h
```

### Check Disk Space
```bash
df -h
```

### Restart Ollama
```bash
# Windows
# Stop Ollama from system tray, then restart

# Linux/Pi
sudo systemctl restart ollama
```

---

## Access URLs

- **Desktop**: http://localhost:8000
- **Pi**: http://raspberrypi.local:8000
- **Pi (IP)**: http://192.168.1.100:8000

---

## Model Sizes

| Model | Size | RAM/VRAM | Speed |
|-------|------|----------|-------|
| mxbai-embed-large | 669 MB | ~1 GB | Fast |
| qwen2.5vl:7b | 6 GB | ~8 GB | Medium |
| qwen2.5:14b | 9 GB | ~12 GB | Medium |
| qwen2.5:3b | 2 GB | ~3 GB | Fast |
| qwen2.5:1.5b | 1 GB | ~2 GB | Very Fast |

---

## Performance Expectations

### Desktop
- Text: 500-1000 chunks/min
- Images: 10-15 images/min
- GPU: 80-100%

### Pi
- Query time: 3-7 seconds
- Concurrent users: 5-10
- Memory: 2-3 GB

---

## Common Issues

**"Model not found"**
```bash
ollama pull <model-name>
```

**"GPU not being used"**
```bash
# Check GPU
nvidia-smi

# Restart Ollama
```

**"Out of memory" (Pi)**
```bash
# Use lighter model
ollama pull qwen2.5:1.5b

# Update config to use qwen2.5:1.5b
```

**"Port already in use"**
```bash
# Find process
netstat -ano | findstr :8000

# Kill process (Windows)
taskkill /PID <pid> /F

# Kill process (Linux/Pi)
kill -9 <pid>
```

---

## File Locations

### Desktop
- Data: `data/chromadb/`, `data/rag_chatbot.db`
- Config: `backend/config.py`
- Exports: `pi_export_*/`

### Pi
- Data: `~/rag-chatbot/data/`
- Config: `~/rag-chatbot/backend/config.py`
- Logs: `~/rag-chatbot/logs/`

---

## Support

- Full Guide: `DESKTOP_PI_USAGE_GUIDE.md`
- Quick Start: `QUICK_START.md`
- Models: `MODEL_RECOMMENDATIONS.md`
- Setup: `SETUP_SUMMARY.md`
