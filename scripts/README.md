# Scripts Directory

This directory contains startup, shutdown, and setup scripts for the RAG Chatbot application.

## Available Scripts

### Startup Scripts

- **start.bat** (Windows) - Starts both backend and frontend servers
- **start.sh** (macOS/Linux) - Starts both backend and frontend servers

Usage:
```bash
# Windows
scripts\start.bat

# macOS/Linux
./scripts/start.sh
```

### Shutdown Scripts

- **stop.bat** (Windows) - Stops all running servers
- **stop.sh** (macOS/Linux) - Stops all running servers

Usage:
```bash
# Windows
scripts\stop.bat

# macOS/Linux
./scripts/stop.sh
```

### Setup Verification Scripts

- **check-setup.bat** (Windows) - Verifies all dependencies are installed
- **check-setup.sh** (macOS/Linux) - Verifies all dependencies are installed

Usage:
```bash
# Windows
scripts\check-setup.bat

# macOS/Linux
./scripts/check-setup.sh
```

### Setup Scripts

- **setup_poppler.ps1** (Windows PowerShell) - Installs Poppler for PDF processing

Usage:
```powershell
# Windows PowerShell (run as Administrator)
.\scripts\setup_poppler.ps1
```

## Notes

- All scripts should be run from the project root directory
- The scripts automatically change to the project root before executing
- Frontend runs on port 5173 (Vite default)
- Backend API runs on port 8000
