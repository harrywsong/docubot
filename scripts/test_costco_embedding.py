#!/usr/bin/env python3
"""Test if Costco receipt has a valid embedding."""
import sys
sys.path.insert(0, '.')

from backend.vector_store import get_vector_store

vs = get_vector_store()
results = vs.collection.get(limit=20, include=['metadatas', 'documents', 'embeddings'])

for i, (doc, meta, emb) in enumerate(zip(results['documents'], results['metadatas'], results['embeddings'])):
    if 'Costco' in doc or 'costco' in doc.lower():
        print(f'\n=== COSTCO RECEIPT (Chunk {i+1}) ===')
        print(f'Filename: {meta.get("filename")}')
        print(f'Has embedding: {emb is not None}')
        if emb is not None:
            print(f'Embedding dimension: {len(emb)}')
            print(f'Embedding sample (first 10 values): {emb[:10]}')
            print(f'Embedding stats: min={min(emb):.4f}, max={max(emb):.4f}, mean={sum(emb)/len(emb):.4f}')
        print(f'\nContent (first 300 chars):')
        print(doc[:300])
