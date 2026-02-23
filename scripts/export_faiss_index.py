"""
Export ChromaDB to FAISS index for Pi deployment.

This script converts the ChromaDB vector store to a FAISS index that can be
used on the Pi without requiring an embedding model.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.vector_store import get_vector_store
from backend.faiss_store import FAISSVectorStore

def main():
    print("=" * 60)
    print("Export ChromaDB to FAISS Index")
    print("=" * 60)
    print()
    
    # Load ChromaDB
    print("Loading ChromaDB...")
    vector_store = get_vector_store()
    collection = vector_store.collection
    total_chunks = collection.count()
    print(f"✓ Loaded ChromaDB with {total_chunks} chunks")
    print()
    
    if total_chunks == 0:
        print("❌ No chunks in ChromaDB - nothing to export")
        return 1
    
    # Build FAISS index
    print("Building FAISS index...")
    faiss_store = FAISSVectorStore(index_path="data/faiss_index")
    faiss_store.build_from_chromadb(collection)
    print()
    
    # Verify
    stats = faiss_store.get_stats()
    print("=" * 60)
    print("Export Complete!")
    print("=" * 60)
    print()
    print(f"FAISS index created:")
    print(f"  - Total vectors: {stats['total_vectors']}")
    print(f"  - Dimension: {stats['dimension']}")
    print(f"  - Total chunks: {stats['total_chunks']}")
    print()
    print(f"Index saved to: data/faiss_index/")
    print(f"  - index.faiss (FAISS index file)")
    print(f"  - data.pkl (chunks + metadata)")
    print()
    print("Next steps:")
    print("  1. Sync to Pi: rsync -avz data/faiss_index/ hws@192.168.1.139:~/docubot/data/faiss_index/")
    print("  2. Update Pi config: USE_FAISS=true")
    print("  3. Restart Pi backend")
    print()

if __name__ == "__main__":
    sys.exit(main() or 0)
