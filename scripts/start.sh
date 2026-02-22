#!/bin/bash
# RAG Chatbot Startup Script for macOS/Linux
# This script starts both the backend API server and frontend development server
# Run from project root: ./scripts/start.sh

# Change to project root directory
cd "$(dirname "$0")/.."

echo "========================================"
echo "RAG Chatbot with Vision - Starting..."
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.10 or higher from https://www.python.org/"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed"
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
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

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo ""
    echo "ERROR: Frontend dependencies not installed!"
    echo "Please run: cd frontend && npm install && cd .."
    echo ""
    exit 1
fi

# Create PID file directory
mkdir -p .pids

# Start backend server
echo ""
echo "Starting backend API server..."
python3 -m uvicorn backend.api:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > .pids/backend.pid
echo "Backend PID: $BACKEND_PID"

# Wait a moment for backend to start
sleep 3

# Start frontend server
echo "Starting frontend development server..."
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../.pids/frontend.pid
cd ..
echo "Frontend PID: $FRONTEND_PID"

echo ""
echo "========================================"
echo "RAG Chatbot is running!"
echo "========================================"
echo ""
echo "Backend API: http://localhost:8000"
echo "Frontend UI: http://localhost:5173"
echo ""
echo "Logs are being written to:"
echo "  - backend.log"
echo "  - frontend.log"
echo ""
echo "To stop the application, run: ./scripts/stop.sh"
echo ""
echo "Opening browser in 5 seconds..."
sleep 5

# Open browser (works on macOS and most Linux)
if command -v open &> /dev/null; then
    # macOS
    open http://localhost:5173
elif command -v xdg-open &> /dev/null; then
    # Linux
    xdg-open http://localhost:5173
fi

echo ""
echo "Application is running in the background!"
echo "Check backend.log and frontend.log for output."
