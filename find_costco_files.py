"""
Find Costco files in vector store.
"""
from backend.vector_store import get_vector_store

vs = get_vector_store()

costco_files = ['IMG_4025.jpeg', 'IMG_4026.jpeg', 'KakaoTalk_20260219_155140673.jpg']

print("=== SEARCHING FOR COSTCO FILES ===\n")

for filename in costco_files:
    results = vs.collection.get(
        where={'filename': {'$eq': filename}},
        include=['metadatas']
    )
    
    if results and results['ids']:
        print(f"✓ Found {filename}: {len(results['ids'])} chunk(s)")
        for i, metadata in enumerate(results['metadatas'], 1):
            basic_fields = ['chunk_index', 'user_id', 'file_type', 'folder_path', 'filename', 'page_number']
            flexible_fields = {k: v for k, v in metadata.items() if k not in basic_fields}
            print(f"  Chunk {i}: {len(flexible_fields)} metadata fields")
            if 'store' in flexible_fields:
                print(f"    Store: {flexible_fields['store']}")
            if 'total' in flexible_fields:
                print(f"    Total: {flexible_fields['total']}")
    else:
        print(f"✗ NOT FOUND: {filename}")
    print()
