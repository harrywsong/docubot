#!/usr/bin/env python3
"""Test qwen3-embedding multilingual capabilities."""
import sys
sys.path.insert(0, '.')

from backend.embedding_engine import get_embedding_engine
import numpy as np

# Reset singleton to use new model
import backend.embedding_engine
backend.embedding_engine._embedding_engine_instance = None

engine = get_embedding_engine()

print(f"Model: {engine.model_name}")
print(f"Dimension: {engine.get_embedding_dimension()}")

# Test cross-lingual similarity
korean_text = "코스트코에서 쇼핑"  # Shopping at Costco
english_text = "Costco Wholesale shopping"
unrelated_text = "marriage certificate document"

print("\nGenerating embeddings...")
korean_emb = engine.generate_embedding(korean_text)
english_emb = engine.generate_embedding(english_text)
unrelated_emb = engine.generate_embedding(unrelated_text)

# Calculate cosine similarity
def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

korean_english_sim = cosine_similarity(korean_emb, english_emb)
korean_unrelated_sim = cosine_similarity(korean_emb, unrelated_emb)

print(f"\nCross-lingual similarity test:")
print(f"Korean '코스트코에서 쇼핑' <-> English 'Costco Wholesale shopping': {korean_english_sim:.4f}")
print(f"Korean '코스트코에서 쇼핑' <-> English 'marriage certificate document': {korean_unrelated_sim:.4f}")

if korean_english_sim > korean_unrelated_sim:
    print("\n✓ SUCCESS: Korean-English cross-lingual search should work!")
else:
    print("\n✗ WARNING: Cross-lingual similarity is low")
