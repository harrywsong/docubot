"""Test vision model speed directly."""

import time
import base64
from backend.ollama_client import OllamaClient

# Create a simple test image (1x1 pixel)
test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

print("=" * 70)
print("VISION MODEL SPEED TEST")
print("=" * 70)

# Test qwen2.5vl:7b
print("\n🔍 Testing qwen2.5vl:7b (current model)...")
client_7b = OllamaClient(model="qwen2.5vl:7b", timeout=60)

start = time.time()
try:
    response = client_7b.generate(
        prompt="What do you see?",
        images=[test_image_base64],
        stream=False
    )
    elapsed_7b = time.time() - start
    print(f"✅ Response time: {elapsed_7b:.2f} seconds")
    print(f"   Response: {response.get('response', '')[:100]}")
except Exception as e:
    print(f"❌ Error: {e}")
    elapsed_7b = None

# Test qwen3-vl:2b
print("\n🔍 Testing qwen3-vl:2b (smaller model)...")
client_2b = OllamaClient(model="qwen3-vl:2b", timeout=60)

start = time.time()
try:
    response = client_2b.generate(
        prompt="What do you see?",
        images=[test_image_base64],
        stream=False
    )
    elapsed_2b = time.time() - start
    print(f"✅ Response time: {elapsed_2b:.2f} seconds")
    print(f"   Response: {response.get('response', '')[:100]}")
except Exception as e:
    print(f"❌ Error: {e}")
    elapsed_2b = None

# Test llava
print("\n🔍 Testing llava:latest (alternative model)...")
client_llava = OllamaClient(model="llava:latest", timeout=60)

start = time.time()
try:
    response = client_llava.generate(
        prompt="What do you see?",
        images=[test_image_base64],
        stream=False
    )
    elapsed_llava = time.time() - start
    print(f"✅ Response time: {elapsed_llava:.2f} seconds")
    print(f"   Response: {response.get('response', '')[:100]}")
except Exception as e:
    print(f"❌ Error: {e}")
    elapsed_llava = None

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
if elapsed_7b:
    print(f"qwen2.5vl:7b:  {elapsed_7b:.2f}s")
if elapsed_2b:
    print(f"qwen3-vl:2b:   {elapsed_2b:.2f}s (speedup: {elapsed_7b/elapsed_2b:.1f}x)" if elapsed_7b else f"qwen3-vl:2b:   {elapsed_2b:.2f}s")
if elapsed_llava:
    print(f"llava:latest:  {elapsed_llava:.2f}s (speedup: {elapsed_7b/elapsed_llava:.1f}x)" if elapsed_7b else f"llava:latest:  {elapsed_llava:.2f}s")

print("\n💡 Recommendation: Use the fastest model for document processing")
print("=" * 70)
