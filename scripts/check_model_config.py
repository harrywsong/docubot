"""Diagnostic script to verify model configuration."""

from backend.config import Config
from backend.llm_generator import LLMGenerator
from backend.embedding_engine import get_embedding_engine
from backend.ollama_client import OllamaClient

print("=" * 70)
print("MODEL CONFIGURATION DIAGNOSTIC")
print("=" * 70)

print("\n📋 Config Settings:")
print(f"  OLLAMA_MODEL (text generation): {Config.OLLAMA_MODEL}")
print(f"  OLLAMA_VISION_MODEL (image processing): {Config.OLLAMA_VISION_MODEL}")
print(f"  CONVERSATIONAL_MODEL (Pi mode): {Config.CONVERSATIONAL_MODEL}")
print(f"  EMBEDDING_MODEL: {Config.EMBEDDING_MODEL}")
print(f"  ENABLE_DOCUMENT_PROCESSING: {Config.ENABLE_DOCUMENT_PROCESSING}")

print("\n🤖 Actual Models Being Used:")

# Check LLM Generator
llm_gen = LLMGenerator()
print(f"  LLMGenerator: {llm_gen.conversation_model}")

# Check Embedding Engine
embed_engine = get_embedding_engine()
print(f"  EmbeddingEngine: {embed_engine.model_name}")

# Check Vision Client (simulated)
vision_client = OllamaClient(Config.OLLAMA_ENDPOINT, Config.OLLAMA_VISION_MODEL)
print(f"  VisionClient: {vision_client.model}")

print("\n✅ Expected Configuration (Desktop Mode):")
print(f"  Text Generation: qwen2.5:14b")
print(f"  Vision Processing: qwen2.5vl:7b (or qwen3-vl:2b for speed)")
print(f"  Embeddings: mxbai-embed-large")

print("\n🔍 Checking Ollama Running Models:")
import subprocess
result = subprocess.run(["ollama", "ps"], capture_output=True, text=True)
print(result.stdout)

print("=" * 70)
