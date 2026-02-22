"""Test if qwen3-vl uses <think> tags."""

from backend.ollama_client import OllamaClient, encode_image_to_base64

client = OllamaClient(model='qwen3-vl:8b')
img = encode_image_to_base64(r'C:\Users\harry\OneDrive\Desktop\testing\KakaoTalk_20260219_155140673.jpg')
result = client.generate('Extract as JSON: {"type": "...", "merchant": "..."}', images=[img])

text = result.get('response') or result.get('thinking', '')
print('HAS <think> TAG:', '<think>' in text)
print('HAS </think> TAG:', '</think>' in text)
print('\nFULL TEXT:')
print(text)
print('\n' + '='*80)
print('TEXT LENGTH:', len(text))
