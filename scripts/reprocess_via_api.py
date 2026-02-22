#!/usr/bin/env python3
"""Reprocess documents via API."""
import requests
import time

# Folder path
folder_path = r"C:\Users\harry\OneDrive\Desktop\testing"

print("Step 1: Adding folder to watch list...")
response = requests.post(
    "http://localhost:8000/api/folders/add",
    json={"path": folder_path}
)
print(f"Response: {response.status_code}")
if response.status_code == 200:
    print(f"Folder added: {response.json()}")
else:
    print(f"Error: {response.text}")

print("\nStep 2: Processing documents...")
response = requests.post(
    "http://localhost:8000/api/process/start"
)
print(f"Response: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"Processed: {result.get('processed', 0)}")
    print(f"Skipped: {result.get('skipped', 0)}")
    print(f"Failed: {result.get('failed', 0)}")
    if result.get('failed_files'):
        print(f"Failed files: {result['failed_files']}")
else:
    print(f"Error: {response.text}")

print("\nDone!")
