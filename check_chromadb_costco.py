import chromadb
from chromadb.config import Settings

# Connect to ChromaDB
client = chromadb.PersistentClient(
    path="data/chromadb",
    settings=Settings(anonymized_telemetry=False)
)

# Get the documents collection
collection = client.get_collection(name="documents")

# Query for Costco receipts from February 2026 for user 3
results = collection.get(
    where={
        "$and": [
            {"user_id": 3},
            {"store": {"$contains": "Costco"}}
        ]
    },
    include=["metadatas", "documents"]
)

print(f"Found {len(results['ids'])} Costco documents for user 3:\n")

# Group by filename to avoid duplicates
seen_files = {}
for i, doc_id in enumerate(results['ids']):
    metadata = results['metadatas'][i]
    content = results['documents'][i]
    
    filename = metadata.get('filename', 'Unknown')
    date = metadata.get('date', '')
    
    # Only show February 2026
    if date.startswith('2026-02'):
        if filename not in seen_files:
            seen_files[filename] = {
                'metadata': metadata,
                'content': content
            }

print(f"Unique Costco receipts from February 2026: {len(seen_files)}\n")

for filename, data in sorted(seen_files.items()):
    metadata = data['metadata']
    content = data['content']
    
    print("=" * 80)
    print(f"Filename: {filename}")
    print(f"Store: {metadata.get('store', 'N/A')}")
    print(f"Date: {metadata.get('date', 'N/A')}")
    print(f"Total: {metadata.get('total', 'N/A')}")
    print(f"Subtotal: {metadata.get('subtotal', 'N/A')}")
    print(f"Tax: {metadata.get('tax', 'N/A')}")
    print(f"\nAll metadata fields:")
    for key, value in sorted(metadata.items()):
        if not key.startswith('_'):
            print(f"  {key}: {value}")
    print(f"\nContent preview (first 200 chars):")
    print(content[:200] if content else "N/A")
    print()

# Calculate total
totals = []
for filename, data in seen_files.items():
    total = data['metadata'].get('total')
    if total is not None:
        try:
            totals.append(float(total))
        except:
            pass

if totals:
    print("=" * 80)
    print(f"Sum of all Costco totals in February 2026: ${sum(totals):.2f}")
    print(f"Individual totals: {[f'${t:.2f}' for t in totals]}")
