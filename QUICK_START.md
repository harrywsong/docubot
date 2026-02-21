# Quick Start Guide

## 🚀 Starting the Application

### Windows Users
1. Make sure Ollama is running (open a terminal and run `ollama serve`)
2. Double-click `start.bat`
3. Wait for the browser to open automatically
4. You're ready to go! 🎉

### macOS/Linux Users
1. Make sure Ollama is running (open a terminal and run `ollama serve`)
2. Open Terminal in the project folder and run:
   ```bash
   ./start.sh
   ```
3. Wait for the browser to open automatically
4. You're ready to go! 🎉

---

## 🛑 Stopping the Application

### Windows Users
Double-click `stop.bat`

### macOS/Linux Users
```bash
./stop.sh
```

---

## 🔧 First Time Setup

**IMPORTANT:** Run these commands before starting the application for the first time:

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install frontend dependencies:**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

3. **Download the vision model:**
   ```bash
   ollama pull qwen2.5-vl:7b
   ```

4. **Make scripts executable (macOS/Linux only):**
   ```bash
   chmod +x start.sh stop.sh check-setup.sh
   ```

5. **Verify setup (optional but recommended):**
   ```bash
   # Windows
   check-setup.bat
   
   # macOS/Linux
   ./check-setup.sh
   ```
   This will check if all dependencies are installed correctly.

---

## 🔧 Troubleshooting

### "Ollama is not running"
Open a terminal and run:
```bash
ollama serve
```
Keep this terminal open while using the application.

### "Python is not installed"
Download and install Python 3.10+ from https://www.python.org/

### "Node.js is not installed"
Download and install Node.js 18+ from https://nodejs.org/

### "Port already in use"
Run the stop script first:
- Windows: `stop.bat`
- macOS/Linux: `./stop.sh`

### Browser doesn't open automatically
Manually open your browser and go to: http://localhost:5173

---

## 📍 Important URLs

- **Application**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs

---

## 💡 Creating Desktop Shortcuts (Optional)

### Windows
1. Right-click `start.bat` → Send to → Desktop (create shortcut)
2. Rename to "Start RAG Chatbot"
3. Repeat for `stop.bat`

### macOS
1. Right-click `start.sh` → Make Alias
2. Drag to Desktop
3. Rename to "Start RAG Chatbot"
4. Repeat for `stop.sh`

### Linux
Create a desktop entry file in `~/.local/share/applications/`:
```ini
[Desktop Entry]
Name=Start RAG Chatbot
Exec=/full/path/to/start.sh
Path=/full/path/to/project
Terminal=true
Type=Application
```

---

## 📚 Need More Help?

Check **README.md** for:
- Detailed installation instructions
- Full API documentation
- Development guide
- Advanced troubleshooting
