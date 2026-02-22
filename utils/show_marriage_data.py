"""Show detailed data for marriage certificate (혼인관계증명서)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.vector_store import get_vector_store

vs = get_vector_store()
results = vs.query([0]*384, top_k=20)

print("\n" + "=" * 80)
print("ALL DOCUMENTS (searching for 혼인관계증명서)")
print("=" * 80)

found = False
for i, r in enumerate(results, 1):
    # Check all metadata fields for marriage-related keywords
    content_lower = r.content.lower()
    merchant = r.metadata.get('merchant', '').lower()
    doc_type = r.metadata.get('document_type', '').lower()
    
    # Search for marriage-related terms
    marriage_terms = ['혼인', 'marriage', '결혼', '배우자', 'spouse']
    
    if any(term in content_lower or term in merchant or term in doc_type for term in marriage_terms):
        found = True
        print(f"\nDocument {i}:")
        print(f"  Filename: {r.metadata.get('filename', 'N/A')}")
        print(f"  Merchant: {r.metadata.get('merchant', 'N/A')}")
        print(f"  Document Type: {r.metadata.get('document_type', 'N/A')}")
        print(f"\n  All Metadata:")
        for key, value in sorted(r.metadata.items()):
            if key not in ['folder_path', 'file_type', 'chunk_index']:
                print(f"    {key}: {value}")
        print(f"\n  Full Content (first 1000 chars):")
        print(f"    {r.content[:1000]}")
        print("\n" + "-" * 80)

if not found:
    print("\nNo marriage certificate found. Showing all Korean legal documents:")
    print("=" * 80)
    for i, r in enumerate(results, 1):
        filename = r.metadata.get('filename', '')
        if '기본증명서' in filename or '증명서' in r.content:
            print(f"\nDocument {i}:")
            print(f"  Filename: {filename}")
            print(f"  Merchant: {r.metadata.get('merchant', 'N/A')}")
            print(f"  Document Type: {r.metadata.get('document_type', 'N/A')}")
            print(f"\n  Content preview (first 500 chars):")
            print(f"    {r.content[:500]}")
            print("\n" + "-" * 80)
