"""
Test the two problematic files that keep producing invalid JSON.
"""
from backend.image_processor import ImageProcessor
from backend.ollama_client import OllamaClient
from backend.config import Config
import json

# Initialize
vision_client = OllamaClient(Config.OLLAMA_ENDPOINT, Config.OLLAMA_VISION_MODEL)
processor = ImageProcessor(vision_client)

# Problematic files
files = [
    ('KakaoTalk_20260219_155002406_01.jpg', r'C:\Users\harry\OneDrive\Desktop\mom\KakaoTalk_20260219_155002406_01.jpg'),
    ('KakaoTalk_20260219_155002406_02.jpg', r'C:\Users\harry\OneDrive\Desktop\mom\KakaoTalk_20260219_155002406_02.jpg')
]

print("=== TESTING PROBLEMATIC FILES ===\n")

for filename, file_path in files:
    print(f"\n{'='*60}")
    print(f"FILE: {filename}")
    print('='*60)
    
    extraction = processor.process_image(file_path)
    
    print(f"\nRaw text length: {len(extraction.raw_text)} chars")
    print(f"Metadata fields extracted: {len(extraction.flexible_metadata)}")
    
    # Check if valid JSON
    try:
        data = json.loads(extraction.raw_text)
        print(f"✓ Valid JSON with {len(data)} top-level keys")
        print(f"Keys: {list(data.keys())[:10]}")
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON: {e}")
        print(f"  Error at position {e.pos}")
        
        # Check for truncation
        if not extraction.raw_text.rstrip().endswith('}'):
            print(f"  ⚠ TRUNCATED - doesn't end with closing brace")
            print(f"  Last 100 chars: ...{extraction.raw_text[-100:]}")
    
    print(f"\nFirst 500 chars:")
    print(extraction.raw_text[:500])
