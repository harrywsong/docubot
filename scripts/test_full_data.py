"""Show all data extracted from the test image."""

from backend.image_processor import ImageProcessor
import json

processor = ImageProcessor()
image_path = r"C:\Users\harry\OneDrive\Desktop\testing\KakaoTalk_20260219_155140673.jpg"

print("Processing image with qwen3-vl:8b...")
print("=" * 80)

extraction = processor.process_image(image_path)

print("\n" + "=" * 80)
print("EXTRACTED DATA")
print("=" * 80)

print("\n1. FLEXIBLE METADATA (all fields dynamically extracted by model):")
if extraction.flexible_metadata:
    for key, value in extraction.flexible_metadata.items():
        print(f"   {key}: {value}")
else:
    print("   (no metadata extracted)")

print("\n2. RAW TEXT FROM MODEL:")
print(extraction.raw_text)

print("\n3. FORMATTED TEXT OUTPUT:")
print(extraction.format_as_text())

print("\n4. JSON REPRESENTATION:")
print(json.dumps({
    "flexible_metadata": extraction.flexible_metadata,
    "raw_text": extraction.raw_text
}, indent=2))

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total metadata fields extracted: {len(extraction.flexible_metadata)}")
print(f"Metadata is searchable: {len(extraction.flexible_metadata) > 0}")
print(f"Model has complete freedom to create any fields based on document type")
