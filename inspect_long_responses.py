"""
Inspect the full raw text of files producing very long responses.
"""
from backend.image_processor import ImageProcessor
from backend.ollama_client import OllamaClient
from backend.config import Config
import json

# Initialize
vision_client = OllamaClient(Config.OLLAMA_ENDPOINT, Config.OLLAMA_VISION_MODEL)
processor = ImageProcessor(vision_client)

# File that produces long response
file_path = r'C:\Users\harry\OneDrive\Desktop\mom\KakaoTalk_20260219_155002406_02.jpg'
filename = 'KakaoTalk_20260219_155002406_02.jpg'

print(f"=== INSPECTING: {filename} ===\n")

extraction = processor.process_image(file_path)

print(f"Raw text length: {len(extraction.raw_text)} chars")
print(f"Metadata fields: {len(extraction.flexible_metadata)}")
print()

print("="*60)
print("FULL RAW TEXT:")
print("="*60)
print(extraction.raw_text)
print("="*60)

# Try to parse
try:
    data = json.loads(extraction.raw_text)
    print(f"\n✓ Valid JSON")
    print(f"Top-level keys ({len(data)}): {list(data.keys())}")
except json.JSONDecodeError as e:
    print(f"\n✗ Invalid JSON")
    print(f"Error: {e}")
    print(f"Position: {e.pos}, Line: {e.lineno}, Column: {e.colno}")
    
    # Show context around error
    if e.pos:
        start = max(0, e.pos - 200)
        end = min(len(extraction.raw_text), e.pos + 200)
        print(f"\nContext around error (position {e.pos}):")
        print("..." + extraction.raw_text[start:end] + "...")
    
    # Check for patterns
    print(f"\nChecking for repetition patterns:")
    
    # Look for repeated words
    words = extraction.raw_text.split()
    if len(words) > 100:
        last_50_words = words[-50:]
        word_counts = {}
        for word in last_50_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        repeated = {w: c for w, c in word_counts.items() if c > 3}
        if repeated:
            print(f"  Highly repeated words in last 50 words: {repeated}")
    
    # Check for character repetition
    if len(extraction.raw_text) > 100:
        last_100 = extraction.raw_text[-100:]
        print(f"  Last 100 chars: {last_100}")
