#!/bin/bash
# RAG Chatbot Startup Script for Raspberry Pi (Backend + Frontend)
# This script starts both the backend API server and frontend in read-only mode
# Run from project root: ./scripts/start_pi.sh

# Change to project root directory
cd "$(dirname "$0")/.."

echo "========================================"
echo "RAG Chatbot - Raspberry Pi Mode"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.10 or higher"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed"
    echo "Please install Node.js from https://nodejs.org/"
    echo "Or run: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "WARNING: Virtual environment not found!"
    echo "Please create one with: python3 -m venv venv"
    echo "Then install dependencies: source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if Ollama is running
echo "Checking Ollama status..."
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo ""
    echo "WARNING: Ollama is not running!"
    echo "Please start Ollama before continuing."
    echo ""
    echo "To start Ollama:"
    echo "  1. Open a new terminal"
    echo "  2. Run: ollama serve"
    echo ""
    read -p "Press Enter to continue anyway, or Ctrl+C to exit..."
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo ""
    echo "WARNING: .env file not found!"
    echo "Creating default .env for Raspberry Pi..."
    cat > .env << 'EOF'
# Raspberry Pi Configuration (Read-Only Mode)
ENABLE_DOCUMENT_PROCESSING=false

# Ollama Configuration (local models)
OLLAMA_ENDPOINT=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
EMBEDDING_MODEL=qwen3-embedding:8b

# Use local models (no Groq)
USE_GROQ=false
EOF
    echo ".env file created!"
fi

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo ""
    echo "ERROR: Frontend dependencies not installed!"
    echo "Please run: cd frontend && npm install && cd .."
    echo ""
    exit 1
fi

# Create data directory if it doesn't exist
mkdir -p data/chromadb

# Create PID file directory
mkdir -p .pids

# Start backend server
echo ""
echo "Starting backend API server (read-only mode)..."
python3 -m uvicorn backend.api:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > .pids/backend.pid
echo "Backend PID: $BACKEND_PID"

# Wait a moment for backend to start
sleep 3

# Start frontend server
echo "Starting frontend development server..."
cd frontend
npm run dev -- --host 0.0.0.0 > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../.pids/frontend.pid
cd ..
echo "Frontend PID: $FRONTEND_PID"

echo ""
echo "========================================"
echo "RAG Chatbot is running on Raspberry Pi!"
echo "========================================"
echo ""
echo "Backend API: http://localhost:8000"
echo "Frontend UI: http://localhost:3000"
echo ""
echo "Access from other devices:"
echo "  http://$(hostname -I | awk '{print $1}'):3000"
echo ""
echo "Mode: READ-ONLY (document processing disabled)"
echo ""
echo "Logs are being written to:"
echo "  - backend.log"
echo "  - frontend.log"
echo ""
echo "To stop the application, run: ./scripts/stop.sh"
echo ""
echo "To sync data from your PC, run the 'Sync to Raspberry Pi' button"
echo "in the Documents tab on your desktop application."
echo ""
