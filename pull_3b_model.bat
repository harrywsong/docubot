@echo off
echo Pulling qwen2.5:3b model from Ollama...
echo This may take a few minutes depending on your internet connection.
echo.

ollama pull qwen2.5:3b

echo.
echo Model pulled successfully!
echo You can now restart the backend server to use the new model.
pause
