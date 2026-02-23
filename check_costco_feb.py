import sqlite3
import json

conn = sqlite3.connect('data/app.db')
cursor = conn.cursor()

# Get all Costco receipts from February 2026
cursor.execute("""
    SELECT filename, metadata 
    FROM chunks 
    WHERE json_extract(metadata, '$.store') LIKE '%Costco%' 
    AND json_extract(metadata, '$.date') LIKE '2026-02%'
""")

results = cursor.fetchall()

print(f"Found {len(results)} Costco chunks from February 2026:\n")

totals = []
for filename, metadata_str in results:
    metadata = json.loads(metadata_str)
    print(f"File: {filename}")
    print(f"  Store: {metadata.get('store', 'N/A')}")
    print(f"  Date: {metadata.get('date', 'N/A')}")
    print(f"  Total: {metadata.get('total', 'N/A')}")
    print()
    
    # Collect totals
    if 'total' in metadata:
        try:
            total_val = float(metadata['total'])
            totals.append(total_val)
        except:
            pass

if totals:
    print(f"Sum of all totals: ${sum(totals):.2f}")
else:
    print("No totals found")

conn.close()
