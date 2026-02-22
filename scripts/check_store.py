#!/usr/bin/env python3
"""Quick check of vector store contents."""
import sys
sys.path.insert(0, '.')

from backend.vector_store import get_vector_store

vs = get_vector_store()
results = vs.collection.get(limit=20, include=['metadatas', 'documents'])

print(f'Total chunks: {len(results["ids"])}')

for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas'])):
    print(f'\n--- Chunk {i+1} ---')
    print(f'File: {meta.get("filename")}')
    
    # Show key metadata fields
    important_fields = ['document_type', 'store_name', 'merchant_name', 'business_name', 
                       'date', 'transaction_date', 'total', 'total_amount', 'amount']
    found_fields = {}
    for field in important_fields:
        if field in meta:
            found_fields[field] = meta[field]
    
    if found_fields:
        print(f'Key fields: {found_fields}')
    else:
        # Show first 5 metadata fields
        sample = dict(list(meta.items())[:5])
        print(f'Sample metadata: {sample}')
    
    print(f'Content: {doc[:200]}...')
