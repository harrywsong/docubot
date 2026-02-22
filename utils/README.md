# Utils Directory

This directory contains utility scripts for managing and debugging the RAG Chatbot application.

## Available Utilities

### Data Inspection

- **check_data.py** - Inspect ChromaDB vector store contents
- **check_folders.py** - List all configured folders and their status
- **check_images.py** - Verify image processing and metadata extraction
- **check_processing_state.py** - Check file processing state in the database
- **find_costco.py** - Search for specific documents (example: Costco receipts)

### Data Management

- **clean_old_documents.py** - Remove old or outdated documents from the vector store
- **clear_all_data.py** - Clear all data (database, vector store, processed files)
- **force_reprocess.py** - Force reprocessing of all documents

## Usage

All utilities should be run from the project root directory:

```bash
# Example: Check what's in the vector store
python utils/check_data.py

# Example: Clear all data and start fresh
python utils/clear_all_data.py

# Example: Force reprocess all documents
python utils/force_reprocess.py
```

## Notes

- These utilities directly access the database and vector store
- Some utilities (like `clear_all_data.py`) are destructive - use with caution
- Make sure the backend server is stopped before running data management utilities
- Always backup your data before running destructive operations
