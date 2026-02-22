@echo off
REM RAG Chatbot Shutdown Script for Windows
REM This script stops both the backend API server and frontend development server

echo ========================================
echo RAG Chatbot with Vision - Stopping...
echo ========================================
echo.

REM Kill backend server (Python/Uvicorn on port 8000)
echo Stopping backend API server...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Kill frontend server (Node/Vite on port 3000)
echo Stopping frontend development server...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Close any terminal windows with our titles
taskkill /FI "WINDOWTITLE eq RAG Chatbot - Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq RAG Chatbot - Frontend*" /F >nul 2>&1

echo.
echo ========================================
echo RAG Chatbot has been stopped!
echo ========================================
echo.
echo All servers have been shut down.
echo You can now safely close this window.
echo.
pause
