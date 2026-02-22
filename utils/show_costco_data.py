"""Show detailed data for Costco document."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.vector_store import get_vector_store

vs = get_vector_store()
results = vs.query([0]*384, top_k=20)

print("\n" + "=" * 80)
print("COSTCO DOCUMENT DATA")
print("=" * 80)

for i, r in enumerate(results, 1):
    merchant = r.metadata.get('merchant', '').lower()
    if 'costco' in merchant:
        print(f"\nDocument {i}:")
        print(f"  Filename: {r.metadata.get('filename', 'N/A')}")
        print(f"  Merchant: {r.metadata.get('merchant', 'N/A')}")
        print(f"  Date: {r.metadata.get('date', 'N/A')}")
        print(f"  Total Amount: {r.metadata.get('total_amount', 'N/A')}")
        print(f"  Payment Method: {r.metadata.get('payment_method', 'N/A')}")
        print(f"  Card Last 4: {r.metadata.get('card_last_4_digits', 'N/A')}")
        print(f"  Document Type: {r.metadata.get('document_type', 'N/A')}")
        print(f"\n  All Metadata:")
        for key, value in sorted(r.metadata.items()):
            if key not in ['filename', 'folder_path', 'file_type', 'chunk_index']:
                print(f"    {key}: {value}")
        print(f"\n  Full Content:")
        print(f"    {r.content}")
        print("\n" + "=" * 80)
