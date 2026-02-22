#!/usr/bin/env python3
"""Check Costco receipt metadata."""
import sys
sys.path.insert(0, '.')

from backend.vector_store import get_vector_store

vs = get_vector_store()
results = vs.collection.get(limit=20, include=['metadatas', 'documents'])

for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas'])):
    if 'Costco' in doc or 'costco' in doc.lower():
        print(f'\n=== COSTCO RECEIPT (Chunk {i+1}) ===')
        print(f'Filename: {meta.get("filename")}')
        print(f'\nALL METADATA FIELDS:')
        for key, value in sorted(meta.items()):
            print(f'  {key}: {value}')
        print(f'\nFULL CONTENT:')
        print(doc)
        print('\n' + '='*50)
