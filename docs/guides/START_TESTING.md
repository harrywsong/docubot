# Quick Start - Testing Commands

## Terminal 1: Start Ollama

```powershell
ollama serve
```

Keep this running. You should see:
```
Ollama is running
```

## Terminal 2: Start Backend Server

```powershell
cd E:\codingprojects\docubot
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
```

Wait for:
```
Starting in DESKTOP mode (document processing enabled)
API server initialized successfully in DESKTOP mode
```

## Terminal 3: Monitor GPU (Optional)

```powershell
nvidia-smi -l 1
```

This shows GPU usage in real-time.

## Browser: Open Web Interface

Navigate to:
```
http://localhost:3000
```

If frontend isn't running, start it first:
```powershell
cd frontend
npm run dev
```

## Test Workflow

1. **Add a folder** with some test documents
2. **Click "Process Documents"**
3. **Wait for processing to complete**
4. **Create a conversation**
5. **Ask questions** about your documents

## Example Test Documents

Create a test folder with:
- A PDF file
- A text file
- An image (receipt, ID, or any document photo)

## What to Watch For

### In Terminal 2 (Backend):
```
Processing text file: example.pdf
Extracted 5 text chunks from PDF
Processing image file: receipt.jpg
Successfully processed receipt.jpg
```

### In Terminal 3 (GPU Monitor):
```
GPU Memory: 8000MB / 16384MB
GPU Utilization: 85%
```

### In Browser:
- Progress bar showing processing status
- Success message when complete
- Responses to your queries with source citations

## Quick Health Check

Before processing, check system health:

```powershell
curl http://localhost:8000/api/health
```

Should return:
```json
{
  "status": "healthy",
  "ollama_available": true,
  "model_available": true,
  "vector_store_loaded": true
}
```

## Stop Everything

When done testing:

1. **Terminal 1**: `Ctrl+C` to stop Ollama
2. **Terminal 2**: `Ctrl+C` to stop backend
3. **Terminal 3**: `Ctrl+C` to stop GPU monitor
4. **Browser**: Close the tab

## Troubleshooting

### Backend won't start
- Check Python version: `python --version` (need 3.8+)
- Install dependencies: `pip install -r requirements.txt`

### Ollama not responding
- Check if running: `ollama list`
- Restart: Stop with `Ctrl+C`, then `ollama serve` again

### Models not found
- List models: `ollama list`
- Should see: `qwen2.5:14b`, `qwen2.5vl:7b`, `mxbai-embed-large`

### Frontend not loading
- Check if running: Look for "Local: http://localhost:3000"
- Start it: `cd frontend && npm run dev`

## Ready for Pi Deployment?

Once desktop testing is successful:

1. Process all your documents
2. Create export package:
   ```powershell
   curl -X POST http://localhost:8000/api/export -H "Content-Type: application/json" -d "{\"output_dir\": \"pi_export\", \"incremental\": false}"
   ```
3. Transfer `pi_export.tar.gz` to your Raspberry Pi
4. Follow Pi setup instructions

See `DESKTOP_PI_USAGE_GUIDE.md` for complete deployment workflow.
