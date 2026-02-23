@echo off
echo ============================================================
echo Force Reset ChromaDB (Windows)
echo ============================================================
echo.

echo Step 1: Stopping any running Python processes...
taskkill /F /IM python.exe 2>nul
if %errorlevel% == 0 (
    echo   Stopped Python processes
    timeout /t 2 /nobreak >nul
) else (
    echo   No Python processes found
)
echo.

echo Step 2: Deleting ChromaDB directory...
if exist "data\chromadb" (
    rmdir /S /Q "data\chromadb"
    if exist "data\chromadb" (
        echo   Failed to delete - please close any programs using the database
        pause
        exit /b 1
    ) else (
        echo   Successfully deleted ChromaDB
    )
) else (
    echo   ChromaDB directory doesn't exist
)
echo.

echo ============================================================
echo ChromaDB Reset Complete!
echo ============================================================
echo.
echo Next steps:
echo 1. Start backend: python backend/main.py
echo 2. Open frontend: http://localhost:3000
echo 3. Re-process all document folders
echo 4. Test queries in Korean and English
echo 5. Sync to Raspberry Pi if quality is good
echo.
pause
