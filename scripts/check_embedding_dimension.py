"""
Check the current embedding dimension in ChromaDB.

This script verifies that ChromaDB is using the correct embedding dimension
that matches your configured embedding model.

Usage:
    python scripts/check_embedding_dimension.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import Config
from backend.embedding_engine import get_embedding_engine
from backend.vector_store import get_vector_store

def main():
    print("=" * 60)
    print("Embedding Dimension Check")
    print("=" * 60)
    print()
    
    # Get configured embedding model
    print(f"Configured embedding model: {Config.EMBEDDING_MODEL}")
    print()
    
    # Initialize embedding engine
    print("Initializing embedding engine...")
    embedding_engine = get_embedding_engine()
    engine_dim = embedding_engine.get_embedding_dimension()
    print(f"✓ Embedding engine dimension: {engine_dim}")
    print()
    
    # Initialize vector store
    print("Initializing vector store...")
    vector_store = get_vector_store()
    
    # Get collection info
    collection = vector_store.collection
    count = collection.count()
    print(f"✓ Vector store initialized")
    print(f"  Collection: {collection.name}")
    print(f"  Document count: {count}")
    print()
    
    # Test embedding generation
    print("Testing embedding generation...")
    test_text = "This is a test sentence for embedding generation."
    test_embedding = embedding_engine.generate_embedding(test_text)
    actual_dim = len(test_embedding)
    print(f"✓ Generated test embedding")
    print(f"  Actual dimension: {actual_dim}")
    print()
    
    # Verify dimensions match
    print("=" * 60)
    print("Verification Results")
    print("=" * 60)
    print()
    
    if engine_dim == actual_dim:
        print(f"✅ PASS: Dimensions match ({engine_dim})")
    else:
        print(f"❌ FAIL: Dimension mismatch!")
        print(f"  Expected: {engine_dim}")
        print(f"  Actual: {actual_dim}")
        return 1
    
    # Check if ChromaDB has documents
    if count == 0:
        print("⚠️  WARNING: ChromaDB is empty")
        print("   You need to re-process your documents")
    else:
        print(f"✅ ChromaDB has {count} documents")
    
    print()
    print("=" * 60)
    print()
    
    # Model-specific info
    model_info = {
        "nomic-embed-text": {"dim": 768, "speed": "Fast", "quality": "Good"},
        "bge-m3": {"dim": 1024, "speed": "Medium", "quality": "Excellent"},
        "qwen3-embedding": {"dim": 4096, "speed": "Slow", "quality": "Excellent"},
        "mxbai-embed-large": {"dim": 1024, "speed": "Medium", "quality": "Good"},
    }
    
    current_model = Config.EMBEDDING_MODEL
    if current_model in model_info:
        info = model_info[current_model]
        print(f"Current model: {current_model}")
        print(f"  Dimension: {info['dim']}")
        print(f"  Speed: {info['speed']}")
        print(f"  Quality: {info['quality']}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
