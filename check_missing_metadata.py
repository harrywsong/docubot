"""
Check which files are missing flexible metadata extraction.
"""
from backend.vector_store import get_vector_store
import json

vs = get_vector_store()
results = vs.collection.get(include=['metadatas'])

print("=== FILES WITH MISSING METADATA ===\n")

files_with_metadata = {}
files_without_metadata = {}

for metadata in results['metadatas']:
    filename = metadata.get('filename', 'unknown')
    
    # Check for flexible metadata (excluding basic fields)
    basic_fields = ['chunk_index', 'user_id', 'file_type', 'folder_path', 'filename', 'page_number']
    flexible_fields = {k: v for k, v in metadata.items() if k not in basic_fields}
    
    if flexible_fields:
        if filename not in files_with_metadata:
            files_with_metadata[filename] = len(flexible_fields)
    else:
        if filename not in files_without_metadata:
            files_without_metadata[filename] = metadata.get('file_type', 'unknown')

print(f"Files WITH metadata: {len(files_with_metadata)}")
for filename, count in sorted(files_with_metadata.items()):
    print(f"  ✓ {filename} ({count} fields)")

print(f"\nFiles WITHOUT metadata: {len(files_without_metadata)}")
for filename, file_type in sorted(files_without_metadata.items()):
    print(f"  ✗ {filename} (type: {file_type})")

print(f"\n{'='*60}")
print(f"SUMMARY")
print(f"{'='*60}")
print(f"Total unique files: {len(files_with_metadata) + len(files_without_metadata)}")
print(f"With metadata: {len(files_with_metadata)}")
print(f"Without metadata: {len(files_without_metadata)}")
print(f"Success rate: {len(files_with_metadata) / (len(files_with_metadata) + len(files_without_metadata)) * 100:.1f}%")
