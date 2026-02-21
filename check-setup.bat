@echo off
REM Setup verification script for Windows

echo ========================================
echo RAG Chatbot - Setup Verification
echo ========================================
echo.

set ERRORS=0

REM Check Python
echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] Python is not installed
    set ERRORS=1
) else (
    python --version
    echo   [OK] Python is installed
)
echo.

REM Check Node.js
echo [2/5] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] Node.js is not installed
    set ERRORS=1
) else (
    node --version
    echo   [OK] Node.js is installed
)
echo.

REM Check Python dependencies
echo [3/5] Checking Python dependencies...
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] Python dependencies not installed
    echo   Run: pip install -r requirements.txt
    set ERRORS=1
) else (
    echo   [OK] Python dependencies installed
)
echo.

REM Check frontend dependencies
echo [4/5] Checking frontend dependencies...
if not exist "frontend\node_modules\" (
    echo   [FAIL] Frontend dependencies not installed
    echo   Run: cd frontend ^&^& npm install ^&^& cd ..
    set ERRORS=1
) else (
    echo   [OK] Frontend dependencies installed
)
echo.

REM Check Ollama
echo [5/5] Checking Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo   [WARN] Ollama is not running
    echo   Start with: ollama serve
) else (
    echo   [OK] Ollama is running
)
echo.

echo ========================================
if %ERRORS%==0 (
    echo Setup verification PASSED!
    echo You can now run: start.bat
) else (
    echo Setup verification FAILED!
    echo Please fix the errors above before running start.bat
)
echo ========================================
echo.
pause
