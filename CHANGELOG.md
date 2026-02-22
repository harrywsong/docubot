# Changelog

## Recent Updates

### LLM-Based Response Generation (Latest)
- **Added**: `qwen2.5:7b` LLM for natural response generation
- **Improved**: Responses are now generated using LLM instead of templates
- **Improved**: Better Korean language support with natural, context-aware responses
- **Improved**: Conversation context is now properly utilized by the LLM
- **Added**: Fallback to template-based responses if LLM fails
- **Fixed**: Korean merchant extraction pattern to avoid capturing dates

### Bug Fixes

#### Korean Query Support & Metadata Extraction Fixes
- **Fixed**: Korean queries now return responses in Korean
- **Fixed**: Legal documents no longer incorrectly labeled with receipt fields (total_amount, payment_method, card_last_4_digits)
- **Fixed**: Vision model prompt improved to prevent hallucinating receipt fields on non-receipt documents
- **Added**: Document type validation to filter out receipt-specific fields from non-receipt documents
- **Added**: Korean language detection and response generation
- **Added**: Korean keyword support for spending queries (얼마, 썼, 쓴, 지출, etc.)
- **Added**: Korean merchant extraction pattern ([merchant]에서)

#### Query Response Relevance Fixes
- **Fixed**: Korean queries return relevant documents with multilingual embedding model
- **Fixed**: Source lists now filter out low-similarity documents (< 0.5 threshold)
- **Fixed**: Metadata field extraction now checks card_last_4_digits and provides explicit "not captured" messages
- **Fixed**: Repeated queries now acknowledge repetition and provide explicit unavailability messages
- **Changed**: Embedding model from `all-MiniLM-L6-v2` to `paraphrase-multilingual-MiniLM-L12-v2` for 50+ language support

### Project Organization
- **Created**: `scripts/` directory for all startup/shutdown/setup scripts
  - Moved `start.bat`, `start.sh`, `stop.bat`, `stop.sh`
  - Moved `check-setup.bat`, `check-setup.sh`
  - Moved `setup_poppler.ps1`
  - All scripts now work from project root with automatic path resolution
- **Created**: `utils/` directory for utility Python scripts
  - Moved `check_data.py`, `check_folders.py`, `check_images.py`
  - Moved `check_processing_state.py`, `find_costco.py`
  - Moved `clean_old_documents.py`, `clear_all_data.py`, `force_reprocess.py`
- **Moved**: All test files to `tests/` directory
  - `test_chroma_contains.py` → `tests/test_chroma_contains.py`
  - `test_format_sources.py` → `tests/test_format_sources.py`
  - `test_query.py` → `tests/test_query.py`
- **Removed**: Outdated documentation files
  - `SMART_VISION_PROCESSING.md`
  - `FLEXIBLE_METADATA_SYSTEM.md`
  - `HYBRID_PROCESSING_SYSTEM.md`
  - `install_poppler.md`
- **Updated**: Startup scripts to use correct frontend port (5173)
  - `scripts/start.bat` - Windows startup script
  - `scripts/start.sh` - macOS/Linux startup script
- **Added**: README files in `scripts/` and `utils/` directories

### Test Coverage
- **Added**: Korean response tests (`tests/test_korean_response.py`)
- **Added**: Bug condition exploration tests (`tests/test_bugfix_query_response_relevance.py`)
- **Added**: Preservation property tests (`tests/test_preservation_query_response.py`)
- **Total**: 186+ tests passing

## Previous Updates

### Vision Processing System
- Implemented hybrid vision processing with Ollama
- Added flexible metadata extraction for all document types
- Support for receipts, legal documents, IDs, certificates, and more

### RAG Chatbot Features
- Document processing with ChromaDB vector store
- Conversation management with SQLite
- Spending aggregation and breakdown
- Source attribution with similarity scores
- Date and merchant filtering
