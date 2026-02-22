#!/bin/bash
# RAG Chatbot Shutdown Script for macOS/Linux
# This script stops both the backend API server and frontend development server
# Run from project root: ./scripts/stop.sh

# Change to project root directory
cd "$(dirname "$0")/.."

echo "========================================"
echo "RAG Chatbot with Vision - Stopping..."
echo "========================================"
echo ""

# Function to kill process and its children
kill_process_tree() {
    local pid=$1
    if [ -n "$pid" ]; then
        # Get all child processes
        local children=$(pgrep -P $pid)
        
        # Kill children first
        for child in $children; do
            kill_process_tree $child
        done
        
        # Kill the process itself
        if ps -p $pid > /dev/null 2>&1; then
            echo "Stopping process $pid..."
            kill $pid 2>/dev/null
            sleep 1
            # Force kill if still running
            if ps -p $pid > /dev/null 2>&1; then
                kill -9 $pid 2>/dev/null
            fi
        fi
    fi
}

# Stop backend server
if [ -f .pids/backend.pid ]; then
    BACKEND_PID=$(cat .pids/backend.pid)
    echo "Stopping backend API server (PID: $BACKEND_PID)..."
    kill_process_tree $BACKEND_PID
    rm .pids/backend.pid
else
    echo "Backend PID file not found, trying to find process..."
    # Try to find and kill by port
    BACKEND_PID=$(lsof -ti:8000)
    if [ -n "$BACKEND_PID" ]; then
        echo "Found backend on port 8000 (PID: $BACKEND_PID)"
        kill_process_tree $BACKEND_PID
    fi
fi

# Stop frontend server (check both port 3000 and 5173)
if [ -f .pids/frontend.pid ]; then
    FRONTEND_PID=$(cat .pids/frontend.pid)
    echo "Stopping frontend development server (PID: $FRONTEND_PID)..."
    kill_process_tree $FRONTEND_PID
    rm .pids/frontend.pid
else
    echo "Frontend PID file not found, trying to find process..."
    # Try to find and kill by port (Vite uses 5173 by default)
    FRONTEND_PID=$(lsof -ti:5173)
    if [ -n "$FRONTEND_PID" ]; then
        echo "Found frontend on port 5173 (PID: $FRONTEND_PID)"
        kill_process_tree $FRONTEND_PID
    else
        # Also check port 3000 for older setups
        FRONTEND_PID=$(lsof -ti:3000)
        if [ -n "$FRONTEND_PID" ]; then
            echo "Found frontend on port 3000 (PID: $FRONTEND_PID)"
            kill_process_tree $FRONTEND_PID
        fi
    fi
fi

# Clean up PID directory if empty
if [ -d .pids ] && [ -z "$(ls -A .pids)" ]; then
    rmdir .pids
fi

echo ""
echo "========================================"
echo "RAG Chatbot has been stopped!"
echo "========================================"
echo ""
echo "All servers have been shut down."
echo ""
