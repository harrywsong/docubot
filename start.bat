@echo off
REM RAG Chatbot Startup Script for Windows
REM This script starts both the backend API server and frontend development server

echo ========================================
echo RAG Chatbot with Vision - Starting...
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10 or higher from https://www.python.org/
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

REM Check if Ollama is running
echo Checking Ollama status...
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo.
    echo WARNING: Ollama is not running!
    echo Please start Ollama before continuing.
    echo.
    echo To start Ollama:
    echo   1. Open a new terminal
    echo   2. Run: ollama serve
    echo.
    pause
)

REM Start backend server
echo.
echo Starting backend API server...
start "RAG Chatbot - Backend" cmd /k "python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000"

REM Wait a moment for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend server
echo Starting frontend development server...
cd frontend
start "RAG Chatbot - Frontend" cmd /k "npm run dev"
cd ..

echo.
echo ========================================
echo RAG Chatbot is starting!
echo ========================================
echo.
echo Backend API: http://localhost:8000
echo Frontend UI: http://localhost:5173
echo.
echo Two terminal windows have been opened:
echo   1. Backend API Server
echo   2. Frontend Development Server
echo.
echo To stop the application, run: stop.bat
echo Or close both terminal windows manually.
echo.
echo Opening browser in 5 seconds...
timeout /t 5 /nobreak >nul

REM Open browser
start http://localhost:5173

echo.
echo Application is running!
echo Press any key to close this window (servers will keep running)...
pause >nul
