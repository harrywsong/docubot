"""Check what data is in the vector store."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.vector_store import get_vector_store

vs = get_vector_store()
results = vs.query([0]*384, top_k=10)

print(f"\nTotal documents in vector store: {len(results)}\n")
print("=" * 80)

for i, r in enumerate(results, 1):
    print(f"\nDocument {i}:")
    print(f"  Merchant: {r.metadata.get('merchant', 'N/A')}")
    print(f"  Date: {r.metadata.get('date', 'N/A')}")
    print(f"  Total Amount: {r.metadata.get('total_amount', 'N/A')}")
    print(f"  Document Type: {r.metadata.get('document_type', 'N/A')}")
    print(f"  Filename: {r.metadata.get('filename', 'N/A')}")
    print(f"  Content preview: {r.content[:200]}...")
