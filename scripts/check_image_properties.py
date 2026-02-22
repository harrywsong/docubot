"""Quick script to check image properties"""
from PIL import Image
import os

test_images = [
    "testing/KakaoTalk_20260219_155002406.jpg",
    "testing/KakaoTalk_20260219_155002406_01.jpg",
    "testing/KakaoTalk_20260219_155002406_02.jpg",
    "testing/KakaoTalk_20260219_155140673.jpg",
    "testing/KakaoTalk_20260219_155151473.jpg",
]

for img_path in test_images:
    if os.path.exists(img_path):
        try:
            img = Image.open(img_path)
            print(f"\n{img_path}:")
            print(f"  Format: {img.format}")
            print(f"  Mode: {img.mode}")
            print(f"  Size: {img.size}")
            
            # Check for EXIF data
            exif = img.getexif()
            if exif:
                print(f"  EXIF data: {len(exif)} tags")
                # Print orientation if present
                if 274 in exif:  # Orientation tag
                    print(f"  Orientation tag: {exif[274]}")
            
            # Check for ICC profile
            if 'icc_profile' in img.info:
                print(f"  ICC Profile: Present ({len(img.info['icc_profile'])} bytes)")
            
        except Exception as e:
            print(f"\n{img_path}: ERROR - {e}")
