"""Check image documents in the vector store."""
import sys
sys.path.insert(0, '.')

from backend.vector_store import get_vector_store
import json

# Get vector store
vs = get_vector_store()

# Get all documents
results = vs.collection.get(
    where={"file_type": {"$eq": "image"}},
    include=['metadatas', 'documents']
)

print(f"Found {len(results['ids'])} image documents:\n")

for i, (meta, doc) in enumerate(zip(results['metadatas'], results['documents']), 1):
    print(f"--- Image {i} ---")
    print(f"Filename: {meta.get('filename')}")
    print(f"Merchant: {meta.get('merchant', 'N/A')}")
    print(f"Date: {meta.get('date', 'N/A')}")
    print(f"Total: {meta.get('total_amount', 'N/A')}")
    print(f"Content preview: {doc[:200]}")
    print()
