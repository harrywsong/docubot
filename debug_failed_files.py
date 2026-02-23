"""
Debug the files that failed to extract metadata.
"""
from backend.image_processor import ImageProcessor
from backend.ollama_client import OllamaClient
from backend.config import Config
import json
import os

# Initialize
vision_client = OllamaClient(Config.OLLAMA_ENDPOINT, Config.OLLAMA_VISION_MODEL)
processor = ImageProcessor(vision_client)

# Failed files
failed_files = [
    'KakaoTalk_20260219_155002406.jpg',
    'KakaoTalk_20260219_155151473.jpg'
]

mom_folder = r'C:\Users\harry\OneDrive\Desktop\mom'

print("=== DEBUGGING FAILED FILES ===\n")

for filename in failed_files:
    file_path = os.path.join(mom_folder, filename)
    
    print(f"\n{'='*60}")
    print(f"FILE: {filename}")
    print('='*60)
    
    extraction = processor.process_image(file_path)
    
    print(f"\nRaw text ({len(extraction.raw_text)} chars):")
    print("-" * 60)
    print(extraction.raw_text)
    print("-" * 60)
    
    print(f"\nTrying to parse as JSON:")
    try:
        data = json.loads(extraction.raw_text)
        print(f"✓ Valid JSON (this shouldn't happen!)")
    except json.JSONDecodeError as e:
        print(f"✗ JSON Error: {e}")
        print(f"  Error at position: {e.pos}")
        print(f"  Line: {e.lineno}, Column: {e.colno}")
        
        # Show the problematic area
        if e.pos:
            start = max(0, e.pos - 50)
            end = min(len(extraction.raw_text), e.pos + 50)
            print(f"\n  Context around error:")
            print(f"  ...{extraction.raw_text[start:end]}...")
    
    print(f"\nChecking for common JSON issues:")
    
    # Check for unclosed brackets
    open_braces = extraction.raw_text.count('{')
    close_braces = extraction.raw_text.count('}')
    open_brackets = extraction.raw_text.count('[')
    close_brackets = extraction.raw_text.count(']')
    
    print(f"  Open braces: {open_braces}, Close braces: {close_braces}")
    print(f"  Open brackets: {open_brackets}, Close brackets: {close_brackets}")
    
    if open_braces != close_braces:
        print(f"  ⚠ Unbalanced braces! Missing {abs(open_braces - close_braces)} {'closing' if open_braces > close_braces else 'opening'} brace(s)")
    
    if open_brackets != close_brackets:
        print(f"  ⚠ Unbalanced brackets! Missing {abs(open_brackets - close_brackets)} {'closing' if open_brackets > close_brackets else 'opening'} bracket(s)")
    
    # Check if it's truncated
    if not extraction.raw_text.rstrip().endswith('}'):
        print(f"  ⚠ Response doesn't end with closing brace - likely truncated!")
        print(f"  Last 100 chars: ...{extraction.raw_text[-100:]}")
