# Desktop-Pi Split Architecture

## Overview

The Desktop-Pi RAG Pipeline uses a **split-architecture** design that separates computationally expensive document processing from lightweight query serving. This enables you to process documents once on powerful hardware and serve queries efficiently on resource-constrained devices.

### Architecture Philosophy

**Process Once, Serve Anywhere**

- **Desktop**: Heavy computation (document processing, embedding generation with large models)
- **Raspberry Pi**: Lightweight operations (query serving, response generation with small models)
- **Data Flow**: Desktop processes → exports → Pi imports → serves queries

### Key Benefits

- ✅ **One-time expensive processing** on powerful hardware with GPU acceleration
- ✅ **Efficient serving** on resource-constrained hardware (Raspberry Pi)
- ✅ **No GPU required** on the Pi
- ✅ **Incremental updates** without full redeployment
- ✅ **Local deployment** with no cloud dependencies
- ✅ **Cost-effective** - process on desktop, serve 24/7 on low-power Pi
- ✅ **Scalable** - add more Pi servers for load balancing

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        DESKTOP PROCESSOR                         │
│                         (RTX 4080 GPU)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Document Processor  →  Embedding Engine  →  Vector Store      │
│  (PDF, Images, Text)    (sentence-transformers)  (ChromaDB)    │
│                              ↓                                   │
│                    Vision Model (Qwen2.5vl:7b)                  │
│                              ↓                                   │
│                      Export Manager                              │
│                              ↓                                   │
│              Creates Export Package (tar.gz)                     │
│                                                                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               │ Transfer via SCP/rsync
                               │
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                          PI SERVER                               │
│                      (Raspberry Pi 4/5)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Data Loader  →  Vector Store (Read-Only)  →  Query Engine     │
│                                                  ↓               │
│                                    Conversational Model          │
│                                    (Qwen2.5:3b)                 │
│                                                  ↓               │
│                                    FastAPI Server                │
│                                                  ↓               │
│                                    Web Interface                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

#### Desktop Processor

| Component | Responsibility |
|-----------|---------------|
| **Document Processor** | Extract text from PDFs, process images with vision model, chunk documents |
| **Embedding Engine** | Generate high-quality embeddings using sentence-transformers (384-dim) with GPU acceleration |
| **Vector Store** | Store document chunks and embeddings in ChromaDB |
| **Export Manager** | Create deployment packages with all processed data, manifest, and configuration |
| **Processing Validator** | Validate data quality before export (check embeddings, metadata) |

#### Pi Server

| Component | Responsibility |
|-----------|---------------|
| **Data Loader** | Load pre-computed vector store and database in read-only mode |
| **Query Engine** | Process user queries, retrieve relevant chunks, construct prompts |
| **Conversational Model** | Generate natural language responses using lightweight model (Qwen2.5:3b) |
| **Resource Monitor** | Track memory usage, log query metrics, expose health check endpoint |
| **Web Interface** | Serve ChatGPT-style interface for user interaction |

---

## Data Flow

### Desktop Processing Flow

```
1. Add Documents
   ↓
2. Document Processor extracts text/processes images
   ↓
3. Text Chunker splits content into chunks
   ↓
4. Embedding Engine generates embeddings (GPU-accelerated)
   ↓
5. Vector Store saves chunks + embeddings
   ↓
6. Processing Validator checks data quality
   ↓
7. Export Manager creates deployment package
   ↓
8. Transfer package to Pi (SCP/rsync)
```

### Pi Serving Flow

```
1. User submits query via web interface
   ↓
2. Query Engine generates query embedding (CPU)
   ↓
3. Vector Store performs similarity search
   ↓
4. Query Engine retrieves top-K relevant chunks
   ↓
5. Query Engine constructs prompt with context
   ↓
6. Conversational Model generates response
   ↓
7. Response returned to user
   ↓
8. Resource Monitor logs metrics
```

### Incremental Update Flow

```
1. Add new documents on desktop
   ↓
2. Process only new/modified documents
   ↓
3. Create incremental export package
   ↓
4. Transfer incremental package to Pi
   ↓
5. Pi merges new data with existing store
   ↓
6. Pi restarts and serves updated data
```

---

## Model Requirements

### Desktop Models

| Model | Purpose | Size | Hardware |
|-------|---------|------|----------|
| **sentence-transformers** | Document embeddings | ~400MB | GPU (CUDA) |
| `paraphrase-multilingual-MiniLM-L12-v2` | 384-dimensional embeddings | | |
| **Qwen2.5vl:7b** | Vision processing (images) | ~4.7GB | GPU (CUDA) |

**Desktop Hardware Requirements:**
- NVIDIA GPU with CUDA support (RTX 4080 or similar)
- 16GB+ RAM
- 50GB+ free disk space

### Pi Models

| Model | Purpose | Size | Hardware |
|-------|---------|------|----------|
| **Qwen2.5:3b** | Conversational responses | ~1.9GB | CPU-only |
| (Alternative) **Qwen2.5:1.5b** | For 4GB Pi | ~900MB | CPU-only |

**Pi Hardware Requirements:**
- **Recommended**: Raspberry Pi 4 (8GB) or Pi 5 (8GB)
- **Minimum**: Raspberry Pi 4 (4GB)
- 32GB+ microSD or SSD (SSD strongly recommended)
- Stable power supply

### Model Compatibility

The system ensures compatibility through a **manifest file** that records:
- Embedding model name and version
- Embedding dimensionality (must match between desktop and Pi)
- Vision model used for processing
- Required conversational model for Pi

The Pi validates the manifest on startup and rejects incompatible data.

---

## Performance Expectations

### Desktop Performance

| Operation | Performance | Notes |
|-----------|-------------|-------|
| **Document Processing** | 10+ docs/min | With GPU acceleration |
| **Embedding Generation** | 100+ chunks/sec | Batch processing with GPU |
| **Image Processing** | 5-10 sec/image | Using Qwen2.5vl:7b |
| **Export Creation** | 30-60 sec | For ~1000 chunks |

### Pi Performance

#### Raspberry Pi 4 (8GB) with Qwen2.5:3b

| Operation | Performance | Notes |
|-----------|-------------|-------|
| **Query Retrieval** | 1-2 seconds | Vector similarity search |
| **Response Generation** | 5-8 seconds | CPU-only inference |
| **Total Query Time** | 6-10 seconds | End-to-end |
| **Concurrent Users** | 3-5 users | Simultaneous queries |
| **Memory Usage** | 3-4GB | Steady state |

#### Raspberry Pi 5 (8GB) with Qwen2.5:3b

| Operation | Performance | Notes |
|-----------|-------------|-------|
| **Query Retrieval** | 0.5-1 seconds | Faster CPU |
| **Response Generation** | 3-5 seconds | Improved performance |
| **Total Query Time** | 3-6 seconds | End-to-end |
| **Concurrent Users** | 5-10 users | Better concurrency |
| **Memory Usage** | 3-4GB | Steady state |

#### Raspberry Pi 4 (4GB) with Qwen2.5:1.5b

| Operation | Performance | Notes |
|-----------|-------------|-------|
| **Query Retrieval** | 1-2 seconds | Same as 8GB |
| **Response Generation** | 4-6 seconds | Smaller model |
| **Total Query Time** | 5-8 seconds | End-to-end |
| **Concurrent Users** | 2-3 users | Limited by memory |
| **Memory Usage** | 2-3GB | Tighter constraints |

### Performance Optimization Tips

**Desktop:**
- Use GPU acceleration for embeddings
- Batch process documents (32 chunks at a time)
- Process incrementally (skip unchanged files)

**Pi:**
- Use SSD instead of microSD (3-5x faster I/O)
- Use wired Ethernet (more stable than WiFi)
- Reduce TOP_K_RESULTS for faster retrieval
- Use smaller model (1.5b) on 4GB Pi
- Enable swap space for stability

---

## Deployment Workflow

### Initial Deployment

```bash
# 1. On Desktop: Process documents
python -m uvicorn backend.api:app --reload
# Add documents to watched folders
# Wait for processing to complete

# 2. On Desktop: Create export package
python utils/export_for_pi.py --output pi_export

# 3. Transfer to Pi
scp pi_export/pi_export.tar.gz pi@pi-hostname:~/docubot/

# 4. On Pi: Extract and setup
tar -xzf pi_export.tar.gz
mv pi_export/chromadb data/
mv pi_export/app.db data/
cp pi_export/config_pi_template.py config.py

# 5. On Pi: Start server
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
```

### Incremental Updates

```bash
# 1. On Desktop: Process new documents
# Add new documents to watched folders
# Wait for processing

# 2. On Desktop: Create incremental export
python utils/export_for_pi.py --incremental --since "2024-01-15T10:30:00"

# 3. Transfer to Pi
scp pi_export_incremental/pi_export_incremental.tar.gz pi@pi-hostname:~/docubot/

# 4. On Pi: Merge and restart
# Stop server
tar -xzf pi_export_incremental.tar.gz
curl -X POST http://localhost:8000/api/data/merge \
  -H "Content-Type: application/json" \
  -d '{"package_path": "pi_export_incremental"}'
# Restart server
```

For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Configuration

### Desktop Configuration

```python
# config.py (Desktop)
ENABLE_DOCUMENT_PROCESSING = True  # Enable processing on desktop

# Embedding model (large, high-quality)
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Vision model for image processing
OLLAMA_MODEL = "qwen2.5vl:7b"

# Processing settings
BATCH_SIZE = 32  # GPU batch size
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
```

### Pi Configuration

```python
# config.py (Pi)
ENABLE_DOCUMENT_PROCESSING = False  # Disable processing on Pi

# Conversational model (small, efficient)
CONVERSATIONAL_MODEL = "qwen2.5:3b"  # or "qwen2.5:1.5b" for 4GB Pi

# Query settings
TOP_K_RESULTS = 5  # Number of chunks to retrieve
QUERY_TIMEOUT = 2  # Retrieval timeout (seconds)
RESPONSE_TIMEOUT = 10  # Generation timeout (seconds)

# Resource limits
MAX_MEMORY_PERCENT = 90  # Warning threshold
```

---

## Export Package Structure

When you create an export package, it contains:

```
pi_export/
├── chromadb/                    # Vector store directory
│   ├── chroma.sqlite3          # ChromaDB metadata
│   └── [collection_data]/      # Embedding data
├── app.db                       # SQLite database (processing state)
├── manifest.json                # Model compatibility manifest
├── config_pi_template.py        # Pi configuration template
├── DEPLOYMENT.md                # Deployment instructions
└── pi_export.tar.gz            # Compressed archive (for transfer)
```

### Manifest File

The manifest ensures compatibility between desktop and Pi:

```json
{
  "version": "1.0",
  "created_at": "2024-01-15T10:30:00Z",
  "export_type": "full",
  "desktop_config": {
    "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
    "embedding_dimension": 384,
    "vision_model": "qwen2.5vl:7b"
  },
  "pi_requirements": {
    "conversational_model": "qwen2.5:3b",
    "min_memory_gb": 4,
    "embedding_dimension": 384
  },
  "statistics": {
    "total_documents": 150,
    "total_chunks": 1250,
    "total_embeddings": 1250,
    "vector_store_size_mb": 45.2,
    "database_size_mb": 2.1
  }
}
```

---

## Advantages of Split Architecture

### Cost Efficiency

- **Desktop**: Process documents occasionally (when new docs added)
- **Pi**: Serve queries 24/7 with minimal power consumption (~5W vs 300W+)
- **Savings**: ~$20-30/month in electricity costs

### Scalability

- **Horizontal**: Deploy multiple Pi servers for load balancing
- **Vertical**: Upgrade desktop GPU for faster processing without changing Pi
- **Incremental**: Update Pi with new data without full reprocessing

### Flexibility

- **Model Selection**: Use best models for each task (large for embeddings, small for responses)
- **Hardware Optimization**: GPU for processing, CPU for serving
- **Deployment Options**: Desktop at home, Pi anywhere (office, remote location)

### Reliability

- **Read-Only Pi**: No data corruption from serving operations
- **Stateless Serving**: Pi can restart without losing data
- **Backup-Friendly**: Export packages serve as backups
- **Disaster Recovery**: Redeploy to new Pi from export package

---

## Limitations and Considerations

### Current Limitations

1. **No Real-Time Updates**: Pi serves pre-computed data; new documents require export/transfer/merge
2. **Embedding Model Fixed**: Cannot change embedding model without reprocessing all documents
3. **Manual Transfer**: Requires manual SCP/rsync for data transfer (no automatic sync)
4. **Single-Language Responses**: Response language matches query language (no translation)

### When to Use This Architecture

✅ **Good Fit:**
- Document corpus changes infrequently (daily/weekly updates)
- Need 24/7 query serving with low power consumption
- Have powerful desktop for processing
- Want local deployment (no cloud)
- Need to serve multiple locations with same data

❌ **Not Ideal:**
- Need real-time document updates (use single-server architecture)
- Document corpus changes constantly (every few minutes)
- Don't have access to GPU for processing
- Need cloud deployment with auto-scaling

### Future Enhancements

Potential improvements to the split architecture:

1. **Automatic Sync**: Scheduled export and transfer
2. **Multi-Pi Deployment**: Load balancing across multiple Pi servers
3. **Compression**: Smaller export packages with embedding compression
4. **Delta Encoding**: More efficient incremental updates
5. **Remote Management**: Web interface for managing exports and transfers
6. **A/B Testing**: Compare different model configurations
7. **Query Analytics**: Track popular queries and response quality

---

## Comparison with Single-Server Architecture

| Aspect | Split Architecture | Single-Server |
|--------|-------------------|---------------|
| **Processing** | Desktop (GPU) | Same server |
| **Serving** | Pi (CPU) | Same server |
| **Power Consumption** | ~5W (Pi) | ~300W+ (Desktop) |
| **Scalability** | Multiple Pi servers | Vertical only |
| **Updates** | Export/transfer/merge | Real-time |
| **Complexity** | Higher (2 systems) | Lower (1 system) |
| **Cost** | Lower (24/7 Pi) | Higher (24/7 Desktop) |
| **Best For** | Infrequent updates, 24/7 serving | Frequent updates, single location |

---

## Getting Started

### Quick Start

1. **Read the full deployment guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
2. **Set up your desktop** with GPU and required models
3. **Set up your Pi** with Ollama and conversational model
4. **Process documents** on desktop
5. **Create export package** and transfer to Pi
6. **Start serving** queries on Pi

### Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)**: Complete deployment instructions
- **[README.md](README.md)**: Main project documentation
- **[QUICK_START.md](QUICK_START.md)**: Quick start guide for single-server setup

### Support

For issues or questions:
1. Check [DEPLOYMENT.md](DEPLOYMENT.md) troubleshooting section
2. Review system logs: `tail -f logs/app.log`
3. Check health endpoint: `curl http://localhost:8000/api/health`
4. Open an issue on GitHub with error details

---

## Summary

The Desktop-Pi split architecture enables:

- **Efficient Processing**: Use powerful desktop GPU for one-time document processing
- **Efficient Serving**: Use low-power Pi for 24/7 query serving
- **Cost Savings**: Reduce electricity costs by ~$20-30/month
- **Scalability**: Deploy multiple Pi servers for load balancing
- **Flexibility**: Choose optimal models for each task
- **Reliability**: Read-only Pi operation prevents data corruption

This architecture is ideal for scenarios where document updates are infrequent but query serving needs to be continuous, cost-effective, and scalable.

---

**Last Updated:** 2024-01-20  
**Version:** 1.0
