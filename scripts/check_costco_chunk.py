"""
Check what's in the Costco receipt chunk.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.vector_store import get_vector_store

def main():
    print("=" * 60)
    print("Costco Receipt Chunk Check")
    print("=" * 60)
    print()
    
    # Get vector store
    vector_store = get_vector_store()
    collection = vector_store.collection
    
    # Get all chunks for user 3
    results = collection.get(
        where={"user_id": 3},
        include=["metadatas", "documents"]
    )
    
    print(f"Total chunks for user 3: {len(results['ids'])}")
    print()
    
    # Find Costco receipt
    for i, (doc_id, metadata, document) in enumerate(zip(results['ids'], results['metadatas'], results['documents'])):
        filename = metadata.get('filename', '')
        if 'costco' in filename.lower() or '155140673' in filename:
            print(f"Found Costco receipt!")
            print(f"  ID: {doc_id}")
            print(f"  Filename: {filename}")
            print(f"  Metadata keys: {list(metadata.keys())}")
            print()
            print(f"  Full metadata:")
            for key, value in metadata.items():
                if key not in ['user_id', 'file_type', 'chunk_index', 'filename', 'folder_path']:
                    print(f"    {key}: {value}")
            print()
            print(f"  Content (first 1000 chars):")
            print(f"    {document[:1000]}")
            print()
            print(f"  Full content length: {len(document)} chars")
            print()
    
    # List all filenames
    print("=" * 60)
    print("All files for user 3:")
    print("=" * 60)
    filenames = set()
    for metadata in results['metadatas']:
        filenames.add(metadata.get('filename', 'Unknown'))
    
    for filename in sorted(filenames):
        print(f"  - {filename}")

if __name__ == "__main__":
    main()
