# Model Recommendations for Desktop-Pi RAG Pipeline

Based on extensive research and benchmarking, here are the recommended models for optimal performance in your Desktop-Pi RAG system.

---

## Desktop Configuration (RTX 4080)

### For Text Embeddings

**Recommended: `mxbai-embed-large` (334M parameters)**

```bash
ollama pull mxbai-embed-large
```

**Why this model:**
- State-of-the-art performance for BERT-large sized models on MTEB benchmark
- Outperforms OpenAI's text-embedding-3-large
- Matches performance of models 20x its size
- 1024-dimensional embeddings (high quality)
- Optimized for retrieval tasks
- Works great with GPU acceleration

**Alternative: `nomic-embed-text` (137M parameters)**
```bash
ollama pull nomic-embed-text
```
- Excellent for long context (8192 tokens)
- Strong multilingual support
- 768-dimensional embeddings
- Faster than mxbai but slightly lower accuracy

### For Vision/Image Processing

**Recommended: `qwen2.5vl:7b` or `qwen2.5vl:32b`**

```bash
# For RTX 4080 (16GB VRAM) - use 7b
ollama pull qwen2.5vl:7b

# If you have more VRAM or want best quality - use 32b
ollama pull qwen2.5vl:32b
```

**Why Qwen 2.5 VL:**
- **Best-in-class vision-language model** for 2025
- Dynamic resolution handling (no image normalization needed)
- Excellent OCR capabilities (29 languages)
- Strong document understanding
- Object localization and structured data extraction
- Can process complex diagrams, charts, and scanned documents
- Apache 2.0 license (fully open source)

**Performance on RTX 4080:**
- 7b model: ~4-6 seconds per image
- 32b model: ~10-15 seconds per image (better quality)

**Alternative: `llava:13b` or `llava:34b`**
```bash
ollama pull llava:13b
```
- Good general-purpose vision model
- Faster than Qwen but less accurate for documents
- Better for simple image captioning

### For Text Generation (Optional - Desktop Testing)

**Recommended: `qwen2.5:14b`**

```bash
ollama pull qwen2.5:14b
```

**Why:**
- Excellent reasoning capabilities
- Strong multilingual support (including Korean)
- Good for testing responses before Pi deployment
- Can be used for query expansion or document summarization

---

## Raspberry Pi Configuration

### For Conversational Responses

**Recommended: `qwen2.5:3b`**

```bash
ollama pull qwen2.5:3b
```

**Why this model:**
- Optimized for Raspberry Pi 4 (4GB+ RAM)
- Excellent quality-to-size ratio
- Strong multilingual support
- Fast inference on CPU (~2-5 seconds per response)
- Memory footprint: ~2-3GB
- Supports Korean and other languages well

**Alternative if memory is tight: `qwen2.5:1.5b`**
```bash
ollama pull qwen2.5:1.5b
```
- Even lighter (1-2GB RAM)
- Faster responses (~1-3 seconds)
- Slightly lower quality but still very capable

**Alternative for English-only: `phi3:3.8b`**
```bash
ollama pull phi3:3.8b
```
- Microsoft's efficient model
- Strong reasoning in compact size
- Good for English-focused applications

### For Embeddings (Query Processing)

**Use the same model as desktop for compatibility:**

```bash
ollama pull mxbai-embed-large
```

**CRITICAL:** The embedding model MUST match between desktop and Pi to ensure embedding dimensions are compatible.

---

## Complete Setup Commands

### Desktop Setup

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull embedding model (for document processing)
ollama pull mxbai-embed-large

# Pull vision model (for image processing)
ollama pull qwen2.5vl:7b

# Optional: Pull text generation model for testing
ollama pull qwen2.5:14b
```

### Raspberry Pi Setup

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull conversational model (lightweight)
ollama pull qwen2.5:3b

# Pull embedding model (MUST match desktop)
ollama pull mxbai-embed-large
```

---

## Configuration Files

### Desktop `backend/config.py`

```python
import os
from pathlib import Path

class Config:
    """Desktop configuration for document processing."""
    
    # Deployment mode
    ENABLE_DOCUMENT_PROCESSING = True  # Enable processing on desktop
    
    # Ollama configuration
    OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
    OLLAMA_MODEL = "qwen2.5:14b"  # For text generation/testing
    OLLAMA_VISION_MODEL = "qwen2.5vl:7b"  # For image processing
    
    # Embedding configuration
    EMBEDDING_MODEL = "mxbai-embed-large"  # For document embeddings
    EMBEDDING_DIMENSION = 1024  # mxbai-embed-large dimension
    
    # Alternative: nomic-embed-text
    # EMBEDDING_MODEL = "nomic-embed-text"
    # EMBEDDING_DIMENSION = 768
    
    # Conversational model (for export manifest)
    CONVERSATIONAL_MODEL = "qwen2.5:3b"
    
    # Paths
    CHROMADB_PATH = os.getenv("CHROMADB_PATH", str(Path("data/chromadb").absolute()))
    SQLITE_PATH = os.getenv("SQLITE_PATH", str(Path("data/rag_chatbot.db").absolute()))
    
    # Processing settings
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    BATCH_SIZE = 32  # GPU can handle larger batches
```

### Raspberry Pi `backend/config.py`

```python
import os
from pathlib import Path

class Config:
    """Raspberry Pi configuration for query serving."""
    
    # Deployment mode
    ENABLE_DOCUMENT_PROCESSING = False  # CRITICAL: Disable on Pi
    
    # Ollama configuration
    OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
    OLLAMA_MODEL = "qwen2.5:3b"  # Lightweight conversational model
    
    # Embedding configuration (MUST match desktop)
    EMBEDDING_MODEL = "mxbai-embed-large"
    EMBEDDING_DIMENSION = 1024  # Must match desktop
    
    # Conversational model
    CONVERSATIONAL_MODEL = "qwen2.5:3b"
    
    # Paths
    CHROMADB_PATH = os.getenv("CHROMADB_PATH", str(Path("data/chromadb").absolute()))
    SQLITE_PATH = os.getenv("SQLITE_PATH", str(Path("data/app.db").absolute()))
    MANIFEST_PATH = os.getenv("MANIFEST_PATH", "data/manifest.json")
    
    # Query settings
    TOP_K = 5  # Number of chunks to retrieve
    SIMILARITY_THRESHOLD = 0.3  # Minimum similarity score
```

---

## Model Comparison

### Embedding Models

| Model | Size | Dimensions | Speed | Accuracy | Use Case |
|-------|------|------------|-------|----------|----------|
| mxbai-embed-large | 334M | 1024 | Medium | Excellent | Best overall for RAG |
| nomic-embed-text | 137M | 768 | Fast | Very Good | Long context, multilingual |
| all-minilm-l6-v2 | 22M | 384 | Very Fast | Good | High-throughput, simple search |
| bge-base-en-v1.5 | 110M | 768 | Fast | Very Good | English-focused RAG |

### Vision Models

| Model | Size | Speed (RTX 4080) | OCR Quality | Document Understanding | License |
|-------|------|------------------|-------------|------------------------|---------|
| qwen2.5vl:7b | 7B | 4-6s | Excellent | Excellent | Apache 2.0 |
| qwen2.5vl:32b | 32B | 10-15s | Best | Best | Apache 2.0 |
| llava:13b | 13B | 3-5s | Good | Good | Apache 2.0 |
| llava:34b | 34B | 8-12s | Very Good | Very Good | Apache 2.0 |

### Conversational Models (Pi)

| Model | Size | RAM Usage | Speed (Pi 4) | Quality | Languages |
|-------|------|-----------|--------------|---------|-----------|
| qwen2.5:3b | 3B | 2-3GB | 2-5s | Excellent | 29+ |
| qwen2.5:1.5b | 1.5B | 1-2GB | 1-3s | Very Good | 29+ |
| phi3:3.8b | 3.8B | 2-3GB | 2-4s | Very Good | English |
| gemma2:2b | 2B | 1.5-2GB | 1-3s | Good | English |

---

## Performance Expectations

### Desktop Processing (RTX 4080)

**Text Documents:**
- Embedding generation: ~500-1000 chunks/minute
- GPU utilization: 80-100%
- Memory: 4-6GB VRAM, 8-12GB RAM

**Images:**
- Processing with qwen2.5vl:7b: ~10-15 images/minute
- Processing with qwen2.5vl:32b: ~4-6 images/minute
- GPU utilization: 90-100%

### Raspberry Pi Query Serving

**Query Processing:**
- Embedding generation: <500ms
- Vector search: <1s
- Response generation: 2-5s (qwen2.5:3b)
- Total query time: 3-7s

**Concurrent Users:**
- 5-10 simultaneous queries (with qwen2.5:3b)
- 10-15 simultaneous queries (with qwen2.5:1.5b)

---

## Troubleshooting

### Desktop Issues

**GPU not being used:**
```bash
# Check GPU availability
nvidia-smi

# Verify Ollama is using GPU
ollama ps
```

**Out of VRAM:**
- Use qwen2.5vl:7b instead of 32b
- Reduce batch size in config
- Process images one at a time

### Pi Issues

**Out of memory:**
```bash
# Check memory usage
free -h

# Switch to lighter model
ollama pull qwen2.5:1.5b
```

**Slow responses:**
- Reduce TOP_K from 5 to 3
- Use qwen2.5:1.5b instead of 3b
- Consider using SSD instead of microSD

**Model compatibility errors:**
- Ensure embedding models match exactly
- Check manifest.json for dimension mismatch
- Re-export from desktop if needed

---

## Upgrading Models

### To upgrade embedding model:

1. **On Desktop:**
   ```bash
   # Pull new model
   ollama pull <new-model>
   
   # Update config.py
   # EMBEDDING_MODEL = "<new-model>"
   
   # Re-process all documents
   curl -X POST http://localhost:8000/api/process
   
   # Create new export
   ./scripts/desktop_export.sh
   ```

2. **On Pi:**
   ```bash
   # Pull same model
   ollama pull <new-model>
   
   # Extract new export package
   # Run setup script
   ```

### To upgrade vision model:

1. **On Desktop only:**
   ```bash
   # Pull new model
   ollama pull qwen2.5vl:32b
   
   # Update config.py
   # OLLAMA_VISION_MODEL = "qwen2.5vl:32b"
   
   # Re-process images only
   ```

---

## Summary

**Best Configuration for Most Users:**

**Desktop:**
- Embeddings: `mxbai-embed-large` (1024-dim)
- Vision: `qwen2.5vl:7b`
- Testing: `qwen2.5:14b` (optional)

**Raspberry Pi:**
- Conversational: `qwen2.5:3b`
- Embeddings: `mxbai-embed-large` (must match desktop)

This configuration provides the best balance of quality, speed, and resource usage for a Desktop-Pi RAG pipeline.

---

## References

- [Ollama Embedding Models](https://ollama.com/blog/embedding-models)
- [Best Open-Source Embedding Models Benchmarked](https://supermemory.ai/blog/best-open-source-embedding-models-benchmarked-and-ranked/)
- [Best Vision Language Models 2025](https://www.labellerr.com/blog/top-open-source-vision-language-models/)
- [Qwen 2.5 VL Documentation](https://ollama.com/library/qwen2.5-vl)
- [mxbai-embed-large on Ollama](https://ollama.com/library/mxbai-embed-large)
