#!/usr/bin/env python3
"""Test qwen3-embedding dimension."""
import requests

r = requests.post('http://localhost:11434/api/embed', json={'model': 'qwen3-embedding:8b', 'input': 'test'})
result = r.json()
embeddings = result.get('embeddings', [[]])
if embeddings and embeddings[0]:
    print(f'Dimension: {len(embeddings[0])}')
    print(f'Sample values: {embeddings[0][:10]}')
else:
    print('No embeddings returned')
