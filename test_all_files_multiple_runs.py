"""
Test vision extraction multiple times to check consistency.
"""
from backend.image_processor import ImageProcessor
from backend.ollama_client import OllamaClient
from backend.config import Config
import json
import os

# Initialize
vision_client = OllamaClient(Config.OLLAMA_ENDPOINT, Config.OLLAMA_VISION_MODEL)
processor = ImageProcessor(vision_client)

# All files
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

num_runs = 2
print(f"=== TESTING VISION EXTRACTION ({num_runs} runs per file) ===\n")

results = {}

for filename in files:
    file_path = os.path.join(mom_folder, filename)
    
    if not os.path.exists(file_path):
        continue
    
    print(f"\n{filename}:")
    results[filename] = []
    
    for run in range(num_runs):
        try:
            extraction = processor.process_image(file_path)
            metadata_count = len(extraction.flexible_metadata)
            
            # Check if valid JSON
            is_valid_json = False
            try:
                json.loads(extraction.raw_text)
                is_valid_json = True
            except:
                pass
            
            status = "✓" if metadata_count > 0 else "✗"
            print(f"  Run {run+1}: {status} {metadata_count} fields, JSON: {is_valid_json}, Length: {len(extraction.raw_text)}")
            
            results[filename].append({
                'metadata_count': metadata_count,
                'is_valid_json': is_valid_json,
                'length': len(extraction.raw_text)
            })
        except Exception as e:
            print(f"  Run {run+1}: ERROR - {e}")
            results[filename].append({'error': str(e)})

print("\n" + "="*60)
print("SUMMARY")
print("="*60)

for filename, runs in results.items():
    success_count = sum(1 for r in runs if r.get('metadata_count', 0) > 0)
    print(f"\n{filename}: {success_count}/{len(runs)} successful")
    
    if success_count < len(runs):
        print(f"  ⚠ Inconsistent results!")
        for i, r in enumerate(runs, 1):
            if 'error' in r:
                print(f"    Run {i}: ERROR")
            else:
                print(f"    Run {i}: {r['metadata_count']} fields, JSON: {r['is_valid_json']}, {r['length']} chars")
