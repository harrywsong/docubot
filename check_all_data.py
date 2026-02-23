import chromadb
from chromadb.config import Settings

# Connect to ChromaDB
client = chromadb.PersistentClient(
    path="data/chromadb",
    settings=Settings(anonymized_telemetry=False)
)

# Get the documents collection
collection = client.get_collection(name="documents")

# Get all documents for user 3
results = collection.get(
    where={"user_id": 3},
    include=["metadatas", "documents"],
    limit=100
)

print(f"Total documents for user 3: {len(results['ids'])}\n")

# Group by filename
files = {}
for i, doc_id in enumerate(results['ids']):
    metadata = results['metadatas'][i]
    filename = metadata.get('filename', 'Unknown')
    
    if filename not in files:
        files[filename] = metadata

print(f"Unique files: {len(files)}\n")

# Show all files with their metadata
for filename, metadata in sorted(files.items()):
    print(f"{filename}")
    print(f"  All metadata:")
    for key, value in sorted(metadata.items()):
        if not key.startswith('_'):  # Skip internal fields
            print(f"    {key}: {value}")
    print()
