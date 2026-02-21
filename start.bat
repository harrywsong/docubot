@echo off
REM RAG Chatbot Startup Script for Windows
REM This script starts both the backend API and frontend dev server

echo.
echo Starting RAG Chatbot...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Check if Node.js is available
node --version >nul 2>&1
if errorlevel 1 (
    echo Node.js is not installed. Please install Node.js 18 or higher.
    pause
    exit /b 1
)

REM Check if backend dependencies are installed
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

REM Check if frontend dependencies are installed
if not exist "frontend\node_modules\" (
    echo Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

echo.
echo Dependencies ready
echo.

REM Start backend
echo Starting backend API on http://127.0.0.1:8000...
start "RAG Chatbot Backend" cmd /k "venv\Scripts\activate.bat && python -m uvicorn backend.api:app --host 127.0.0.1 --port 8000"

REM Wait for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend
echo Starting frontend on http://localhost:3000...
cd frontend
start "RAG Chatbot Frontend" cmd /k "npm run dev"
cd ..

echo.
echo RAG Chatbot is running!
echo.
echo Frontend: http://localhost:3000
echo Backend API: http://127.0.0.1:8000
echo API Docs: http://127.0.0.1:8000/docs
echo.
echo Close the terminal windows to stop the services
echo.

pause
