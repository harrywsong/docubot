#!/usr/bin/env python3
"""Test if multilingual search is working with qwen3-embedding."""
import sys
sys.path.insert(0, '.')

from backend.embedding_engine import get_embedding_engine
from backend.vector_store import get_vector_store

# Test Korean query
query = "2월에 코스트코에서 얼마나 썼어?"

print(f"Query: {query}")
print(f"Embedding model: qwen3-embedding:8b")
print()

embedding_engine = get_embedding_engine()
vector_store = get_vector_store()

# Generate embedding
print("Generating query embedding...")
query_embedding = embedding_engine.generate_embedding(query)
print(f"Embedding dimension: {len(query_embedding)}")

# Search
print("\nSearching vector store...")
results = vector_store.query(
    query_embedding=query_embedding,
    top_k=5
)

print(f"\nFound {len(results)} results:")
for i, result in enumerate(results):
    print(f"\n--- Result {i+1} (score: {result.similarity_score:.3f}) ---")
    print(f"File: {result.metadata.get('filename')}")
    
    # Check if it's the Costco receipt
    if 'Costco' in result.content or 'costco' in result.content.lower():
        print("✓✓✓ THIS IS THE COSTCO RECEIPT! ✓✓✓")
    
    # Show key fields
    if 'store' in result.metadata:
        print(f"Store: {result.metadata['store']}")
    if 'total' in result.metadata:
        print(f"Total: {result.metadata['total']}")
    
    # Show date fields
    date_fields = [k for k in result.metadata.keys() if 'date' in k.lower() or 'time' in k.lower()]
    if date_fields:
        print(f"Date fields: {date_fields[:3]}")
        for field in date_fields[:2]:
            print(f"  {field}: {result.metadata[field]}")
    
    print(f"Content preview: {result.content[:200]}...")
