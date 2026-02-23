"""
Debug files with unusually long responses.
"""
from backend.image_processor import ImageProcessor
from backend.ollama_client import OllamaClient
from backend.config import Config
import json

# Initialize
vision_client = OllamaClient(Config.OLLAMA_ENDPOINT, Config.OLLAMA_VISION_MODEL)
processor = ImageProcessor(vision_client)

# Files with long responses
long_files = [
    ('IMG_4026.jpeg', r'C:\Users\harry\OneDrive\Desktop\mom\IMG_4026.jpeg'),
    ('KakaoTalk_20260219_155002406_02.jpg', r'C:\Users\harry\OneDrive\Desktop\mom\KakaoTalk_20260219_155002406_02.jpg')
]

print("=== DEBUGGING LONG RESPONSES ===\n")

for filename, file_path in long_files:
    print(f"\n{'='*60}")
    print(f"FILE: {filename}")
    print('='*60)
    
    extraction = processor.process_image(file_path)
    
    print(f"\nRaw text length: {len(extraction.raw_text)} chars")
    print(f"Metadata fields: {len(extraction.flexible_metadata)}")
    
    # Show full raw text
    print(f"\nFull raw text:")
    print("-" * 60)
    print(extraction.raw_text)
    print("-" * 60)
    
    # Try to parse
    try:
        data = json.loads(extraction.raw_text)
        print(f"\n✓ Valid JSON")
        print(f"Top-level keys: {list(data.keys())}")
    except json.JSONDecodeError as e:
        print(f"\n✗ JSON Error: {e}")
        print(f"  Position: {e.pos}, Line: {e.lineno}, Column: {e.colno}")
        
        # Check for truncation
        if not extraction.raw_text.rstrip().endswith('}'):
            print(f"  ⚠ Response doesn't end with closing brace - TRUNCATED!")
        
        # Check balance
        open_braces = extraction.raw_text.count('{')
        close_braces = extraction.raw_text.count('}')
        print(f"  Braces: {open_braces} open, {close_braces} close")
        if open_braces != close_braces:
            print(f"  ⚠ Unbalanced by {abs(open_braces - close_braces)}")
