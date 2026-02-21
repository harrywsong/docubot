"""
Unit tests for text processor module.
"""

import pytest
import tempfile
import os
from pathlib import Path

from backend.text_processor import extract_from_pdf, extract_from_txt, chunk_text
from backend.models import DocumentChunk


class TestTextExtraction:
    """Test text extraction from PDF and TXT files."""
    
    def test_extract_from_txt_utf8(self):
        """Test extracting text from UTF-8 encoded TXT file."""
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.txt') as f:
            f.write("Hello, world!\nThis is a test file.")
            temp_path = f.name
        
        try:
            text = extract_from_txt(temp_path)
            assert "Hello, world!" in text
            assert "This is a test file." in text
        finally:
            os.unlink(temp_path)
    
    def test_extract_from_txt_latin1(self):
        """Test extracting text from Latin-1 encoded TXT file."""
        with tempfile.NamedTemporaryFile(mode='w', encoding='latin-1', delete=False, suffix='.txt') as f:
            f.write("Café résumé")
            temp_path = f.name
        
        try:
            text = extract_from_txt(temp_path)
            # Should handle encoding gracefully
            assert len(text) > 0
        finally:
            os.unlink(temp_path)
    
    def test_extract_from_txt_empty(self):
        """Test extracting from empty TXT file."""
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.txt') as f:
            temp_path = f.name
        
        try:
            text = extract_from_txt(temp_path)
            assert text == ""
        finally:
            os.unlink(temp_path)


class TestTextChunking:
    """Test text chunking with overlap."""
    
    def test_chunk_text_basic(self):
        """Test basic text chunking."""
        text = "a" * 1500  # 1500 characters
        chunks = chunk_text(text, "test.txt", "/test/folder")
        
        # Should create at least 2 chunks
        assert len(chunks) >= 2
        
        # All chunks should be DocumentChunk instances
        assert all(isinstance(chunk, DocumentChunk) for chunk in chunks)
        
        # Check metadata
        for chunk in chunks:
            assert chunk.metadata['filename'] == "test.txt"
            assert chunk.metadata['folder_path'] == "/test/folder"
            assert chunk.metadata['file_type'] == 'text'
            assert 'chunk_index' in chunk.metadata
            assert 'char_start' in chunk.metadata
            assert 'char_end' in chunk.metadata
    
    def test_chunk_text_size_constraints(self):
        """Test that chunks meet size constraints (500-1000 chars)."""
        text = "a" * 5000  # 5000 characters
        chunks = chunk_text(text, "test.txt", "/test/folder")
        
        # Check chunk sizes (except possibly the last one)
        for i, chunk in enumerate(chunks[:-1]):
            chunk_size = len(chunk.content)
            assert 500 <= chunk_size <= 1000, f"Chunk {i} size {chunk_size} not in range [500, 1000]"
        
        # Last chunk might be smaller
        last_chunk_size = len(chunks[-1].content)
        assert last_chunk_size <= 1000
    
    def test_chunk_text_overlap(self):
        """Test that consecutive chunks have 100 character overlap."""
        text = "a" * 2500  # 2500 characters
        chunks = chunk_text(text, "test.txt", "/test/folder")
        
        # Check overlap between consecutive chunks
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]
            
            # Get the last 100 chars of current chunk
            current_end = current_chunk.content[-100:]
            # Get the first 100 chars of next chunk
            next_start = next_chunk.content[:100]
            
            # They should be identical (100 char overlap)
            assert current_end == next_start, f"Overlap mismatch between chunks {i} and {i+1}"
    
    def test_chunk_text_with_page_number(self):
        """Test chunking with page number metadata."""
        text = "a" * 1500
        chunks = chunk_text(text, "test.pdf", "/test/folder", page_number=5)
        
        # All chunks should have page_number in metadata
        for chunk in chunks:
            assert chunk.metadata['page_number'] == 5
    
    def test_chunk_text_empty(self):
        """Test chunking empty text."""
        chunks = chunk_text("", "test.txt", "/test/folder")
        assert len(chunks) == 0
        
        chunks = chunk_text("   ", "test.txt", "/test/folder")
        assert len(chunks) == 0
    
    def test_chunk_text_short(self):
        """Test chunking text shorter than min chunk size."""
        text = "Short text"  # Less than 500 chars
        chunks = chunk_text(text, "test.txt", "/test/folder")
        
        # Should create 1 chunk
        assert len(chunks) == 1
        assert chunks[0].content == text
    
    def test_chunk_text_metadata_positions(self):
        """Test that char_start and char_end are correct."""
        text = "a" * 2500
        chunks = chunk_text(text, "test.txt", "/test/folder")
        
        for chunk in chunks:
            start = chunk.metadata['char_start']
            end = chunk.metadata['char_end']
            
            # Verify the chunk content matches the positions
            assert chunk.content == text[start:end]
    
    def test_chunk_text_coverage(self):
        """Test that all text is covered by chunks."""
        text = "a" * 3000
        chunks = chunk_text(text, "test.txt", "/test/folder")
        
        # First chunk should start at 0
        assert chunks[0].metadata['char_start'] == 0
        
        # Last chunk should end at text length
        assert chunks[-1].metadata['char_end'] == len(text)
        
        # Reconstruct text from chunks (accounting for overlap)
        reconstructed = chunks[0].content
        for i in range(1, len(chunks)):
            # Skip the overlap (first 100 chars of each subsequent chunk)
            reconstructed += chunks[i].content[100:]
        
        assert reconstructed == text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
