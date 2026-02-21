"""
Integration tests demonstrating text processor usage.
"""

import tempfile
import os
from pathlib import Path

from backend.text_processor import extract_from_txt, chunk_text


def test_complete_text_processing_workflow():
    """
    Demonstrate complete workflow: extract text from file and chunk it.
    """
    # Create a sample text file with enough content to create multiple chunks
    sample_text = """
    This is a sample document for testing the RAG chatbot text processing.
    """ * 50  # Repeat to get enough text for multiple chunks
    
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.txt') as f:
        f.write(sample_text)
        temp_path = f.name
    
    try:
        # Step 1: Extract text from file
        extracted_text = extract_from_txt(temp_path)
        assert len(extracted_text) > 0
        
        # Step 2: Chunk the text
        filename = Path(temp_path).name
        chunks = chunk_text(
            text=extracted_text,
            filename=filename,
            folder_path="/test/folder"
        )
        
        # Verify chunks were created
        assert len(chunks) > 0
        
        # Verify each chunk has proper structure
        for i, chunk in enumerate(chunks):
            # Check content
            assert len(chunk.content) > 0
            assert 500 <= len(chunk.content) <= 1000 or i == len(chunks) - 1  # Last chunk can be smaller
            
            # Check metadata
            assert chunk.metadata['filename'] == filename
            assert chunk.metadata['folder_path'] == "/test/folder"
            assert chunk.metadata['file_type'] == 'text'
            assert chunk.metadata['chunk_index'] == i
            assert 'char_start' in chunk.metadata
            assert 'char_end' in chunk.metadata
            
            # Verify chunk is valid
            assert chunk.validate()
        
        # Verify overlap between consecutive chunks
        if len(chunks) > 1:
            for i in range(len(chunks) - 1):
                # Last 100 chars of current should match first 100 of next
                overlap_current = chunks[i].content[-100:]
                overlap_next = chunks[i + 1].content[:100]
                assert overlap_current == overlap_next
        
        print(f"✓ Successfully processed {filename}")
        print(f"✓ Created {len(chunks)} chunks")
        print(f"✓ Total text length: {len(extracted_text)} characters")
        
    finally:
        os.unlink(temp_path)


if __name__ == "__main__":
    test_complete_text_processing_workflow()
    print("\n✓ All integration tests passed!")
