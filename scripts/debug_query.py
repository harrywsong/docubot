"""
Debug script to see what data is being retrieved for Korean queries.

This shows:
1. What chunks are retrieved by embedding search
2. What metadata fields are in those chunks
3. What content is being passed to the LLM
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.embedding_engine import get_embedding_engine
from backend.vector_store import get_vector_store
from backend.config import Config

def main():
    Config.ensure_data_directories()
    
    # Test queries - both Korean and English
    questions = [
        "2월에 코스트코에서 얼마나 썼어?",
        "how much did i spend at costco in february",
        "costco february 2026"
    ]
    print("=" * 80)
    print(f"DEBUGGING QUERY: {question}")
    print("=" * 80)
    
    # Generate embedding
    print("\n[1] Generating embedding...")
    embedding_engine = get_embedding_engine()
    question_embedding = embedding_engine.generate_embedding(question)
    print(f"✓ Generated embedding (dimension: {len(question_embedding)})")
    
    # Retrieve chunks
    print("\n[2] Retrieving similar chunks...")
    vector_store = get_vector_store()
    results = vector_store.query(
        query_embedding=question_embedding,
        top_k=5,
        metadata_filter=None
    )
    
    print(f"✓ Found {len(results)} chunks")
    
    # Show each result
    for i, result in enumerate(results, 1):
        print("\n" + "=" * 80)
        print(f"RESULT #{i} (Similarity: {result.similarity_score:.3f})")
        print("=" * 80)
        
        # Show metadata
        print("\nMETADATA:")
        for key, value in result.metadata.items():
            # Truncate long values
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:100] + "..."
            print(f"  {key}: {value_str}")
        
        # Show content preview
        print("\nCONTENT PREVIEW:")
        content_preview = result.content[:500]
        print(f"  {content_preview}")
        if len(result.content) > 500:
            print(f"  ... (total {len(result.content)} chars)")
    
    # Show what would be passed to LLM
    print("\n" + "=" * 80)
    print("WHAT LLM RECEIVES:")
    print("=" * 80)
    
    for i, result in enumerate(results, 1):
        print(f"\n=== Document {i} ===")
        print(result.content)

if __name__ == "__main__":
    main()
