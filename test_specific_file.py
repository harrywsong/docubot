from backend.image_processor import ImageProcessor
from backend.ollama_client import OllamaClient
from backend.config import Config

# Initialize processor
processor = ImageProcessor()

# Process the problematic file
file_path = r"C:\Users\harry\OneDrive\Desktop\mom\KakaoTalk_20260219_155002406.jpg"

print(f"Processing: {file_path}\n")
print("=" * 80)

try:
    extraction = processor.process_image(file_path)
    
    print(f"Raw text length: {len(extraction.raw_text)} chars")
    print(f"\nRaw text preview (first 600 chars):")
    print(extraction.raw_text[:600])
    print("\n" + "=" * 80)
    
    print(f"\nFlexible metadata ({len(extraction.flexible_metadata)} fields):")
    if extraction.flexible_metadata:
        for key, value in sorted(extraction.flexible_metadata.items()):
            print(f"  {key}: {value}")
    else:
        print("  (empty)")
    
    print("\n" + "=" * 80)
    print(f"\nValidation: {extraction.validate()}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
