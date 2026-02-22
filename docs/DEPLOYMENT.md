# Desktop-Pi RAG Pipeline Deployment Guide

This guide provides complete instructions for deploying the Desktop-Pi RAG Pipeline, a split-architecture system that processes documents on powerful desktop hardware and serves queries on resource-constrained Raspberry Pi hardware.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
  - [Desktop Prerequisites](#desktop-prerequisites)
  - [Raspberry Pi Prerequisites](#raspberry-pi-prerequisites)
- [Initial Setup](#initial-setup)
  - [Desktop Setup](#desktop-setup)
  - [Raspberry Pi Setup](#raspberry-pi-setup)
- [Transfer Workflow](#transfer-workflow)
  - [Step 1: Process Documents on Desktop](#step-1-process-documents-on-desktop)
  - [Step 2: Create Export Package](#step-2-create-export-package)
  - [Step 3: Transfer to Raspberry Pi](#step-3-transfer-to-raspberry-pi)
  - [Step 4: Load Data on Pi](#step-4-load-data-on-pi)
  - [Step 5: Start Pi Server](#step-5-start-pi-server)
- [Incremental Update Workflow](#incremental-update-workflow)
- [Troubleshooting](#troubleshooting)
- [Performance Tuning](#performance-tuning)
- [Security Considerations](#security-considerations)

---

## Overview

The Desktop-Pi RAG Pipeline uses a "process once, serve anywhere" architecture:

- **Desktop**: Handles heavy computation (document processing, embedding generation with large models)
- **Raspberry Pi**: Handles lightweight operations (query serving, response generation with small models)
- **Data Flow**: Desktop processes → exports → Pi imports → serves queries

### Key Benefits

- One-time expensive processing on powerful hardware
- Efficient serving on resource-constrained hardware
- No GPU required on Pi
- Incremental updates without full redeployment
- Local deployment (no cloud dependencies)

---

## Prerequisites

### Desktop Prerequisites

**Hardware Requirements:**
- NVIDIA GPU with CUDA support (RTX 4080 or similar recommended)
- 16GB+ RAM
- 50GB+ free disk space (for models and processed data)

**Software Requirements:**
- Ubuntu 20.04+ or Windows 10+
- Python 3.10 or higher
- CUDA toolkit (for GPU acceleration)
- Git

**Required Software:**
1. **Ollama** - For vision model inference
   ```bash
   # Install Ollama
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Pull the vision model
   ollama pull qwen2.5vl:7b
   
   # Verify installation
   ollama list
   ```

2. **Python Dependencies**
   ```bash
   # Clone the repository
   git clone <repository-url>
   cd docubot
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Verify GPU Setup**
   ```bash
   # Check CUDA availability
   python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
   ```

### Raspberry Pi Prerequisites

**Hardware Requirements:**
- **Recommended**: Raspberry Pi 4 (8GB RAM) or Raspberry Pi 5 (8GB RAM)
- **Minimum**: Raspberry Pi 4 (4GB RAM)
- 32GB+ microSD card or SSD (SSD strongly recommended for better performance)
- Stable power supply (official Pi power supply recommended)
- Network connectivity (wired Ethernet recommended)

**Software Requirements:**
- Raspberry Pi OS (64-bit) - Bookworm or later
- Python 3.10 or higher
- SSH access enabled (for remote management)

**Required Software:**
1. **Update System**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Install Python and Dependencies**
   ```bash
   # Install Python 3.10+ if not already installed
   sudo apt install python3 python3-pip python3-venv -y
   
   # Install system dependencies
   sudo apt install git -y
   ```

3. **Install Ollama**
   ```bash
   # Install Ollama
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Pull the conversational model
   # For 8GB Pi: use qwen2.5:3b
   ollama pull qwen2.5:3b
   
   # For 4GB Pi: use smaller model
   # ollama pull qwen2.5:1.5b
   
   # Verify installation
   ollama list
   
   # Test the model
   ollama run qwen2.5:3b "Hello"
   ```

4. **Enable Ollama Service**
   ```bash
   # Ensure Ollama starts on boot
   sudo systemctl enable ollama
   sudo systemctl start ollama
   sudo systemctl status ollama
   ```

---

## Initial Setup

### Desktop Setup

1. **Configure the Application**
   
   Edit `config.py` to ensure document processing is enabled:
   ```python
   # config.py
   ENABLE_DOCUMENT_PROCESSING = True  # Must be True on desktop
   EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
   OLLAMA_MODEL = "qwen2.5vl:7b"  # Vision model for desktop
   ```

2. **Prepare Document Directories**
   ```bash
   # Create watched directories
   mkdir -p data/watched_folders/receipts
   mkdir -p data/watched_folders/reports
   mkdir -p data/watched_folders/forms
   
   # Add your documents to these folders
   cp /path/to/your/documents/* data/watched_folders/receipts/
   ```

3. **Verify Configuration**
   ```bash
   # Test the configuration
   python -c "from backend.config import Config; print('Config OK')"
   ```

### Raspberry Pi Setup

1. **Create Project Directory**
   ```bash
   # On the Pi
   mkdir -p ~/docubot
   cd ~/docubot
   ```

2. **Create Data Directories**
   ```bash
   mkdir -p data/chromadb
   mkdir -p data
   ```

3. **Prepare Configuration**
   
   You'll copy the `config_pi_template.py` from the export package later. For now, ensure the directory structure is ready.

---

## Transfer Workflow

This section describes the complete workflow for initial deployment from desktop to Pi.

### Step 1: Process Documents on Desktop

1. **Start the Desktop Application**
   ```bash
   # On desktop
   cd /path/to/docubot
   python -m uvicorn backend.api:app --reload
   ```

2. **Process Documents**
   
   The application will automatically scan the watched folders and process documents:
   - Extract text from PDFs and images
   - Generate embeddings using the large embedding model
   - Store chunks and embeddings in ChromaDB
   - Update processing state in SQLite database

3. **Monitor Processing**
   
   Check the logs to ensure processing completes successfully:
   ```bash
   # Watch the logs
   tail -f logs/app.log
   ```
   
   Or use the API to check processing status:
   ```bash
   curl http://localhost:8000/api/processing/report
   ```

4. **Validate Processing**
   
   Before exporting, ensure all documents processed successfully:
   ```bash
   # Get processing report
   curl http://localhost:8000/api/processing/report | python -m json.tool
   ```
   
   Look for:
   - `total_documents`: Number of documents processed
   - `total_chunks`: Number of chunks created
   - `failed_documents`: Should be empty or minimal

### Step 2: Create Export Package

1. **Run Export Script**
   
   Use the export utility to create a deployment package:
   ```bash
   # Full export (first time deployment)
   python utils/export_for_pi.py --output pi_export
   ```
   
   This will:
   - Copy the ChromaDB vector store
   - Copy the SQLite database
   - Create a manifest file with model compatibility information
   - Generate Pi configuration template
   - Create deployment instructions
   - Package everything into a compressed tar.gz archive

2. **Verify Export Package**
   
   Check the export completed successfully:
   ```bash
   ls -lh pi_export/
   ```
   
   You should see:
   - `chromadb/` - Vector store directory
   - `app.db` - SQLite database
   - `manifest.json` - Model compatibility manifest
   - `config_pi_template.py` - Pi configuration template
   - `DEPLOYMENT.md` - This deployment guide
   - `pi_export.tar.gz` - Compressed archive

3. **Review Export Statistics**
   
   The export script will display statistics:
   ```
   Export Complete!
   ================================================================================
   
   Export package: pi_export
   Archive: pi_export/pi_export.tar.gz
   Size: 45.23 MB
   
   Statistics:
     • Total documents: 150
     • Total chunks: 1250
     • Total embeddings: 1250
     • Vector store size: 42.10 MB
     • Database size: 2.15 MB
   ```

### Step 3: Transfer to Raspberry Pi

1. **Transfer the Archive**
   
   Use `scp` to securely transfer the archive to your Pi:
   ```bash
   # Replace pi-hostname with your Pi's hostname or IP address
   scp pi_export/pi_export.tar.gz pi@pi-hostname:~/docubot/
   ```
   
   For faster transfer on local network, you can use `rsync`:
   ```bash
   rsync -avz --progress pi_export/pi_export.tar.gz pi@pi-hostname:~/docubot/
   ```

2. **Verify Transfer**
   
   SSH into your Pi and check the file:
   ```bash
   ssh pi@pi-hostname
   cd ~/docubot
   ls -lh pi_export.tar.gz
   ```

### Step 4: Load Data on Pi

1. **Extract the Archive**
   ```bash
   # On the Pi
   cd ~/docubot
   tar -xzf pi_export.tar.gz
   ```

2. **Move Data to Correct Locations**
   ```bash
   # Move ChromaDB
   mv pi_export/chromadb data/
   
   # Move SQLite database
   mv pi_export/app.db data/
   
   # Move manifest
   mv pi_export/manifest.json data/
   
   # Copy Pi configuration template
   cp pi_export/config_pi_template.py config.py
   ```

3. **Install Python Dependencies**
   ```bash
   # Create virtual environment (recommended)
   python3 -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   # Copy requirements.txt from desktop or install manually
   pip install fastapi uvicorn chromadb sentence-transformers sqlalchemy
   ```

4. **Copy Application Code**
   
   You need to transfer the application code from desktop:
   ```bash
   # On desktop, create a code archive
   tar -czf docubot-code.tar.gz backend/ frontend/ --exclude="__pycache__" --exclude="*.pyc"
   
   # Transfer to Pi
   scp docubot-code.tar.gz pi@pi-hostname:~/docubot/
   
   # On Pi, extract
   cd ~/docubot
   tar -xzf docubot-code.tar.gz
   ```

5. **Verify Configuration**
   ```bash
   # On Pi, verify the configuration
   python3 -c "from backend.config import Config; valid, errors = Config.validate(); print('Valid' if valid else errors)"
   ```

### Step 5: Start Pi Server

1. **Start the Server**
   ```bash
   # On Pi
   cd ~/docubot
   source venv/bin/activate  # If using virtual environment
   
   # Start the server
   python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
   ```
   
   The server will:
   - Load the vector store in read-only mode
   - Validate the manifest for model compatibility
   - Load the conversational model (qwen2.5:3b)
   - Start the resource monitor
   - Begin serving queries

2. **Verify Server is Running**
   ```bash
   # Check health endpoint
   curl http://localhost:8000/api/health
   ```
   
   Expected response:
   ```json
   {
     "status": "healthy",
     "memory_usage_percent": 45.2,
     "memory_available_mb": 4096.0,
     "model_loaded": true,
     "vector_store_loaded": true,
     "total_chunks": 1250
   }
   ```

3. **Access the Web Interface**
   
   Open a browser and navigate to:
   ```
   http://pi-hostname:8000
   ```
   
   You should see the RAG query interface.

4. **Test a Query**
   ```bash
   # Test via API
   curl -X POST http://localhost:8000/api/query \
     -H "Content-Type: application/json" \
     -d '{"query": "What documents do I have about receipts?"}'
   ```

5. **Run as Background Service (Optional)**
   
   To run the server as a systemd service:
   ```bash
   # Create service file
   sudo nano /etc/systemd/system/docubot.service
   ```
   
   Add the following content:
   ```ini
   [Unit]
   Description=Docubot RAG Server
   After=network.target ollama.service
   
   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/docubot
   Environment="PATH=/home/pi/docubot/venv/bin"
   ExecStart=/home/pi/docubot/venv/bin/python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
   Restart=always
   RestartSec=10
   
   [Install]
   WantedBy=multi-user.target
   ```
   
   Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable docubot
   sudo systemctl start docubot
   sudo systemctl status docubot
   ```

---

## Incremental Update Workflow

When you add new documents on the desktop, you can create an incremental export to update the Pi without full redeployment.

### Step 1: Process New Documents on Desktop

1. **Add New Documents**
   ```bash
   # On desktop, add new documents to watched folders
   cp /path/to/new/documents/* data/watched_folders/receipts/
   ```

2. **Process New Documents**
   
   The application will automatically detect and process new documents. Wait for processing to complete.

3. **Note the Timestamp**
   
   Record when you last did a full export. You'll need this for the incremental export:
   ```bash
   # Check the manifest from your last export
   cat pi_export/manifest.json | grep created_at
   # Output: "created_at": "2024-01-15T10:30:00Z"
   ```

### Step 2: Create Incremental Export

1. **Run Incremental Export**
   ```bash
   # Export only data modified since last export
   python utils/export_for_pi.py --incremental --since "2024-01-15T10:30:00" --output pi_export_incremental
   ```
   
   This creates a smaller package containing only new/modified data.

2. **Review Incremental Statistics**
   ```
   Export Complete!
   ================================================================================
   
   Statistics:
     • New documents: 10
     • New chunks: 85
     • Vector store size: 3.20 MB
     • Database size: 0.15 MB
   ```

### Step 3: Transfer Incremental Package

1. **Transfer to Pi**
   ```bash
   scp pi_export_incremental/pi_export_incremental.tar.gz pi@pi-hostname:~/docubot/
   ```

### Step 4: Merge on Pi

1. **Stop the Server**
   ```bash
   # On Pi
   # If running as service:
   sudo systemctl stop docubot
   
   # If running manually, press Ctrl+C
   ```

2. **Extract Incremental Package**
   ```bash
   cd ~/docubot
   tar -xzf pi_export_incremental.tar.gz
   ```

3. **Merge the Data**
   
   Use the merge API endpoint or script:
   ```bash
   # Start server temporarily for merge
   python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000 &
   
   # Wait for server to start
   sleep 5
   
   # Trigger merge
   curl -X POST http://localhost:8000/api/data/merge \
     -H "Content-Type: application/json" \
     -d '{"package_path": "pi_export_incremental"}'
   
   # Stop server
   pkill -f uvicorn
   ```
   
   Or manually merge:
   ```bash
   # Backup current data
   cp -r data/chromadb data/chromadb.backup
   cp data/app.db data/app.db.backup
   
   # Copy incremental data
   cp -r pi_export_incremental/chromadb/* data/chromadb/
   cp pi_export_incremental/app.db data/app.db
   cp pi_export_incremental/manifest.json data/
   ```

4. **Restart the Server**
   ```bash
   # If using systemd service:
   sudo systemctl start docubot
   
   # If running manually:
   python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
   ```

5. **Verify Merge**
   ```bash
   # Check data stats
   curl http://localhost:8000/api/data/stats
   ```
   
   You should see the updated chunk count.

---

## Troubleshooting

### Desktop Issues

#### Issue: GPU not detected
```
Error: CUDA not available
```

**Solution:**
1. Verify CUDA installation:
   ```bash
   nvidia-smi
   nvcc --version
   ```
2. Reinstall PyTorch with CUDA support:
   ```bash
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
   ```

#### Issue: Ollama model not found
```
Error: Model qwen2.5vl:7b not found
```

**Solution:**
```bash
# Pull the model
ollama pull qwen2.5vl:7b

# Verify
ollama list
```

#### Issue: Export fails with validation errors
```
Export Failed!
Errors:
  ✗ Found 15 chunks without embeddings
```

**Solution:**
1. Check processing logs for errors
2. Reprocess failed documents
3. Run validation again:
   ```bash
   curl http://localhost:8000/api/processing/report
   ```

### Raspberry Pi Issues

#### Issue: Server fails to start - missing data
```
Error: ChromaDB path does not exist: data/chromadb
```

**Solution:**
1. Verify data was extracted correctly:
   ```bash
   ls -la data/
   ```
2. Re-extract the export package:
   ```bash
   tar -xzf pi_export.tar.gz
   mv pi_export/chromadb data/
   mv pi_export/app.db data/
   ```

#### Issue: Model compatibility error
```
Error: Embedding dimension mismatch. Expected 384, got 768
```

**Solution:**
1. Check the manifest file:
   ```bash
   cat data/manifest.json | grep embedding_dimension
   ```
2. Ensure desktop and Pi use compatible models
3. Re-export from desktop with correct configuration

#### Issue: Ollama service not running
```
Error: Failed to connect to Ollama at http://localhost:11434
```

**Solution:**
```bash
# Check Ollama status
sudo systemctl status ollama

# Start Ollama
sudo systemctl start ollama

# Enable on boot
sudo systemctl enable ollama

# Verify
curl http://localhost:11434/api/tags
```

#### Issue: High memory usage
```
Warning: Memory usage at 92%
```

**Solution:**
1. Reduce TOP_K_RESULTS in config.py:
   ```python
   TOP_K_RESULTS = 3  # Reduce from 5
   ```
2. Use smaller model (for 4GB Pi):
   ```bash
   ollama pull qwen2.5:1.5b
   ```
   Update config.py:
   ```python
   CONVERSATIONAL_MODEL = "qwen2.5:1.5b"
   ```
3. Restart the server

#### Issue: Slow query responses
```
Query taking >15 seconds
```

**Solution:**
1. Check system resources:
   ```bash
   htop
   ```
2. Verify using SSD (not microSD):
   ```bash
   df -h
   ```
3. Reduce similarity threshold:
   ```python
   SIMILARITY_THRESHOLD = 0.6  # Increase from 0.5
   ```
4. Consider using smaller model or upgrading to Pi 5

#### Issue: Server crashes under load
```
Server stopped responding after multiple concurrent requests
```

**Solution:**
1. Check memory usage:
   ```bash
   free -h
   ```
2. Limit concurrent requests in config
3. Add swap space:
   ```bash
   sudo dphys-swapfile swapoff
   sudo nano /etc/dphys-swapfile
   # Set CONF_SWAPSIZE=2048
   sudo dphys-swapfile setup
   sudo dphys-swapfile swapon
   ```

### Network Issues

#### Issue: Cannot access web interface from other devices
```
Connection refused when accessing http://pi-ip:8000
```

**Solution:**
1. Verify server is listening on all interfaces:
   ```bash
   netstat -tulpn | grep 8000
   ```
   Should show `0.0.0.0:8000`
2. Check firewall:
   ```bash
   sudo ufw status
   sudo ufw allow 8000/tcp
   ```
3. Verify Pi's IP address:
   ```bash
   hostname -I
   ```

#### Issue: Transfer fails or is very slow
```
scp stalls or times out
```

**Solution:**
1. Use rsync with compression:
   ```bash
   rsync -avz --progress pi_export.tar.gz pi@pi-hostname:~/docubot/
   ```
2. Check network connectivity:
   ```bash
   ping pi-hostname
   ```
3. Use wired Ethernet instead of WiFi

---

## Performance Tuning

### Desktop Performance

**Optimize Embedding Generation:**
```python
# config.py
BATCH_SIZE = 32  # Increase for faster processing with more GPU memory
```

**Parallel Document Processing:**
```python
# Future enhancement - not yet implemented
MAX_WORKERS = 4  # Process multiple documents in parallel
```

### Pi Performance

**For Raspberry Pi 4 (8GB):**
```python
# config.py
CONVERSATIONAL_MODEL = "qwen2.5:3b"
TOP_K_RESULTS = 5
QUERY_TIMEOUT = 2
RESPONSE_TIMEOUT = 10
```

**For Raspberry Pi 4 (4GB):**
```python
# config.py
CONVERSATIONAL_MODEL = "qwen2.5:1.5b"  # Smaller model
TOP_K_RESULTS = 3  # Fewer results
QUERY_TIMEOUT = 2
RESPONSE_TIMEOUT = 8
```

**For Raspberry Pi 5 (8GB):**
```python
# config.py
CONVERSATIONAL_MODEL = "qwen2.5:3b"  # or even qwen2.5:7b
TOP_K_RESULTS = 5
QUERY_TIMEOUT = 1  # Faster retrieval
RESPONSE_TIMEOUT = 7  # Faster generation
```

**Storage Optimization:**
- Use SSD instead of microSD card for 3-5x faster I/O
- Mount SSD at `/home/pi/docubot/data`

**Network Optimization:**
- Use wired Ethernet for stable performance
- Consider static IP for easier access

### Monitoring Performance

**Check Query Latency:**
```bash
# View logs
tail -f logs/app.log | grep "Query processing time"
```

**Monitor Memory:**
```bash
# Real-time monitoring
watch -n 1 free -h

# Or use htop
htop
```

**Check Health Status:**
```bash
# Periodic health checks
watch -n 5 'curl -s http://localhost:8000/api/health | python3 -m json.tool'
```

---

## Security Considerations

### Network Security

1. **Firewall Configuration**
   ```bash
   # On Pi, allow only necessary ports
   sudo ufw enable
   sudo ufw allow ssh
   sudo ufw allow 8000/tcp
   ```

2. **Restrict Access by IP (Optional)**
   
   Edit config.py:
   ```python
   # Only allow access from specific network
   SERVER_HOST = "192.168.1.100"  # Pi's IP
   
   # Or use nginx as reverse proxy with IP restrictions
   ```

3. **Use HTTPS (Recommended for Production)**
   
   Set up nginx with SSL certificate:
   ```bash
   sudo apt install nginx certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

### Data Security

1. **Encrypt Export Packages**
   ```bash
   # On desktop, encrypt before transfer
   gpg --symmetric --cipher-algo AES256 pi_export.tar.gz
   
   # Transfer encrypted file
   scp pi_export.tar.gz.gpg pi@pi-hostname:~/docubot/
   
   # On Pi, decrypt
   gpg --decrypt pi_export.tar.gz.gpg > pi_export.tar.gz
   ```

2. **Secure SSH Access**
   ```bash
   # Use SSH keys instead of passwords
   ssh-keygen -t ed25519
   ssh-copy-id pi@pi-hostname
   
   # Disable password authentication
   sudo nano /etc/ssh/sshd_config
   # Set: PasswordAuthentication no
   sudo systemctl restart ssh
   ```

3. **Regular Updates**
   ```bash
   # Keep system updated
   sudo apt update && sudo apt upgrade -y
   
   # Update Python packages
   pip install --upgrade -r requirements.txt
   ```

### Application Security

1. **Add Authentication (Future Enhancement)**
   
   Consider adding API key authentication or OAuth for production deployments.

2. **Rate Limiting**
   
   Implement rate limiting to prevent abuse:
   ```python
   # In backend/api.py
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)
   
   @app.post("/api/query")
   @limiter.limit("10/minute")
   async def query_endpoint(...):
       ...
   ```

3. **Input Validation**
   
   Always validate user input to prevent injection attacks.

---

## Additional Resources

### Documentation
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Ollama Documentation](https://ollama.ai/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Sentence Transformers](https://www.sbert.net/)

### Community Support
- GitHub Issues: Report bugs and request features
- Discord/Slack: Join the community for help

### Performance Benchmarks

**Typical Performance (Pi 4 8GB with qwen2.5:3b):**
- Query retrieval: 1-2 seconds
- Response generation: 5-8 seconds
- Total query time: 6-10 seconds
- Concurrent users: 3-5
- Memory usage: 3-4GB

**Typical Performance (Pi 5 8GB with qwen2.5:3b):**
- Query retrieval: 0.5-1 seconds
- Response generation: 3-5 seconds
- Total query time: 3-6 seconds
- Concurrent users: 5-10
- Memory usage: 3-4GB

---

## Quick Reference

### Desktop Commands
```bash
# Process documents
python -m uvicorn backend.api:app --reload

# Create full export
python utils/export_for_pi.py

# Create incremental export
python utils/export_for_pi.py --incremental --since "2024-01-15T10:30:00"

# Check processing status
curl http://localhost:8000/api/processing/report
```

### Pi Commands
```bash
# Start server
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000

# Check health
curl http://localhost:8000/api/health

# Check data stats
curl http://localhost:8000/api/data/stats

# View logs
tail -f logs/app.log

# Monitor resources
htop
```

### Transfer Commands
```bash
# Transfer export package
scp pi_export.tar.gz pi@pi-hostname:~/docubot/

# Transfer with progress
rsync -avz --progress pi_export.tar.gz pi@pi-hostname:~/docubot/

# SSH into Pi
ssh pi@pi-hostname
```

---

## Support

If you encounter issues not covered in this guide:

1. Check the logs: `tail -f logs/app.log`
2. Review the troubleshooting section above
3. Check system resources: `htop`, `free -h`, `df -h`
4. Verify configuration: `python -c "from backend.config import Config; Config.validate()"`
5. Open an issue on GitHub with:
   - Error messages
   - System information (Pi model, RAM, OS version)
   - Configuration settings
   - Steps to reproduce

---

**Last Updated:** 2024-01-20
**Version:** 1.0
