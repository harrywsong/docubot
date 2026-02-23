"""
Reprocess Costco files to extract metadata.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.image_processor import ImageProcessor
from backend.ollama_client import OllamaClient
from backend.embedding_engine import EmbeddingEngine
from backend.vector_store import get_vector_store
from backend.models import DocumentChunk
from backend.config import Config
from pathlib import Path

print("=== REPROCESSING COSTCO FILES ===\n")

# Initialize
vision_client = OllamaClient(Config.OLLAMA_ENDPOINT, Config.OLLAMA_VISION_MODEL)
processor = ImageProcessor(vision_client)
embedding_engine = EmbeddingEngine(
    model_name=Config.EMBEDDING_MODEL,
    ollama_endpoint=Config.OLLAMA_ENDPOINT
)
vs = get_vector_store()

# Costco files
costco_files = [
    r'C:\Users\harry\OneDrive\Desktop\mom\IMG_4025.jpeg',
    r'C:\Users\harry\OneDrive\Desktop\mom\IMG_4026.jpeg',
    r'C:\Users\harry\OneDrive\Desktop\mom\KakaoTalk_20260219_155140673.jpg'
]

for file_path in costco_files:
    filename = os.path.basename(file_path)
    print(f"\nProcessing: {filename}")
    
    if not os.path.exists(file_path):
        print(f"  ✗ File not found: {file_path}")
        continue
    
    # Delete existing chunks
    print(f"  Deleting existing chunks...")
    results = vs.collection.get(
        where={'filename': {'$eq': filename}},
        include=['metadatas']
    )
    if results and results['ids']:
        vs.collection.delete(ids=results['ids'])
        print(f"  ✓ Deleted {len(results['ids'])} old chunk(s)")
    
    # Process with vision model
    print(f"  Extracting with vision model...")
    try:
        extraction = processor.process_image(file_path)
        print(f"  ✓ Extracted {len(extraction.flexible_metadata)} metadata fields")
        
        if extraction.flexible_metadata:
            # Show sample fields
            sample_fields = list(extraction.flexible_metadata.items())[:5]
            for key, value in sample_fields:
                print(f"    {key}: {value}")
            if len(extraction.flexible_metadata) > 5:
                print(f"    ... and {len(extraction.flexible_metadata) - 5} more fields")
        else:
            print(f"  ⚠ No metadata extracted!")
            print(f"  Raw text length: {len(extraction.raw_text)}")
            print(f"  Raw text preview: {extraction.raw_text[:200]}")
        
        # Format as text
        formatted_text = extraction.format_as_text()
        
        # Create chunk with metadata
        path = Path(file_path)
        metadata = {
            'user_id': 3,  # Mom's user_id
            'filename': filename,
            'folder_path': str(path.parent),
            'file_type': 'image',
            'chunk_index': 0
        }
        
        # Add flexible metadata
        if extraction.flexible_metadata:
            for key, value in extraction.flexible_metadata.items():
                metadata[key] = value
        
        chunk = DocumentChunk(
            content=formatted_text,
            metadata=metadata
        )
        
        # Generate embedding
        print(f"  Generating embedding...")
        embedding = embedding_engine.generate_embedding(formatted_text)
        chunk.embedding = embedding
        print(f"  ✓ Embedding generated (dimension: {len(embedding)})")
        
        # Store in vector store
        print(f"  Storing in vector store...")
        vs.add_chunks([chunk])
        print(f"  ✓ Stored successfully")
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*60}")
print(f"REPROCESSING COMPLETE")
print(f"{'='*60}")
print(f"Total chunks in vector store: {vs.collection.count()}")
