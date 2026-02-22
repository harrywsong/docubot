"""Check what data is stored in the vector database."""
import sys
sys.path.insert(0, '.')

from backend.vector_store import get_vector_store
import json

# Get vector store
vs = get_vector_store()

# Get stats
stats = vs.get_stats()
print(f"Total documents in vector store: {stats.get('count', 0)}")
print(f"Stats: {stats}")
print()

# Get all documents
total = stats.get('total_chunks', 0)
if total > 0:
    print(f"Found {total} chunks!")
    results = vs.collection.get(
        limit=20,
        include=['metadatas', 'documents']
    )
    
    print("=== Stored Documents ===")
    for i, (meta, doc) in enumerate(zip(results['metadatas'], results['documents'])):
        print(f"\n--- Document {i+1} ---")
        print(f"Metadata: {json.dumps(meta, indent=2)}")
        print(f"Content preview: {doc[:300]}")
        print()
else:
    print("No documents found in vector store!")
    print("\nThis means either:")
    print("1. No documents were successfully processed")
    print("2. The vision model didn't extract any text from images")
    print("3. The PDF had no extractable text")
