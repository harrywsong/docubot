"""Debug script to test image preprocessing"""
from PIL import Image
import tempfile

image_path = r'C:\Users\harry\OneDrive\Desktop\testing\KakaoTalk_20260219_155002406.jpg'

print(f"Testing image: {image_path}")

# Open image
img = Image.open(image_path)
print(f"Original - Mode: {img.mode}, Size: {img.size}, Format: {img.format}")

# Check EXIF
try:
    exif = img.getexif()
    print(f"EXIF data present: {len(exif) if exif else 0} entries")
    if exif:
        for key, value in exif.items():
            print(f"  EXIF {key}: {value}")
except Exception as e:
    print(f"No EXIF data: {e}")

# Check ICC profile
if 'icc_profile' in img.info:
    print(f"ICC profile present: {len(img.info['icc_profile'])} bytes")
else:
    print("No ICC profile")

# Try preprocessing
print("\nApplying preprocessing...")

# Convert to RGB
if img.mode != 'RGB':
    print(f"Converting from {img.mode} to RGB")
    img = img.convert('RGB')
else:
    print("Already RGB")

# Resize if needed
width, height = img.size
max_dim = 1536
if width > max_dim or height > max_dim:
    if width > height:
        new_width = max_dim
        new_height = int(height * (max_dim / width))
    else:
        new_height = max_dim
        new_width = int(width * (max_dim / height))
    print(f"Resizing from {width}x{height} to {new_width}x{new_height}")
    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
else:
    print(f"No resize needed: {width}x{height}")

# Save as clean JPEG
with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
    tmp_path = tmp.name
    img.save(tmp_path, 'JPEG', quality=92, optimize=True, progressive=False, exif=b'')
    print(f"Saved to: {tmp_path}")

# Verify saved image
img2 = Image.open(tmp_path)
print(f"\nProcessed - Mode: {img2.mode}, Size: {img2.size}, Format: {img2.format}")

# Check if EXIF is gone
try:
    exif2 = img2.getexif()
    print(f"EXIF data after processing: {len(exif2) if exif2 else 0} entries")
except:
    print("No EXIF data after processing")

print(f"\nProcessed image ready at: {tmp_path}")
