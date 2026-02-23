import chromadb
from chromadb.config import Settings

# Connect to ChromaDB
client = chromadb.PersistentClient(
    path="data/chromadb",
    settings=Settings(anonymized_telemetry=False)
)

# Get the documents collection
collection = client.get_collection(name="documents")

# Test the filter that should be used for "코스트코"
print("Testing store filter with $contains...")
print("=" * 80)

# This is what the query engine should be doing
results = collection.get(
    where={
        "$and": [
            {"user_id": 3},
            {"store": {"$contains": "Costco"}}
        ]
    },
    include=["metadatas"]
)

print(f"Found {len(results['ids'])} documents matching 'Costco'\n")

for i, doc_id in enumerate(results['ids']):
    metadata = results['metadatas'][i]
    print(f"{i+1}. {metadata.get('filename')}")
    print(f"   Store: {metadata.get('store')}")
    print(f"   Date: {metadata.get('date')}")
    print(f"   Total: {metadata.get('total')}")
    print()

print("=" * 80)
print("\nNow testing with Korean '코스트코'...")
results2 = collection.get(
    where={
        "$and": [
            {"user_id": 3},
            {"store": {"$contains": "코스트코"}}
        ]
    },
    include=["metadatas"]
)

print(f"Found {len(results2['ids'])} documents matching '코스트코'\n")

for i, doc_id in enumerate(results2['ids']):
    metadata = results2['metadatas'][i]
    print(f"{i+1}. {metadata.get('filename')}")
    print(f"   Store: {metadata.get('store')}")
    print(f"   Date: {metadata.get('date')}")
    print(f"   Total: {metadata.get('total')}")
    print()
