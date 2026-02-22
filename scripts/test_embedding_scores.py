"""
Test embedding similarity scores with different queries.

This tests if the embedding model is working properly by comparing
similarity scores for Korean, English, and direct keyword queries.
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
    
    # Test queries - Korean, English, and keywords
    questions = [
        ("Korean", "2월에 코스트코에서 얼마나 썼어?"),
        ("English", "how much did i spend at costco in february"),
        ("Keywords", "costco february 2026 total"),
        ("Direct", "costco wholesale 222.18")
    ]
    
    embedding_engine = get_embedding_engine()
    vector_store = get_vector_store()
    
    for lang, question in questions:
        print("=" * 80)
        print(f"[{lang}] QUERY: {question}")
        print("=" * 80)
        
        # Generate embedding
        question_embedding = embedding_engine.generate_embedding(question)
        
        # Retrieve chunks
        results = vector_store.query(
            query_embedding=question_embedding,
            top_k=3,
            metadata_filter=None
        )
        
        # Show top 3 results
        for i, result in enumerate(results, 1):
            store = result.metadata.get('store', 'N/A')
            date = result.metadata.get('transaction_details_transaction_date', 'N/A')
            total = result.metadata.get('subtotals_total', 'N/A')
            
            print(f"  #{i} Score: {result.similarity_score:.4f} | {store} | {date} | ${total}")
        
        print()

if __name__ == "__main__":
    main()
