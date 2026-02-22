# Performance Issues Analysis

## 📊 Observed Performance

### Processing Times (From Logs)
- **First PDF (2 pages)**: 31 seconds for vision processing
- **Second PDF page 1**: 35 seconds → **TIMEOUT**
- **Second PDF page 2**: 10 seconds (successful)
- **Images**: 17-20 seconds each
- **Total**: ~5 minutes for 7 files

### Expected Performance (RTX 4080)
- **PDF page**: 2-3 seconds
- **Image**: 2-3 seconds
- **Total**: 30-45 seconds for 7 files

## 🔴 Critical Issues Found

### Issue 1: Ollama Timeout Too Short
**Problem**: 30-second timeout is too aggressive
**Evidence**: 
```
20:01:04 - Vision model failed on page 1: Request timed out after 30 seconds
20:03:11 - Vision model failed: Request timed out after 30 seconds
```

**Impact**: 1 file completely failed, 1 PDF page failed

### Issue 2: Extremely Slow Vision Processing
**Problem**: 17-35 seconds per image is 10x slower than expected
**Evidence**: Each image takes 17-20 seconds, should be 2-3 seconds

**Possible Causes**:
1. Ollama not using GPU (using CPU instead)
2. Model not loaded in VRAM (loading from disk each time)
3. Image preprocessing taking too long
4. Network/API overhead

### Issue 3: Inconsistent Performance
**Problem**: Some images process in 10 seconds, others take 35 seconds
**Evidence**: 
- Page 2 of second PDF: 10 seconds ✓
- Page 1 of second PDF: 35 seconds ✗
- Images: 17-20 seconds

## 🔍 Root Cause Analysis

### Most Likely: Ollama Not Using GPU

**Indicators**:
1. **Speed**: 17-35 seconds is CPU-level performance
2. **GPU speed should be**: 2-3 seconds per image
3. **10x slower** = likely CPU inference

**How to Verify**:
Run `nvidia-smi -l 1` during processing and check:
- GPU utilization should be 80-95%
- VRAM usage should be 6-8GB
- If both are low → Ollama is using CPU

### Secondary: Timeout Too Short

Even if GPU is working, 30 seconds is too short for:
- Complex images
- First-time model loading
- Large images (need resizing)

## 🛠️ Fixes Required

### Fix 1: Increase Ollama Timeout
**Change**: 30 seconds → 120 seconds for vision model
**File**: `backend/ollama_client.py`
**Reason**: Vision models need more time, especially for complex images

### Fix 2: Verify Ollama GPU Usage
**Check**: Run `ollama ps` to see if models show "100% GPU"
**If CPU**: Restart Ollama or reinstall to force GPU detection

### Fix 3: Add Model Preloading
**Change**: Load vision model once at startup
**Benefit**: Eliminates first-request slowness

### Fix 4: Optimize Image Preprocessing
**Check**: Image resizing might be slow
**Optimize**: Use faster PIL operations

## 📈 Expected Improvements

### After Fixes:
- **PDF page**: 2-3 seconds (10x faster)
- **Image**: 2-3 seconds (8x faster)
- **Total**: 30-45 seconds for 7 files (6x faster)
- **No timeouts**: 120-second timeout handles all cases

## 🎯 Action Plan

1. **Immediate**: Increase timeout to 120 seconds
2. **Verify**: Check if Ollama is using GPU with `nvidia-smi`
3. **Test**: Reprocess files and compare times
4. **Optimize**: If still slow, add model preloading

## 🔧 Quick Verification Commands

```powershell
# Check if Ollama is using GPU
ollama ps

# Watch GPU usage in real-time
nvidia-smi -l 1

# Check Ollama logs
ollama logs
```

**Expected Output (GPU working)**:
```
NAME                ID          SIZE    PROCESSOR    UNTIL
qwen2.5vl:7b       abc123      6.0 GB  100% GPU     4 minutes from now
```

**Bad Output (CPU only)**:
```
NAME                ID          SIZE    PROCESSOR    UNTIL
qwen2.5vl:7b       abc123      6.0 GB  100% CPU     4 minutes from now
```
