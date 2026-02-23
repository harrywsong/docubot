#!/bin/bash
# Configure Ollama on Raspberry Pi 5 for optimal performance
# This script sets memory limits and model loading constraints

echo "============================================================"
echo "Configuring Ollama for Raspberry Pi 5"
echo "============================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "This script needs sudo privileges to configure systemd."
    echo "It will prompt for your password."
    echo ""
fi

# Create systemd override directory
echo "Step 1: Creating systemd override directory..."
sudo mkdir -p /etc/systemd/system/ollama.service.d
echo "✓ Directory created"
echo ""

# Create override configuration
echo "Step 2: Creating Ollama configuration..."
sudo tee /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
# Limit to 1 model loaded at a time (Pi 5 has limited RAM)
Environment="OLLAMA_MAX_LOADED_MODELS=1"

# Allow 2 parallel requests (balance between throughput and memory)
Environment="OLLAMA_NUM_PARALLEL=2"

# Limit request queue to prevent memory exhaustion
Environment="OLLAMA_MAX_QUEUE=5"

# Hard memory limit - Ollama will be killed if it exceeds this
MemoryMax=6G

# Soft memory limit - Ollama will be throttled if it exceeds this
MemoryHigh=5G
EOF

echo "✓ Configuration created at /etc/systemd/system/ollama.service.d/override.conf"
echo ""

# Reload systemd
echo "Step 3: Reloading systemd daemon..."
sudo systemctl daemon-reload
echo "✓ Systemd reloaded"
echo ""

# Restart Ollama
echo "Step 4: Restarting Ollama service..."
sudo systemctl restart ollama
echo "✓ Ollama restarted"
echo ""

# Wait for Ollama to start
echo "Step 5: Waiting for Ollama to start..."
sleep 3
echo ""

# Check Ollama status
echo "Step 6: Checking Ollama status..."
if sudo systemctl is-active --quiet ollama; then
    echo "✓ Ollama is running"
else
    echo "✗ Ollama failed to start"
    echo "  Check logs with: sudo journalctl -u ollama -n 50"
    exit 1
fi
echo ""

# Pull qwen2.5:1.5b model
echo "Step 7: Pulling qwen2.5:1.5b model..."
echo "  This will download ~986 MB"
echo ""
ollama pull qwen2.5:1.5b
echo ""
echo "✓ Model downloaded"
echo ""

# Verify configuration
echo "============================================================"
echo "Configuration Complete!"
echo "============================================================"
echo ""
echo "Ollama is now configured with:"
echo "  - Max loaded models: 1"
echo "  - Parallel requests: 2"
echo "  - Max queue: 5"
echo "  - Memory limit (hard): 6G"
echo "  - Memory limit (soft): 5G"
echo ""
echo "Model installed:"
echo "  - qwen2.5:1.5b (986 MB)"
echo ""
echo "Next steps:"
echo "  1. Update .env on Pi: OLLAMA_MODEL=qwen2.5:1.5b"
echo "  2. Restart Pi backend: ./scripts/start_pi.sh"
echo "  3. Test queries and monitor performance"
echo ""
echo "To monitor Ollama:"
echo "  - Logs: sudo journalctl -u ollama -f"
echo "  - Memory: watch -n 1 free -h"
echo "  - Process: htop (filter for 'ollama')"
echo ""
