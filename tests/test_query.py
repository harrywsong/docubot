"""Test the query with filters."""
import sys
sys.path.insert(0, '.')

from backend.vector_store import get_vector_store
from backend.embedding_engine import get_embedding_engine

# Get instances
vs = get_vector_store()
ee = get_embedding_engine()

# Generate embedding for the query
query_text = "how much did i spend at costco on feb 11"
embedding = ee.generate_embedding(query_text)

# Test with filters
filters = {'date': '2026-02-11', 'merchant': 'Costco'}

print(f"Testing query with filters: {filters}\n")

# Query
results = vs.query(
    query_embedding=embedding,
    top_k=5,
    metadata_filter=filters
)

print(f"Found {len(results)} results")

for i, result in enumerate(results, 1):
    print(f"\n--- Result {i} ---")
    print(f"Merchant: {result.metadata.get('merchant')}")
    print(f"Date: {result.metadata.get('date')}")
    print(f"Total: {result.metadata.get('total_amount')}")
    print(f"Similarity: {result.similarity_score:.3f}")
