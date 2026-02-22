#!/bin/bash
# Raspberry Pi Setup Script
# Run this on your Raspberry Pi after transferring the export package

set -e

echo "=========================================="
echo "Desktop-Pi RAG Pipeline - Pi Setup"
echo "=========================================="
echo ""

# Configuration
APP_DIR="${APP_DIR:-$HOME/rag-chatbot}"
DATA_DIR="$APP_DIR/data"

# Check if we're in an export package directory
if [ ! -f "manifest.json" ]; then
    echo "Error: manifest.json not found in current directory"
    echo "Please run this script from the extracted export package directory"
    exit 1
fi

echo "Found export package in current directory"
echo ""

# Step 1: Create directory structure
echo "Step 1: Creating directory structure..."
mkdir -p "$DATA_DIR"
echo "✓ Created $DATA_DIR"
echo ""

# Step 2: Copy data files
echo "Step 2: Copying data files..."

if [ -d "chromadb" ]; then
    echo "Copying ChromaDB vector store..."
    rm -rf "$DATA_DIR/chromadb"
    cp -r chromadb "$DATA_DIR/"
    echo "✓ Copied vector store"
else
    echo "✗ Warning: chromadb directory not found"
fi

if [ -f "app.db" ]; then
    echo "Copying SQLite database..."
    cp app.db "$DATA_DIR/"
    echo "✓ Copied database"
else
    echo "✗ Warning: app.db not found"
fi

if [ -f "manifest.json" ]; then
    echo "Copying manifest..."
    cp manifest.json "$DATA_DIR/"
    echo "✓ Copied manifest"
else
    echo "✗ Warning: manifest.json not found"
fi

echo ""

# Step 3: Check if application code exists
echo "Step 3: Checking application code..."
if [ ! -d "$APP_DIR/backend" ]; then
    echo "⚠ Warning: Application code not found at $APP_DIR"
    echo ""
    echo "You need to copy your application code to the Pi:"
    echo "  From your desktop, run:"
    echo "  rsync -avz --exclude 'data' --exclude '__pycache__' --exclude '*.pyc' \\"
    echo "    backend/ frontend/ requirements.txt \\"
    echo "    pi@raspberrypi.local:$APP_DIR/"
    echo ""
    read -p "Press Enter when application code is in place..."
fi

if [ -d "$APP_DIR/backend" ]; then
    echo "✓ Application code found"
else
    echo "✗ Application code still not found. Please copy it manually."
    exit 1
fi
echo ""

# Step 4: Update configuration
echo "Step 4: Updating configuration..."
if [ -f "config_pi.py" ] && [ -d "$APP_DIR/backend" ]; then
    echo "Copying Pi configuration..."
    cp config_pi.py "$APP_DIR/backend/config.py"
    echo "✓ Configuration updated"
else
    echo "⚠ Warning: config_pi.py not found or backend directory missing"
    echo "You may need to manually configure backend/config.py"
fi
echo ""

# Step 5: Check Ollama and model
echo "Step 5: Checking Ollama and models..."

if ! command -v ollama &> /dev/null; then
    echo "✗ Ollama not found. Install it with:"
    echo "  curl -fsSL https://ollama.ai/install.sh | sh"
    exit 1
fi
echo "✓ Ollama is installed"

# Check if model is available
REQUIRED_MODEL=$(jq -r '.pi_requirements.conversational_model' manifest.json)
echo "Checking for model: $REQUIRED_MODEL"

if ! ollama list | grep -q "$REQUIRED_MODEL"; then
    echo "⚠ Model $REQUIRED_MODEL not found"
    echo "Pulling model (this may take a few minutes)..."
    ollama pull "$REQUIRED_MODEL"
fi
echo "✓ Model $REQUIRED_MODEL is available"
echo ""

# Step 6: Check Python dependencies
echo "Step 6: Checking Python dependencies..."
if [ -f "$APP_DIR/requirements.txt" ]; then
    echo "Installing/updating Python dependencies..."
    pip install -q -r "$APP_DIR/requirements.txt"
    echo "✓ Dependencies installed"
else
    echo "⚠ Warning: requirements.txt not found"
fi
echo ""

# Step 7: Validate manifest
echo "Step 7: Validating manifest..."
EMBEDDING_DIM=$(jq -r '.pi_requirements.embedding_dimension' manifest.json)
MIN_MEMORY=$(jq -r '.pi_requirements.min_memory_gb' manifest.json)
TOTAL_CHUNKS=$(jq -r '.statistics.total_chunks' manifest.json)

echo "  Embedding dimension: $EMBEDDING_DIM"
echo "  Minimum memory: ${MIN_MEMORY}GB"
echo "  Total chunks: $TOTAL_CHUNKS"

# Check available memory
AVAILABLE_MEMORY=$(free -g | awk '/^Mem:/{print $2}')
if [ "$AVAILABLE_MEMORY" -lt "$MIN_MEMORY" ]; then
    echo "⚠ Warning: System has ${AVAILABLE_MEMORY}GB RAM, but ${MIN_MEMORY}GB recommended"
else
    echo "✓ Memory requirements met (${AVAILABLE_MEMORY}GB available)"
fi
echo ""

# Step 8: Create systemd service (optional)
echo "Step 8: Setting up systemd service (optional)..."
read -p "Create systemd service for auto-start? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    SERVICE_FILE="/etc/systemd/system/rag-chatbot.service"
    
    echo "Creating service file..."
    sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=RAG Chatbot Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3 -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable rag-chatbot
    echo "✓ Service created and enabled"
    echo ""
    echo "Service commands:"
    echo "  Start:   sudo systemctl start rag-chatbot"
    echo "  Stop:    sudo systemctl stop rag-chatbot"
    echo "  Status:  sudo systemctl status rag-chatbot"
    echo "  Logs:    sudo journalctl -u rag-chatbot -f"
fi
echo ""

# Step 9: Start server
echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Data location: $DATA_DIR"
echo "Application: $APP_DIR"
echo ""
echo "To start the server:"
echo "  cd $APP_DIR"
echo "  python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000"
echo ""
echo "Or if you created the systemd service:"
echo "  sudo systemctl start rag-chatbot"
echo ""

read -p "Start server now? (Y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    cd "$APP_DIR"
    echo "Starting server..."
    echo "Access the web interface at: http://$(hostname -I | awk '{print $1}'):8000"
    echo ""
    python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
fi
