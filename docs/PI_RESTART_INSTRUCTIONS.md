# Raspberry Pi Restart Instructions

## Current Status

✅ **Data synced to Pi**:
- ChromaDB vector store with corrected metadata
- SQLite database (app.db)

✅ **Code synced to Pi**:
- Updated `backend/llm_generator.py` with metadata-aware prompts
- Updated `backend/ollama_client.py` with custom options support
- Updated `backend/image_processor.py` with higher num_predict for vision

✅ **Metadata fix verified locally**:
- Test query: "2월에 코스트코에 총 얼마나 썼어?"
- Expected result: $411.89 (Costco total)
- Local test: ✓ PASSED

## Next Steps

### 1. SSH to Raspberry Pi

```bash
wsl -d Ubuntu -- ssh hws@192.168.1.139
```

### 2. Stop Current Backend

```bash
cd ~/docubot
pkill -f 'python.*main.py'
```

### 3. Verify Data Sync

```bash
# Check ChromaDB
ls -lh ~/docubot/data/chromadb/

# Check database
ls -lh ~/docubot/data/app.db
```

### 4. Start Backend

```bash
cd ~/docubot
./scripts/start_pi.sh
```

### 5. Monitor Logs

```bash
# In a separate SSH session
tail -f ~/docubot/backend.log
```

### 6. Test Query

Open browser: `http://192.168.1.139:3000`

Login as "Mom" and test:
```
2월에 코스트코에 총 얼마나 썼어?
```

**Expected response**: Should mention Costco receipts and total around $411.89

**Previous incorrect response**: Returned $41.94 from H-MART

## What Was Fixed

1. **Vision model JSON truncation**: Increased `num_predict` from 256 to 2048 for vision extraction
2. **Missing metadata**: Costco receipts now have complete metadata including `store` and `total` fields
3. **Duplicate chunks**: Removed old chunks without metadata from vector store
4. **LLM prompt**: Enhanced to explicitly use metadata fields for store filtering and total calculation

## Verification Checklist

- [ ] Backend starts without errors
- [ ] Frontend accessible at http://192.168.1.139:3000
- [ ] Can login as "Mom"
- [ ] Query "2월에 코스트코에 총 얼마나 썼어?" returns Costco total (~$411.89)
- [ ] Query does NOT return H-MART total ($41.94)
- [ ] Response mentions specific Costco receipts (IMG_4025.jpeg, KakaoTalk_20260219_155140673.jpg)

## Troubleshooting

### If backend fails to start:
```bash
# Check Python environment
source ~/docubot/venv/bin/activate
python --version

# Check dependencies
pip list | grep -E "chromadb|fastapi|ollama"

# Check Ollama
curl http://localhost:11434/api/tags
```

### If query returns wrong results:
```bash
# Check ChromaDB data
python3 << EOF
from backend.vector_store import get_vector_store
vs = get_vector_store()
print(f"Total chunks: {vs.collection.count()}")
results = vs.collection.get(where={'filename': {'$eq': 'IMG_4025.jpeg'}}, include=['metadatas'])
if results and results['metadatas']:
    print(f"IMG_4025 metadata: {results['metadatas'][0]}")
EOF
```

### If LLM is slow:
- Expected: ~50-55 seconds total (embedding: 3s, retrieval: 3s, LLM: 45s)
- If slower, check CPU usage: `htop`
- Check Ollama config: `systemctl status ollama`

## Performance Expectations

- **Embedding generation**: ~3 seconds
- **Vector retrieval**: ~3 seconds  
- **LLM response**: ~45 seconds
- **Total query time**: ~50-55 seconds

This is normal for qwen2.5:1.5b on Raspberry Pi 5.

## Files Modified

Desktop (already synced to Pi):
- `backend/ollama_client.py`
- `backend/image_processor.py`
- `backend/llm_generator.py`

Data (already synced to Pi):
- `data/chromadb/` (updated with corrected metadata)
- `data/app.db` (SQLite database)

## Sync Scripts for Future Updates

Located in `scripts/`:
- `sync_to_pi.py` - Sync data (ChromaDB + database)
- `sync_code_to_pi.py` - Sync backend code

Usage:
```bash
# On desktop
python scripts/sync_to_pi.py
python scripts/sync_code_to_pi.py
```
