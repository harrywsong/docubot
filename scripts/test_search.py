#!/usr/bin/env python3
"""Test semantic search for Costco query."""
import sys
sys.path.insert(0, '.')

from backend.embedding_engine import get_embedding_engine
from backend.vector_store import get_vector_store

# Test queries
queries = [
    "2월에 코스트코에서 얼마나 썼지?",  # How much did I spend at Costco in February?
    "Costco spending",
    "코스트코",  # Costco in Korean
]

embedding_engine = get_embedding_engine()
vector_store = get_vector_store()

for query in queries:
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print('='*60)
    
    # Generate embedding
    query_embedding = embedding_engine.generate_embedding(query)
    
    # Search
    results = vector_store.query(
        query_embedding=query_embedding,
        top_k=5
    )
    
    print(f"Found {len(results)} results:")
    for i, result in enumerate(results):
        print(f"\n--- Result {i+1} (score: {result.similarity_score:.3f}) ---")
        print(f"File: {result.metadata.get('filename')}")
        
        # Check if it's the Costco receipt
        if 'Costco' in result.content or 'costco' in result.content.lower():
            print("✓ THIS IS THE COSTCO RECEIPT!")
        
        # Show key fields
        if 'store' in result.metadata:
            print(f"Store: {result.metadata['store']}")
        if 'total' in result.metadata:
            print(f"Total: {result.metadata['total']}")
        
        print(f"Content preview: {result.content[:150]}...")
