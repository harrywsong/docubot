"""Check Costco receipt data in ChromaDB."""

import chromadb
from pathlib import Path

# Connect to ChromaDB
client = chromadb.PersistentClient(path=str(Path("data/chromadb").absolute()))
collection = client.get_collection("documents")

# Get all documents
results = collection.get(
    include=["metadatas", "documents"]
)

print(f"Total documents in ChromaDB: {len(results['ids'])}\n")

# Find Costco documents
costco_docs = []
for i, metadata in enumerate(results['metadatas']):
    merchant = metadata.get('merchant', '').lower()
    if 'costco' in merchant or '코스트코' in merchant:
        costco_docs.append({
            'id': results['ids'][i],
            'metadata': metadata,
            'content': results['documents'][i][:200]
        })

print(f"Found {len(costco_docs)} Costco documents:\n")

for doc in costco_docs:
    print(f"ID: {doc['id']}")
    print(f"Metadata: {doc['metadata']}")
    print(f"Content preview: {doc['content']}...")
    print("-" * 80)
