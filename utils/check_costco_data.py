"""Check Costco receipt data in database."""

import sqlite3
import json

conn = sqlite3.connect('data/app.db')
cursor = conn.cursor()

cursor.execute('''
    SELECT filename, merchant, date, total_amount, payment_method, card_last_4_digits, raw_metadata 
    FROM documents 
    WHERE merchant LIKE "%costco%" OR merchant LIKE "%코스트코%"
''')

rows = cursor.fetchall()

print(f"Found {len(rows)} Costco documents:\n")

for row in rows:
    filename, merchant, date, total_amount, payment_method, card_digits, raw_metadata = row
    print(f"Filename: {filename}")
    print(f"Merchant: {merchant}")
    print(f"Date: {date}")
    print(f"Total Amount: {total_amount}")
    print(f"Payment Method: {payment_method}")
    print(f"Card Last 4: {card_digits}")
    
    if raw_metadata:
        try:
            metadata = json.loads(raw_metadata)
            print(f"Metadata keys: {list(metadata.keys())}")
            print(f"Full metadata: {json.dumps(metadata, indent=2)}")
        except:
            print(f"Raw metadata: {raw_metadata[:300]}")
    
    print("-" * 80)

conn.close()
