# GPU Verification Guide

## Understanding GPU Usage

Your system has **two separate GPU acceleration paths**:

### 1. Ollama (Primary - Handles GPU Automatically)
- **Models**: `qwen2.5:14b`, `qwen2.5vl:7b`, `mxbai-embed-large`
- **GPU**: Ollama automatically detects and uses your RTX 4080
- **No configuration needed** - works out of the box

### 2. PyTorch/Sentence-Transformers (Fallback Only)
- **Only used if Ollama is unavailable**
- **Requires CUDA setup** for GPU acceleration
- **You won't use this** since Ollama is working

## The "No GPU Acceleration" Message

If you see this message during startup:
```
No GPU acceleration available, using CPU
```

**Don't worry!** This is just PyTorch checking for CUDA, but it's **not relevant** because:
- ✅ You're using Ollama for embeddings (not sentence-transformers)
- ✅ Ollama handles GPU acceleration automatically
- ✅ Your RTX 4080 is being used by Ollama

## Verify Ollama is Using Your GPU

### Method 1: Watch GPU Usage in Real-Time

Open a terminal and run:
```powershell
nvidia-smi -l 1
```

Then start processing documents. You should see:
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.xx       Driver Version: 535.xx       CUDA Version: 12.x   |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  NVIDIA GeForce ...  Off  | 00000000:01:00.0  On |                  N/A |
| 30%   45C    P2    85W / 320W |   6543MiB / 16384MiB |     87%      Default |
+-------------------------------+----------------------+----------------------+
```

**What to look for:**
- **Memory-Usage**: Should increase when processing (4-8GB)
- **GPU-Util**: Should spike to 60-95% during inference
- **Power Usage**: Should increase significantly

### Method 2: Check Ollama Logs

Ollama logs show GPU usage. Run:
```powershell
ollama ps
```

You should see your models loaded with GPU memory:
```
NAME                    ID              SIZE      PROCESSOR    UNTIL
qwen2.5vl:7b           abc123def       6.0 GB    100% GPU     4 minutes from now
mxbai-embed-large      def456ghi       669 MB    100% GPU     4 minutes from now
```

**"100% GPU"** means Ollama is using your GPU!

### Method 3: Check Backend Logs

When you start the backend, look for:
```
✓ Using Ollama for embeddings: mxbai-embed-large
✓ Ollama handles GPU acceleration automatically
```

This confirms Ollama is being used (not the CPU fallback).

## Performance Indicators

### With GPU (Expected):
- **Image processing**: 2-3 seconds per image
- **PDF processing**: 5-10 seconds for 10 pages
- **Embedding generation**: <1 second for batch of 32 texts
- **Query response**: 1-2 seconds

### Without GPU (Much Slower):
- **Image processing**: 30-60 seconds per image
- **PDF processing**: 2-5 minutes for 10 pages
- **Embedding generation**: 5-10 seconds for batch of 32 texts
- **Query response**: 10-20 seconds

If you're seeing the fast times, **your GPU is working!**

## Troubleshooting

### GPU Not Being Used

If `nvidia-smi` shows 0% GPU usage during processing:

1. **Check Ollama is running**:
   ```powershell
   ollama list
   ```

2. **Verify models are loaded**:
   ```powershell
   ollama ps
   ```

3. **Check Ollama GPU detection**:
   ```powershell
   ollama show qwen2.5vl:7b
   ```

4. **Restart Ollama**:
   ```powershell
   # Stop Ollama (Ctrl+C in the terminal)
   # Then restart:
   ollama serve
   ```

### Still Showing CPU Usage

If Ollama is using CPU instead of GPU:

1. **Check NVIDIA drivers**:
   ```powershell
   nvidia-smi
   ```
   Should show driver version and CUDA version.

2. **Reinstall Ollama** (it should auto-detect GPU):
   - Download from: https://ollama.ai/download
   - Install and restart

3. **Check CUDA installation**:
   ```powershell
   nvcc --version
   ```
   Should show CUDA compiler version.

## Expected Startup Logs

When you start the backend, you should see:

```
INFO:     Starting RAG chatbot API server
INFO:     Starting in DESKTOP mode (document processing enabled)
INFO:     Initializing embedding engine with model: mxbai-embed-large
INFO:     ✓ Using Ollama for embeddings: mxbai-embed-large
INFO:     ✓ Ollama handles GPU acceleration automatically
INFO:     Embedding engine initialized successfully
INFO:     Embedding dimension: 1024
INFO:     API server initialized successfully in DESKTOP mode
```

**Key indicators:**
- ✅ "Using Ollama for embeddings" (not "falling back to sentence-transformers")
- ✅ "Ollama handles GPU acceleration automatically"
- ✅ No errors about model loading

## Summary

- **Ignore** the "No GPU acceleration" message - it's just PyTorch checking
- **Ollama automatically uses your RTX 4080** - no configuration needed
- **Verify with `nvidia-smi -l 1`** while processing documents
- **Fast processing times** = GPU is working correctly

Your GPU is being used if:
1. ✅ `nvidia-smi` shows memory usage increase during processing
2. ✅ `ollama ps` shows "100% GPU" for loaded models
3. ✅ Processing times are fast (seconds, not minutes)
4. ✅ Backend logs show "Using Ollama for embeddings"

**You're all set! Your RTX 4080 is being used by Ollama for all model inference.**
