"""
Test a query to see what chunks are retrieved and what the LLM sees.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.query_engine import get_query_engine
from backend.embedding_engine import get_embedding_engine
from backend.vector_store import get_vector_store

def main():
    print("=" * 60)
    print("Query Test")
    print("=" * 60)
    print()
    
    # Test query
    question = "2월에 코스트코에 총 얼마나 썼어?"
    user_id = 3
    
    print(f"Question: {question}")
    print(f"User ID: {user_id}")
    print()
    
    # Generate embedding
    print("Generating embedding...")
    embedding_engine = get_embedding_engine()
    question_embedding = embedding_engine.generate_embedding(question)
    print(f"✓ Embedding dimension: {len(question_embedding)}")
    print()
    
    # Query vector store
    print("Querying vector store...")
    vector_store = get_vector_store()
    results = vector_store.query(
        query_embedding=question_embedding,
        top_k=5,
        metadata_filter={"user_id": user_id}
    )
    print(f"✓ Retrieved {len(results)} chunks")
    print()
    
    # Display results
    print("=" * 60)
    print("Retrieved Chunks")
    print("=" * 60)
    print()
    
    for i, result in enumerate(results):
        print(f"Chunk {i+1}:")
        print(f"  Filename: {result.metadata.get('filename', 'N/A')}")
        print(f"  Similarity: {result.similarity_score:.3f}")
        print(f"  User ID: {result.metadata.get('user_id', 'N/A')}")
        print(f"  Metadata keys: {list(result.metadata.keys())}")
        print(f"  Content preview (first 300 chars):")
        print(f"    {result.content[:300]}")
        print()
    
    print("=" * 60)
    print()
    
    # Now test the full query engine
    print("Testing full query engine...")
    query_engine = get_query_engine()
    response = query_engine.query(
        question=question,
        user_id=user_id,
        conversation_history=[],
        top_k=5
    )
    
    print(f"Answer: {response['answer']}")
    print()
    print(f"Sources: {len(response['sources'])}")
    for i, source in enumerate(response['sources']):
        print(f"  {i+1}. {source['filename']} (score: {source['score']})")

if __name__ == "__main__":
    main()
