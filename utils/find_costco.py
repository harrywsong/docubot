"""Find Costco receipt in vector store."""
from backend.vector_store import get_vector_store

vs = get_vector_store()
results = vs.collection.get()

print(f"Total chunks: {len(results['ids'])}")

for i, (doc_id, metadata) in enumerate(zip(results['ids'], results['metadatas'])):
    if 'costco' in str(metadata).lower():
        print(f"\n=== Found Costco Document ===")
        print(f"ID: {doc_id}")
        print(f"Metadata: {metadata}")
        print(f"Content: {results['documents'][i][:500]}")
        print()
