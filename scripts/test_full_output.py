"""Check the full output from qwen3-vl to see if JSON comes after thinking."""

from backend.image_processor import ImageProcessor

processor = ImageProcessor()
image_path = r"C:\Users\harry\OneDrive\Desktop\testing\KakaoTalk_20260219_155140673.jpg"

extraction = processor.process_image(image_path)

print("FULL RAW TEXT:")
print("=" * 80)
print(extraction.raw_text)
print("=" * 80)
print(f"\nTotal length: {len(extraction.raw_text)} chars")
print(f"\nFlexible metadata: {extraction.flexible_metadata}")
print(f"\nMetadata count: {len(extraction.flexible_metadata)}")
