# Metadata Extraction Fix - Summary

## Problem Identified

The query "2월에 코스트코에 총 얼마나 썼어?" (How much spent at Costco in February?) was returning incorrect results:
- **Returned**: 41.94 (from H-MART receipt)
- **Expected**: Sum of Costco receipts (189.71 + 36.44 + 222.18 = 448.33)

### Root Cause

1. **Vision model JSON truncation**: The `num_predict: 256` setting was too low for vision extraction, causing JSON responses to be truncated before metadata fields like `store` and `total` were included.

2. **Missing metadata in vector store**: Costco receipts (IMG_4025.jpeg, IMG_4026.jpeg, KakaoTalk_20260219_155140673.jpg) had NO extracted metadata in ChromaDB, while H-MART receipt had complete metadata including `store: "H-MART"` and `total_due: "41.94"`.

3. **Duplicate chunks**: Each file had 3 chunks in the vector store - 2 old chunks without metadata and 1 new chunk with metadata. The query engine was retrieving old chunks without metadata.

## Solution Implemented

### 1. Fixed Vision Model Parameters (backend/ollama_client.py & backend/image_processor.py)

Modified `backend/ollama_client.py` to accept custom `options` parameter override:
```python
def generate_with_image(self, prompt: str, image_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    # Allow custom options override for specific use cases
    request_options = self.options.copy()
    if options:
        request_options.update(options)
```

Modified `backend/image_processor.py` to use higher limits for vision extraction:
```python
extraction_result = self.vision_client.generate_with_image(
    prompt=prompt,
    image_path=image_path,
    options={
        "num_predict": 2048,  # Allow longer JSON responses
        "num_ctx": 4096       # Larger context for complex receipts
    }
)
```

### 2. Cleaned Up Vector Store

Deleted 6 old chunks without metadata:
- IMG_4025.jpeg: Removed 2 old chunks, kept 1 with 36 metadata fields including `total: "189.71"`
- IMG_4026.jpeg: Removed 2 old chunks, kept 1 with 30 metadata fields including `total: "36.44"`
- KakaoTalk_20260219_155140673.jpg: Removed 2 old chunks, kept 1 with 30 metadata fields including `total: "222.18"`

Script: `delete_old_costco_chunks.py`

### 3. Enhanced LLM Prompt (backend/llm_generator.py)

Updated prompt to explicitly use metadata fields:

**Korean prompt**:
```
규칙:
- 각 문서의 메타데이터에서 "store" 필드와 "total" 필드를 확인하세요
- 질문에서 특정 가게를 물어보면 "store" 필드가 일치하는 문서만 계산 (예: "코스트코" → store: "Costco Wholesale")
- "총"/"전체" 요청시 해당 가게의 모든 "total" 값을 합산
```

**English prompt**:
```
Rules:
- Look for "store" and "total" fields in each document's metadata
- If question asks about specific store, only count documents where "store" field matches (e.g., "Costco" → store: "Costco Wholesale")
- Aggregate all "total" values from matching store documents
```

### 4. Improved Context Building

Modified context to show metadata prominently:
```python
metadata_summary = f"Store: {store} | Total: {total} | Date: {date}"
context_parts.append(f"=== {filename} ===\nMetadata: {metadata_summary}\nContent:\n{truncated_content}")
```

### 5. Synced to Raspberry Pi

Created sync scripts:
- `sync_to_pi.py`: Syncs ChromaDB vector store and SQLite database
- `sync_code_to_pi.py`: Syncs updated backend code

Both scripts executed successfully.

## Verification

### Before Fix
```
10. IMG_4025.jpeg:
  ❌ NO EXTRACTED METADATA

11. IMG_4026.jpeg:
  ❌ NO EXTRACTED METADATA

12. KakaoTalk_20260219_155140673.jpg:
  ❌ NO EXTRACTED METADATA
```

### After Fix
```
10. IMG_4025.jpeg:
  Extracted (36 fields):
    total: 189.71
    store: Costco Wholesale
    subtotal: 187.76
    tax: 1.95
    ... and 32 more fields

11. IMG_4026.jpeg:
  Extracted (30 fields):
    total: 36.44
    store: NOFRILLS
    subtotal: 35.40
    tax: 1.04
    ... and 26 more fields

12. KakaoTalk_20260219_155140673.jpg:
  Extracted (30 fields):
    total: 222.18
    store: Costco Wholesale
    subtotal: 218.09
    tax: 4.09
    ... and 26 more fields
```

## Next Steps

1. **SSH to Pi**: `wsl -d Ubuntu -- ssh hws@192.168.1.139`
2. **Restart backend**: `cd ~/docubot && pkill -f 'python.*main.py' && ./scripts/start_pi.sh`
3. **Test query**: "2월에 코스트코에 총 얼마나 썼어?"
4. **Expected result**: Should return sum of Costco totals (189.71 + 222.18 = 411.89) from February receipts

## Files Modified

1. `backend/ollama_client.py` - Added custom options parameter support
2. `backend/image_processor.py` - Increased num_predict to 2048 for vision extraction
3. `backend/llm_generator.py` - Enhanced prompt to use metadata fields explicitly
4. `delete_old_costco_chunks.py` - Script to clean up duplicate chunks
5. `sync_to_pi.py` - Script to sync data to Pi
6. `sync_code_to_pi.py` - Script to sync code to Pi

## Key Insights

1. **Vision model needs high num_predict**: Receipt JSON can be very large (2000+ tokens). The default 256 was insufficient.

2. **Reprocessing doesn't auto-delete old chunks**: When reprocessing files, old chunks remain in the vector store. Need explicit deletion.

3. **Metadata must be visible to LLM**: Simply having metadata in the vector store isn't enough - the LLM needs to see it clearly in the context with explicit instructions on how to use it.

4. **Store name variations**: "코스트코" (Korean) maps to "Costco Wholesale" (English) in metadata. The LLM needs to handle this mapping.
