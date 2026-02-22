"""Test ChromaDB $contains operator."""
import sys
sys.path.insert(0, '.')

from backend.vector_store import get_vector_store

vs = get_vector_store()

# Get all image documents
results = vs.collection.get(
    where={"file_type": {"$eq": "image"}},
    include=['metadatas']
)

print(f"Total image documents: {len(results['ids'])}\n")

# Find Costco documents
costco_docs = []
for meta in results['metadatas']:
    merchant = meta.get('merchant', '')
    if 'Costco' in merchant:
        costco_docs.append(meta)
        print(f"Found: {meta.get('filename')}")
        print(f"  Merchant: {merchant}")
        print(f"  Date: {meta.get('date')}")
        print()

print(f"\nTotal Costco documents: {len(costco_docs)}")

# Test $contains operator
print("\n--- Testing $contains operator ---")
try:
    results_contains = vs.collection.get(
        where={"merchant": {"$contains": "Costco"}},
        include=['metadatas']
    )
    print(f"$contains 'Costco': {len(results_contains['ids'])} results")
except Exception as e:
    print(f"$contains failed: {e}")

# Test $eq operator
print("\n--- Testing $eq operator ---")
try:
    results_eq = vs.collection.get(
        where={"merchant": {"$eq": "Costco Wholesale"}},
        include=['metadatas']
    )
    print(f"$eq 'Costco Wholesale': {len(results_eq['ids'])} results")
except Exception as e:
    print(f"$eq failed: {e}")
