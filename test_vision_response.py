"""
Test what the vision model actually returns.
"""
from backend.image_processor import ImageProcessor
from backend.ollama_client import OllamaClient
from backend.config import Config
import json

# Initialize
vision_client = OllamaClient(Config.OLLAMA_ENDPOINT, Config.OLLAMA_VISION_MODEL)
processor = ImageProcessor(vision_client)

# Test on a Costco receipt
image_path = r'C:\Users\harry\OneDrive\Desktop\mom\IMG_4025.jpeg'

print("=== TESTING VISION MODEL RESPONSE ===\n")
print(f"Image: {image_path}\n")

extraction = processor.process_image(image_path)

print(f"Raw text length: {len(extraction.raw_text)} chars\n")
print("="*60)
print("RAW TEXT FROM VISION MODEL:")
print("="*60)
print(extraction.raw_text[:1000])  # First 1000 chars
print("\n... (truncated)\n")

print("="*60)
print("PARSED FLEXIBLE METADATA:")
print("="*60)
print(f"Field count: {len(extraction.flexible_metadata)}")
if extraction.flexible_metadata:
    print("\nFields:")
    for key, value in list(extraction.flexible_metadata.items())[:10]:
        print(f"  {key}: {value}")
    if len(extraction.flexible_metadata) > 10:
        print(f"  ... and {len(extraction.flexible_metadata) - 10} more")
else:
    print("NO METADATA EXTRACTED!")
    print("\nTrying to parse raw text as JSON manually:")
    try:
        data = json.loads(extraction.raw_text)
        print(f"✓ Raw text IS valid JSON with {len(data)} top-level keys")
        print(f"Keys: {list(data.keys())}")
    except json.JSONDecodeError as e:
        print(f"✗ Raw text is NOT valid JSON: {e}")
        print("\nChecking for JSON patterns:")
        if '{' in extraction.raw_text and '}' in extraction.raw_text:
            print("  Contains curly braces (might be JSON-like text)")
        if 'store' in extraction.raw_text.lower():
            print("  Contains 'store' keyword")
        if 'total' in extraction.raw_text.lower():
            print("  Contains 'total' keyword")
