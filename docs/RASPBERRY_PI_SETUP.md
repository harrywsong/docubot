# Raspberry Pi Setup Guide

Quick guide to set up DocuBot on your Raspberry Pi in read-only mode.

## Prerequisites

- Raspberry Pi with Raspberry Pi OS installed
- SSH enabled on Pi
- Network connection
- Ollama installed on Pi

## Setup Steps

### 1. Clone Repository

```bash
ssh hws@192.168.1.139
cd ~
git clone <your-repo-url> docubot
cd docubot
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create Configuration

The start script will create a default `.env` file, or you can create it manually:

```bash
nano .env
```

Add this content:

```bash
# Raspberry Pi Configuration (Read-Only Mode)
ENABLE_DOCUMENT_PROCESSING=false

# Ollama Configuration (local models)
OLLAMA_ENDPOINT=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
EMBEDDING_MODEL=qwen3-embedding:8b

# Use local models (no Groq)
USE_GROQ=false
```

### 5. Create Data Directory

```bash
mkdir -p data/chromadb
```

### 6. Make Scripts Executable

```bash
chmod +x scripts/start_pi.sh
chmod +x scripts/stop.sh
```

### 7. Start Ollama

In a separate terminal or screen session:

```bash
ollama serve
```

### 8. Pull Required Models

```bash
ollama pull qwen2.5:7b
ollama pull qwen3-embedding:8b
```

### 9. Start DocuBot

```bash
./scripts/start_pi.sh
```

## Usage

### Starting the Application

```bash
cd ~/docubot
./scripts/start_pi.sh
```

### Stopping the Application

```bash
cd ~/docubot
./scripts/stop.sh
```

### Viewing Logs

```bash
tail -f backend.log
```

### Syncing Data from PC

1. On your desktop PC, open DocuBot
2. Go to Documents tab
3. Click "Sync to Raspberry Pi"
4. Data will be copied to Pi automatically

## Accessing from Other Devices

Once running, you can access DocuBot from any device on your network:

```
http://192.168.1.139:8000
```

Replace `192.168.1.139` with your Pi's actual IP address.

## Troubleshooting

### "Virtual environment not found"

```bash
cd ~/docubot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### "Ollama is not running"

```bash
# Start Ollama in a separate terminal
ollama serve

# Or run in background
nohup ollama serve > ollama.log 2>&1 &
```

### "Port 8000 already in use"

```bash
# Find and kill the process
lsof -ti:8000 | xargs kill -9
```

### Check if service is running

```bash
curl http://localhost:8000/api/health
```

## Auto-Start on Boot (Optional)

To make DocuBot start automatically when Pi boots:

### Create systemd service

```bash
sudo nano /etc/systemd/system/docubot.service
```

Add this content:

```ini
[Unit]
Description=DocuBot RAG Chatbot
After=network.target

[Service]
Type=simple
User=hws
WorkingDirectory=/home/hws/docubot
ExecStart=/home/hws/docubot/venv/bin/python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable docubot
sudo systemctl start docubot
```

Check status:

```bash
sudo systemctl status docubot
```

View logs:

```bash
sudo journalctl -u docubot -f
```

## Performance Tips

1. **Use wired Ethernet** instead of WiFi for better performance
2. **Overclock your Pi** (if using Pi 4 or 5) for faster model inference
3. **Use a good power supply** (official Pi power supply recommended)
4. **Keep Pi cool** with heatsinks or fan
5. **Use SSD instead of SD card** for faster I/O

## Memory Management

The Pi has limited RAM. Monitor memory usage:

```bash
free -h
htop
```

If running out of memory:
- Reduce `OLLAMA_NUM_PARALLEL` in Ollama settings
- Use smaller models
- Increase swap space

## Next Steps

- Set up the sync from your desktop PC (see `RASPBERRY_PI_SYNC.md`)
- Configure auto-start on boot
- Set up remote access (port forwarding, VPN, etc.)
