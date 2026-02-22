"""Test processing a single image with qwen3-vl."""

from backend.image_processor import ImageProcessor

# Initialize processor (will use default config with enable_thinking: 0)
processor = ImageProcessor()

# Test with Costco receipt
image_path = r"C:\Users\harry\OneDrive\Desktop\testing\KakaoTalk_20260219_155140673.jpg"

print("Processing image with qwen3-vl:8b...")
print("=" * 80)

try:
    extraction = processor.process_image(image_path)
    print(f"\nExtraction successful!")
    print(f"Raw text length: {len(extraction.raw_text)}")
    print(f"Raw text preview (first 500 chars):\n{extraction.raw_text[:500]}")
    print(f"\nFlexible metadata fields: {len(extraction.flexible_metadata)}")
    if extraction.flexible_metadata:
        print("Metadata keys:", list(extraction.flexible_metadata.keys())[:10])
    print(f"\nFormatted text preview (first 500 chars):\n{extraction.format_as_text()[:500]}")
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
