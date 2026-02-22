"""Debug JSON parsing in _parse_response."""

from backend.image_processor import ImageProcessor
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

processor = ImageProcessor()
image_path = r"C:\Users\harry\OneDrive\Desktop\testing\KakaoTalk_20260219_155140673.jpg"

extraction = processor.process_image(image_path)

print("\n" + "=" * 80)
print("RESULTS:")
print("=" * 80)
print(f"Metadata count: {len(extraction.flexible_metadata)}")
print(f"Metadata: {extraction.flexible_metadata}")
print(f"\nMerchant: {extraction.merchant}")
print(f"Date: {extraction.date}")
print(f"Total: {extraction.total_amount}")
