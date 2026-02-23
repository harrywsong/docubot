import sqlite3
import json

conn = sqlite3.connect('data/app.db')
cursor = conn.cursor()

# Get all documents for user 3 (assuming that's you)
cursor.execute("""
    SELECT id, filename, metadata, content
    FROM documents 
    WHERE user_id = 3
    ORDER BY filename
""")

results = cursor.fetchall()

print(f"Found {len(results)} documents for user 3:\n")

for doc_id, filename, metadata_str, content in results:
    metadata = json.loads(metadata_str) if metadata_str else {}
    
    # Only show Costco receipts from February
    store = metadata.get('store', '')
    date = metadata.get('date', '')
    
    if 'costco' in store.lower() and date.startswith('2026-02'):
        print(f"=" * 80)
        print(f"Document ID: {doc_id}")
        print(f"Filename: {filename}")
        print(f"Store: {store}")
        print(f"Date: {date}")
        print(f"Total: {metadata.get('total', 'N/A')}")
        print(f"Subtotal: {metadata.get('subtotal', 'N/A')}")
        print(f"Tax: {metadata.get('tax', 'N/A')}")
        print(f"\nAll metadata fields:")
        for key, value in sorted(metadata.items()):
            print(f"  {key}: {value}")
        print(f"\nContent preview (first 300 chars):")
        print(content[:300] if content else "N/A")
        print()

conn.close()
