"""
Test vision extraction on all files to see which ones fail.
"""
from backend.image_processor import ImageProcessor
from backend.ollama_client import OllamaClient
from backend.config import Config
import json
import os

# Initialize
vision_client = OllamaClient(Config.OLLAMA_ENDPOINT, Config.OLLAMA_VISION_MODEL)
processor = ImageProcessor(vision_client)

# All files in the mom folder
mom_folder = r'C:\Users\harry\OneDrive\Desktop\mom'
files = [
    'IMG_4025.jpeg',
    'IMG_4026.jpeg',
    'IMG_4027.jpeg',
    'KakaoTalk_20260219_155002406.jpg',
    'KakaoTalk_20260219_155002406_01.jpg',
    'KakaoTalk_20260219_155002406_02.jpg',
    'KakaoTalk_20260219_155140673.jpg',
    'KakaoTalk_20260219_155151473.jpg'
]

print("=== TESTING VISION EXTRACTION ON ALL FILES ===\n")

results = []

for filename in files:
    file_path = os.path.join(mom_folder, filename)
    
    if not os.path.exists(file_path):
        print(f"✗ {filename}: FILE NOT FOUND")
        results.append({
            'filename': filename,
            'status': 'not_found',
            'metadata_count': 0
        })
        continue
    
    print(f"\nProcessing: {filename}")
    print("-" * 60)
    
    try:
        extraction = processor.process_image(file_path)
        
        raw_length = len(extraction.raw_text)
        metadata_count = len(extraction.flexible_metadata)
        
        print(f"Raw text length: {raw_length} chars")
        print(f"Metadata fields: {metadata_count}")
        
        # Check if raw text is valid JSON
        is_valid_json = False
        try:
            json.loads(extraction.raw_text)
            is_valid_json = True
            print(f"Raw text format: ✓ Valid JSON")
        except json.JSONDecodeError:
            print(f"Raw text format: ✗ NOT valid JSON")
        
        # Show raw text preview
        print(f"\nRaw text preview (first 300 chars):")
        print(extraction.raw_text[:300])
        
        if metadata_count > 0:
            print(f"\n✓ SUCCESS - Extracted {metadata_count} fields")
            # Show key fields
            if 'store' in extraction.flexible_metadata:
                print(f"  Store: {extraction.flexible_metadata['store']}")
            if 'total' in extraction.flexible_metadata:
                print(f"  Total: {extraction.flexible_metadata['total']}")
            
            results.append({
                'filename': filename,
                'status': 'success',
                'metadata_count': metadata_count,
                'raw_length': raw_length,
                'is_valid_json': is_valid_json
            })
        else:
            print(f"\n✗ FAILED - No metadata extracted")
            results.append({
                'filename': filename,
                'status': 'failed',
                'metadata_count': 0,
                'raw_length': raw_length,
                'is_valid_json': is_valid_json
            })
        
    except Exception as e:
        print(f"✗ ERROR: {e}")
        results.append({
            'filename': filename,
            'status': 'error',
            'metadata_count': 0,
            'error': str(e)
        })

print("\n" + "="*60)
print("SUMMARY")
print("="*60)

success_count = sum(1 for r in results if r['status'] == 'success')
failed_count = sum(1 for r in results if r['status'] == 'failed')
error_count = sum(1 for r in results if r['status'] == 'error')

print(f"\nTotal files: {len(results)}")
print(f"Success: {success_count}")
print(f"Failed (no metadata): {failed_count}")
print(f"Error: {error_count}")

if failed_count > 0:
    print(f"\nFiles that failed to extract metadata:")
    for r in results:
        if r['status'] == 'failed':
            print(f"  - {r['filename']}")
            print(f"    Raw length: {r.get('raw_length', 0)} chars")
            print(f"    Valid JSON: {r.get('is_valid_json', False)}")

print(f"\nSuccess rate: {success_count / len(results) * 100:.1f}%")
