#!/bin/bash
# Setup verification script for macOS/Linux
# Run from project root: ./scripts/check-setup.sh

# Change to project root directory
cd "$(dirname "$0")/.."

echo "========================================"
echo "RAG Chatbot - Setup Verification"
echo "========================================"
echo ""

ERRORS=0

# Check Python
echo "[1/5] Checking Python..."
if command -v python3 &> /dev/null; then
    python3 --version
    echo "  [OK] Python is installed"
else
    echo "  [FAIL] Python is not installed"
    ERRORS=1
fi
echo ""

# Check Node.js
echo "[2/5] Checking Node.js..."
if command -v node &> /dev/null; then
    node --version
    echo "  [OK] Node.js is installed"
else
    echo "  [FAIL] Node.js is not installed"
    ERRORS=1
fi
echo ""

# Check Python dependencies
echo "[3/5] Checking Python dependencies..."
if python3 -c "import fastapi" 2>/dev/null; then
    echo "  [OK] Python dependencies installed"
else
    echo "  [FAIL] Python dependencies not installed"
    echo "  Run: pip install -r requirements.txt"
    ERRORS=1
fi
echo ""

# Check frontend dependencies
echo "[4/5] Checking frontend dependencies..."
if [ -d "frontend/node_modules" ]; then
    echo "  [OK] Frontend dependencies installed"
else
    echo "  [FAIL] Frontend dependencies not installed"
    echo "  Run: cd frontend && npm install && cd .."
    ERRORS=1
fi
echo ""

# Check Ollama
echo "[5/5] Checking Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "  [OK] Ollama is running"
else
    echo "  [WARN] Ollama is not running"
    echo "  Start with: ollama serve"
fi
echo ""

echo "========================================"
if [ $ERRORS -eq 0 ]; then
    echo "Setup verification PASSED!"
    echo "You can now run: ./scripts/start.sh"
else
    echo "Setup verification FAILED!"
    echo "Please fix the errors above before running ./scripts/start.sh"
fi
echo "========================================"
echo ""
