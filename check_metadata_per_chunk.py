"""
Check metadata for each chunk, grouped by file.
"""
from backend.vector_store import get_vector_store
import json

vs = get_vector_store()
results = vs.collection.get(include=['metadatas'])

print("=== METADATA STATUS PER CHUNK ===\n")

# Group by filename
files = {}
for metadata in results['metadatas']:
    filename = metadata.get('filename', 'unknown')
    file_type = metadata.get('file_type', 'unknown')
    
    if filename not in files:
        files[filename] = {'chunks': [], 'file_type': file_type}
    
    # Check for flexible metadata
    basic_fields = ['chunk_index', 'user_id', 'file_type', 'folder_path', 'filename', 'page_number']
    flexible_fields = {k: v for k, v in metadata.items() if k not in basic_fields}
    
    files[filename]['chunks'].append({
        'has_metadata': len(flexible_fields) > 0,
        'field_count': len(flexible_fields),
        'chunk_index': metadata.get('chunk_index', 'N/A'),
        'page_number': metadata.get('page_number', 'N/A')
    })

# Display results
for filename in sorted(files.keys()):
    file_info = files[filename]
    chunks_with_meta = sum(1 for c in file_info['chunks'] if c['has_metadata'])
    total_chunks = len(file_info['chunks'])
    
    status = "✓" if chunks_with_meta == total_chunks else "⚠" if chunks_with_meta > 0 else "✗"
    
    print(f"{status} {filename} ({file_info['file_type']})")
    print(f"   Chunks: {total_chunks} total, {chunks_with_meta} with metadata, {total_chunks - chunks_with_meta} without")
    
    for i, chunk in enumerate(file_info['chunks'], 1):
        meta_status = "✓" if chunk['has_metadata'] else "✗"
        print(f"     {meta_status} Chunk {i}: {chunk['field_count']} fields (index={chunk['chunk_index']}, page={chunk['page_number']})")
    print()

print(f"{'='*60}")
print(f"SUMMARY")
print(f"{'='*60}")

total_files = len(files)
files_fully_extracted = sum(1 for f in files.values() if all(c['has_metadata'] for c in f['chunks']))
files_partially_extracted = sum(1 for f in files.values() if any(c['has_metadata'] for c in f['chunks']) and not all(c['has_metadata'] for c in f['chunks']))
files_no_extraction = sum(1 for f in files.values() if not any(c['has_metadata'] for c in f['chunks']))

print(f"Total files: {total_files}")
print(f"Fully extracted (all chunks have metadata): {files_fully_extracted}")
print(f"Partially extracted (some chunks have metadata): {files_partially_extracted}")
print(f"No extraction (no chunks have metadata): {files_no_extraction}")
