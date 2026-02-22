# Desktop Testing Guide

Your system is now configured with the correct models. Here's how to test it:

## Prerequisites ✓

You've already pulled the required models:
- `mxbai-embed-large` (669 MB) - Embeddings
- `qwen2.5vl:7b` (6 GB) - Vision processing
- `qwen2.5:14b` (9 GB) - Text generation

## Step 1: Start Ollama

Make sure Ollama is running:

```powershell
ollama serve
```

Leave this terminal open.

## Step 2: Start the Backend Server

Open a new terminal in the project directory:

```powershell
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
```

The server will start and you should see:
- "Starting in DESKTOP mode (document processing enabled)"
- "API server initialized successfully in DESKTOP mode"

## Step 3: Open the Web Interface

Open your browser and go to:
```
http://localhost:3000
```

(If the frontend isn't running, start it with `npm run dev` in the `frontend` directory)

## Step 4: Test Document Processing

1. Click "Add Folder" in the web interface
2. Select a folder containing documents (PDFs, images, or text files)
3. Click "Process Documents"
4. Watch the progress as it processes your files

## Step 5: Test Querying

1. Create a new conversation
2. Ask questions about your documents
3. The system will:
   - Use `mxbai-embed-large` to embed your question
   - Search the vector store for relevant chunks
   - Use `qwen2.5:14b` to generate a response

## What's Happening Behind the Scenes

### Document Processing:
- **Text files (.txt)**: Extracted and chunked
- **PDFs**: Text extracted, then vision model processes pages with images/tables
- **Images**: Processed with `qwen2.5vl:7b` to extract structured data
- **Embeddings**: Generated with `mxbai-embed-large` (1024-dim)

### Vision Processing:
- Automatically detects document types (receipts, IDs, legal docs, etc.)
- Extracts structured data as key-value pairs
- Handles image orientation issues automatically

### GPU Usage:
Your RTX 4080 will be used for:
- Vision model inference (`qwen2.5vl:7b`)
- Text generation (`qwen2.5:14b`)
- Embedding generation (`mxbai-embed-large`)

## Monitoring GPU Usage

Open another terminal and run:

```powershell
nvidia-smi -l 1
```

This will show GPU utilization every second. You should see:
- Memory usage increase when processing documents
- GPU utilization spike during inference

## Troubleshooting

### "Ollama is not running"
- Make sure `ollama serve` is running in a terminal
- Check that Ollama is accessible at `http://localhost:11434`

### "Model not found"
- Verify models are installed: `ollama list`
- Re-pull if needed: `ollama pull qwen2.5vl:7b`

### Processing fails on certain images
- Some images may have orientation issues
- The system will automatically try all 4 rotations
- If it still fails, the image is blacklisted and skipped

### Slow processing
- First-time model loading takes longer
- Subsequent requests are faster (models stay in memory)
- Large PDFs with many images take longer to process

## Next Steps

Once you've verified everything works on your desktop:

1. Process all your documents
2. Export the data for Pi deployment:
   ```
   POST http://localhost:8000/api/export
   {
     "output_dir": "pi_export",
     "incremental": false
   }
   ```
3. Transfer the export package to your Raspberry Pi
4. Follow the Pi setup instructions in `DESKTOP_PI_USAGE_GUIDE.md`

## Configuration Files

All configuration is in `backend/config.py`:
- `OLLAMA_MODEL = "qwen2.5:14b"` - Text generation
- `OLLAMA_VISION_MODEL = "qwen2.5vl:7b"` - Vision processing
- `EMBEDDING_MODEL = "mxbai-embed-large"` - Embeddings
- `CONVERSATIONAL_MODEL = "qwen2.5:3b"` - For Pi export

You can override these with environment variables if needed.
