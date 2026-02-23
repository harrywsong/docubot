@echo off
REM Configure Ollama on Raspberry Pi via SSH from Windows

echo ============================================================
echo Configure Ollama on Raspberry Pi 5
echo ============================================================
echo.

REM Check if WSL is available
wsl --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: WSL is not installed or not available
    echo.
    echo Please install WSL or run the commands manually on the Pi:
    echo   1. SSH to Pi: ssh hws@192.168.1.139
    echo   2. Run: bash ~/docubot/scripts/configure_pi_ollama.sh
    echo.
    pause
    exit /b 1
)

echo Copying configuration script to Pi...
wsl scp scripts/configure_pi_ollama.sh hws@192.168.1.139:~/docubot/scripts/
if errorlevel 1 (
    echo ERROR: Failed to copy script to Pi
    echo Make sure you can SSH to the Pi without password
    pause
    exit /b 1
)
echo.

echo Making script executable...
wsl ssh hws@192.168.1.139 "chmod +x ~/docubot/scripts/configure_pi_ollama.sh"
echo.

echo Running configuration script on Pi...
echo This will prompt for your Pi password (for sudo)
echo.
wsl ssh -t hws@192.168.1.139 "cd ~/docubot && ./scripts/configure_pi_ollama.sh"
echo.

echo ============================================================
echo Configuration Complete!
echo ============================================================
echo.
echo Next steps:
echo   1. Update Pi .env: OLLAMA_MODEL=qwen2.5:1.5b
echo   2. Restart Pi backend
echo   3. Test queries
echo.
pause
