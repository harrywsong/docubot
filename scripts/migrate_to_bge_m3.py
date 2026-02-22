"""
Migrate from qwen3-embedding:8b to bge-m3 for better Korean-English cross-lingual search.

This script:
1. Updates the config to use bge-m3
2. Clears the vector store (removes old 4096-dim embeddings)
3. Reprocesses all documents with bge-m3 (1024-dim embeddings)

Why bge-m3?
- Excellent Korean-English cross-lingual performance
- 1024-dimensional embeddings (smaller, faster)
- Supports 100+ languages
- Specifically designed for multilingual semantic search
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.vector_store import get_vector_store
from backend.document_processor import DocumentProcessor
from backend.config import Config

def main():
    print("=" * 80)
    print("MIGRATE TO BGE-M3 EMBEDDING MODEL")
    print("=" * 80)
    print()
    print("This will:")
    print("  1. Clear the vector store (delete old qwen3-embedding data)")
    print("  2. Reprocess all documents with bge-m3")
    print("  3. Test Korean-English cross-lingual search")
    print()
    print("IMPORTANT: Make sure you have bge-m3 model installed:")
    print("  ollama pull bge-m3")
    print()
    
    confirm = input("Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("Aborted.")
        return
    
    # Initialize
    Config.ensure_data_directories()
    
    # Step 1: Clear vector store
    print("\n[1/3] Clearing vector store...")
    vector_store = get_vector_store()
    current_count = vector_store.collection.count()
    print(f"Current document count: {current_count}")
    
    if current_count > 0:
        vector_store.reset()
        print("✓ Vector store cleared")
    else:
        print("✓ Vector store already empty")
    
    # Step 2: Update config (manual step - user needs to do this)
    print("\n[2/3] Update configuration...")
    print("Please update backend/config.py:")
    print('  EMBEDDING_MODEL = "bge-m3"')
    print()
    input("Press Enter after updating config...")
    
    # Step 3: Find and process images
    print("\n[3/3] Processing documents with bge-m3...")
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
        print("No images found.")
        return
    
    # Process each image
    processor = DocumentProcessor()
    
    for i, image_path in enumerate(image_files, 1):
        print(f"\n[{i}/{len(image_files)}] Processing: {image_path.name}")
        
        try:
            folder_path = str(image_path.parent.relative_to(Path.cwd()))
            result = processor.process_document(
                file_path=str(image_path),
                folder_path=folder_path
            )
            
            if result['status'] == 'success':
                print(f"  ✓ Created {result.get('chunks_created', 0)} chunks")
            else:
                print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")
        
        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue
    
    # Final stats
    print("\n" + "=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)
    final_count = vector_store.collection.count()
    print(f"Total chunks in vector store: {final_count}")
    print("\nNow test with: python test_embedding_scores.py")

if __name__ == "__main__":
    main()
