"""
Clear vector store and reprocess all documents with fixed vision extraction.

This script:
1. Clears the vector store (removes old data with duplicate fields)
2. Reprocesses all images in uploads/ folder
3. Re-embeds and stores them with clean metadata

Run this after the max_list_items=5 fix to get clean data.
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.vector_store import get_vector_store
from backend.document_processor import DocumentProcessor
from backend.config import Config

def main():
    print("=" * 60)
    print("CLEAR AND REPROCESS DOCUMENTS")
    print("=" * 60)
    
    # Initialize
    Config.ensure_data_directories()
    vector_store = get_vector_store()
    processor = DocumentProcessor()
    
    # Step 1: Clear vector store
    print("\n[1/3] Clearing vector store...")
    current_count = vector_store.collection.count()
    print(f"Current document count: {current_count}")
    
    if current_count > 0:
        confirm = input("Are you sure you want to delete all data? (yes/no): ")
        if confirm.lower() != "yes":
            print("Aborted.")
            return
        
        vector_store.reset()
        print("✓ Vector store cleared")
    else:
        print("✓ Vector store already empty")
    
    # Step 2: Find all images
    print("\n[2/3] Finding images to process...")
    uploads_dir = Path("uploads")
    
    if not uploads_dir.exists():
        print(f"Error: uploads/ directory not found")
        return
    
    # Find all image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    image_files = []
    
    for file_path in uploads_dir.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            image_files.append(file_path)
    
    print(f"Found {len(image_files)} images to process")
    
    if len(image_files) == 0:
        print("No images found. Add images to uploads/ folder first.")
        return
    
    # Step 3: Process each image
    print("\n[3/3] Processing images with fixed vision extraction...")
    
    for i, image_path in enumerate(image_files, 1):
        print(f"\n[{i}/{len(image_files)}] Processing: {image_path.name}")
        
        try:
            # Process image (uses max_list_items=5 fix)
            folder_path = str(image_path.parent.relative_to(Path.cwd()))
            result = processor.process_document(
                file_path=str(image_path),
                folder_path=folder_path
            )
            
            if result['status'] == 'success':
                print(f"  ✓ Extracted {len(result.get('metadata', {}))} metadata fields")
                print(f"  ✓ Created {result.get('chunks_created', 0)} chunks")
            else:
                print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")
        
        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue
    
    # Final stats
    print("\n" + "=" * 60)
    print("PROCESSING COMPLETE")
    print("=" * 60)
    final_count = vector_store.collection.count()
    print(f"Total chunks in vector store: {final_count}")
    print("\nYou can now test queries with clean data!")

if __name__ == "__main__":
    main()
