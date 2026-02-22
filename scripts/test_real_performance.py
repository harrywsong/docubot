"""Test real document processing performance."""

import time
from pathlib import Path
from backend.image_processor import ImageProcessor
from backend.ollama_client import OllamaClient

# Find a test image
test_dir = Path("C:/Users/harry/OneDrive/Desktop/testing")
test_images = list(test_dir.glob("*.jpg"))

if not test_images:
    print("No test images found!")
    exit(1)

test_image = str(test_images[0])
print(f"Testing with: {test_image}")

print("\n" + "=" * 70)
print("REAL DOCUMENT PROCESSING TEST")
print("=" * 70)

# Test with qwen2.5vl:7b
print(f"\n🔍 Testing with qwen2.5vl:7b (larger model)...")
vision_client_7b = OllamaClient(model="qwen2.5vl:7b")
processor_7b = ImageProcessor(vision_client_7b)

start = time.time()
try:
    result = processor_7b.process_image(test_image)
    elapsed = time.time() - start
    print(f"✅ Processing time: {elapsed:.2f} seconds")
    print(f"   Merchant: {result.merchant}")
    print(f"   Date: {result.date}")
    print(f"   Total: {result.total_amount}")
    print(f"   Metadata fields: {len(result.flexible_metadata)}")
    print(f"\n   Raw response preview:")
    print(f"   {result.raw_text[:500]}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
