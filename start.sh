#!/bin/bash

# RAG Chatbot Startup Script
# This script starts both the backend API and frontend dev server

echo "🚀 Starting RAG Chatbot..."
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18 or higher."
    exit 1
fi

# Check if backend dependencies are installed
if [ ! -d "venv" ] && [ ! -f ".venv/bin/activate" ]; then
    echo "⚠️  Virtual environment not found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate 2>/dev/null || source .venv/bin/activate 2>/dev/null
fi

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

echo ""
echo "✅ Dependencies ready"
echo ""

# Start backend in background
echo "🔧 Starting backend API on http://127.0.0.1:8000..."
python3 -m uvicorn backend.api:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend in background
echo "🎨 Starting frontend on http://localhost:3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✨ RAG Chatbot is running!"
echo ""
echo "📍 Frontend: http://localhost:3000"
echo "📍 Backend API: http://127.0.0.1:8000"
echo "📍 API Docs: http://127.0.0.1:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for Ctrl+C
trap "echo ''; echo '🛑 Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT

# Keep script running
wait
