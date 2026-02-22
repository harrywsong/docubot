"""Test script to see what qwen3-vl:8b returns."""

import requests
import base64
from pathlib import Path

# Test with the Costco receipt
image_path = r"C:\Users\harry\OneDrive\Desktop\testing\KakaoTalk_20260219_155140673.jpg"

# Encode image to base64
with open(image_path, 'rb') as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

# Test 1: Simple prompt
print("=" * 80)
print("TEST 1: Simple prompt")
print("=" * 80)
response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "qwen3-vl:8b",
        "prompt": "What do you see in this image?",
        "images": [image_data],
        "stream": False
    }
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"Response: {result.get('response', 'NO RESPONSE')[:500]}")
else:
    print(f"Error: {response.text}")

# Test 2: JSON extraction prompt (like our current prompt)
print("\n" + "=" * 80)
print("TEST 2: JSON extraction prompt (current)")
print("=" * 80)
response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "qwen3-vl:8b",
        "prompt": """Extract all text and data from this document as JSON.

Rules:
- Only extract visible text (no guessing)
- Preserve original language
- Use snake_case field names
- Include "document_type" field

Return JSON format.""",
        "images": [image_data],
        "stream": False
    }
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"Response: {result.get('response', 'NO RESPONSE')[:500]}")
else:
    print(f"Error: {response.text}")

# Test 3: More explicit JSON prompt
print("\n" + "=" * 80)
print("TEST 3: Explicit JSON prompt")
print("=" * 80)
response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "qwen3-vl:8b",
        "prompt": "Extract the text from this receipt and return it as JSON with fields: store_name, date, total_amount, items.",
        "images": [image_data],
        "stream": False
    }
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"Response: {result.get('response', 'NO RESPONSE')[:500]}")
else:
    print(f"Error: {response.text}")

# Test 4: Check if model is loaded
print("\n" + "=" * 80)
print("TEST 4: Model info")
print("=" * 80)
response = requests.get("http://localhost:11434/api/tags")
if response.status_code == 200:
    models = response.json().get("models", [])
    qwen_models = [m for m in models if "qwen" in m.get("name", "").lower()]
    print(f"Found {len(qwen_models)} Qwen models:")
    for m in qwen_models:
        print(f"  - {m.get('name')}")
