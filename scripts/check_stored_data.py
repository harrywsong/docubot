"""Check what data is stored in the vector store"""
import sys
sys.path.insert(0, '.')

from backend.vector_store import VectorStore
from backend.config import Config

# Initialize vector store
Config.ensure_data_directories()
vector_store = VectorStore(persist_directory=Config.CHROMADB_PATH)
vector_store.initialize()

# Get stats
stats = vector_store.get_stats()
print(f"Total documents in vector store: {stats['total_chunks']}")
print()

# Get all documents
collection = vector_store.collection
results = collection.get(limit=10, include=['documents', 'metadatas'])

print("Stored documents:")
print("=" * 80)
for i, (doc, metadata) in enumerate(zip(results['documents'], results['metadatas'])):
    print(f"\nDocument {i+1}:")
    print(f"Filename: {metadata.get('filename', 'Unknown')}")
    print(f"File type: {metadata.get('file_type', 'Unknown')}")
    print(f"Content preview (first 200 chars):")
    print(doc[:200] if doc else "(empty)")
    print(f"Full metadata: {metadata}")
    print("-" * 80)
