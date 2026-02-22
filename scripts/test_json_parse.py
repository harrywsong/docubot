"""Test JSON parsing."""

import json

# Sample from the output
raw_text = '{"document_type": "receipt", "merchant": "COSTCO WHOLESALE", "date": "2026/02/11", "total_amount": "$222.18", "currency": "USD", "all_text": "COSTCO WHOLESALE..."}'

print("Attempting to parse JSON...")
try:
    data = json.loads(raw_text.strip(), strict=False)
    print("SUCCESS! Parsed data:")
    print(data)
except json.JSONDecodeError as e:
    print(f"FAILED: {e}")
