"""
Check the 3 files that are producing invalid JSON.
"""
from backend.image_processor import ImageProcessor
from backend.ollama_client import OllamaClient
from backend.config import Config
import json
import os

# Initialize
vision_client = OllamaClient(Config.OLLAMA_ENDPOINT, Config.OLLAMA_VISION_MODEL)
processor = ImageProcessor(vision_client)

mom_folder = r'C:\Users\harry\OneDrive\Desktop\mom'
failed_files = [
    'IMG_4025.jpeg',
    'IMG_4027.jpeg',
    'KakaoTalk_20260219_155140673.jpg'
]

for filename in failed_files:
    file_path = os.path.join(mom_folder, filename)
    
    print(f"\n{'='*60}")
    print(f"FILE: {filename}")
    print('='*60)
    
    extraction = processor.process_image(file_path)
    
    print(f"Raw length: {len(extraction.raw_text)} chars")
    print(f"\nLast 500 chars:")
    print(extraction.raw_text[-500:])
    
    # Try to parse
    try:
        data = json.loads(extraction.raw_text)
        print(f"\n✓ Valid JSON (unexpected!)")
    except json.JSONDecodeError as e:
        print(f"\n✗ Invalid JSON")
        print(f"Error: {e}")
        print(f"Position: {e.pos}")
        
        # Show context around error
        if e.pos:
            start = max(0, e.pos - 100)
            end = min(len(extraction.raw_text), e.pos + 100)
            print(f"\nContext around error:")
            print(extraction.raw_text[start:end])
