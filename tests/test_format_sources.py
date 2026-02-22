"""Test source formatting."""
import sys
sys.path.insert(0, '.')

from backend.query_engine import get_query_engine

qe = get_query_engine()

# Test query with user_id (using Harry's ID = 1)
result = qe.query("how much did i spend at costco on feb 11", user_id=1)

print("Answer:", result['answer'])
print("\nSources:")
for i, source in enumerate(result['sources'], 1):
    print(f"\n--- Source {i} ---")
    print(f"Filename: {source.get('filename')}")
    print(f"Score: {source.get('score')}")
    print(f"Metadata: {source.get('metadata')}")
    print(f"Chunk preview: {source.get('chunk', '')[:100]}")

