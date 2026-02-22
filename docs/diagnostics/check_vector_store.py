#!/usr/bin/env python3
"""Check what's actually in the vector store."""

from backend.vector_store import get_vector_store

vs = get_vector_store()
results = vs.collection.get(limit=10, include=['metadatas', 'documents'])

print(f'Total chunks: {len(results["ids"])}')
print('\nChunk contents:')

for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas'])):
    print(f'\n--- Chunk {i+1} ---')
    print(f'File: {meta.get("filename", "unknown")}')
    print(f'File type: {meta.get("file_type", "N/A")}')
    
    # Show all metadata fields dynamically
    print(f'Metadata fields: {", ".join(meta.keys())}')
    
    # Show a few sample metadata values (first 5 non-internal fields)
    sample_fields = [k for k in meta.keys() if not k.startswith('_')][:5]
    for field in sample_fields:
        print(f'  {field}: {meta.get(field, "N/A")}')
    
    print(f'Content preview: {doc[:300]}')
    print('...')
