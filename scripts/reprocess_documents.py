#!/usr/bin/env python3
"""Reprocess all documents with the new qwen3-embedding model."""
import sys
sys.path.insert(0, '.')

from backend.config import Config
from backend.database import DatabaseManager
from backend.folder_manager import FolderManager
from backend.processing_state import ProcessingStateManager
from backend.embedding_engine import get_embedding_engine
from backend.vector_store import get_vector_store
from backend.image_processor import ImageProcessor
from backend.document_processor import DocumentProcessor
from pathlib import Path

# Initialize
Config.ensure_data_directories()

# Create all required components
db_manager = DatabaseManager()
folder_manager = FolderManager(db_manager)
state_manager = ProcessingStateManager(db_manager)
embedding_engine = get_embedding_engine()
vector_store = get_vector_store()
image_processor = ImageProcessor()

# Create document processor
processor = DocumentProcessor(
    db_manager=db_manager,
    folder_manager=folder_manager,
    state_manager=state_manager,
    embedding_engine=embedding_engine,
    vector_store=vector_store,
    image_processor=image_processor
)

# Get the test folder path
test_folder = Path(r"C:\Users\harry\OneDrive\Desktop\testing")

if not test_folder.exists():
    print(f"Error: Test folder not found: {test_folder}")
    sys.exit(1)

print(f"Processing documents from: {test_folder}")
print(f"Using embedding model: {Config.EMBEDDING_MODEL}")
print(f"Embedding dimension: 4096 (qwen3-embedding:8b)")
print()

# Add the folder first
folder_id = folder_manager.add_folder(str(test_folder))
print(f"Added folder with ID: {folder_id}")

# Process all folders
try:
    result = processor.process_folders()
    
    print(f"\n{'='*60}")
    print("Processing Complete!")
    print(f"{'='*60}")
    print(f"Total files processed: {result['total_files']}")
    print(f"Successfully processed: {result['successful']}")
    print(f"Failed: {result['failed']}")
    print(f"Total chunks created: {result['total_chunks']}")
    
    if result['errors']:
        print(f"\nErrors:")
        for error in result['errors']:
            print(f"  - {error}")
    
    print(f"\nDocuments are now embedded with qwen3-embedding:8b")
    print(f"This model supports multilingual search (Korean + English)")
    
except Exception as e:
    print(f"Error processing documents: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
