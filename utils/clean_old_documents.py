"""Clean up old format documents from vector store."""
import sys
sys.path.insert(0, '.')

from backend.vector_store import get_vector_store

# Get vector store
vs = get_vector_store()

# Get all documents
stats = vs.get_stats()
total = stats.get('total_chunks', 0)

if total == 0:
    print("No documents found in vector store!")
    sys.exit(0)

print(f"Found {total} chunks in vector store")

# Get all documents
results = vs.collection.get(
    include=['metadatas']
)

# Find old format documents (those without merchant/date/total_amount metadata)
old_format_ids = []
for doc_id, meta in zip(results['ids'], results['metadatas']):
    # Old format: has no merchant, date, or total_amount fields
    if 'merchant' not in meta and 'date' not in meta and 'total_amount' not in meta:
        old_format_ids.append(doc_id)
        print(f"Found old format document: {meta.get('filename', 'Unknown')} (ID: {doc_id})")

if not old_format_ids:
    print("\nNo old format documents found! All documents have proper metadata.")
    sys.exit(0)

print(f"\nFound {len(old_format_ids)} old format documents to delete")
print("Deleting old format documents...")

# Delete old format documents
vs.collection.delete(ids=old_format_ids)

print(f"✓ Deleted {len(old_format_ids)} old format documents")

# Verify deletion
new_stats = vs.get_stats()
new_total = new_stats.get('total_chunks', 0)
print(f"\nVector store now has {new_total} chunks (was {total})")
print("\nPlease reprocess your documents to extract metadata properly.")
