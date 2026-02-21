"""
Text document processor for RAG chatbot.

Handles text extraction from PDF and TXT files, and chunking with overlap.
"""

import logging
from pathlib import Path
from typing import List, Optional
import chardet
from pypdf import PdfReader

from backend.models import DocumentChunk


logger = logging.getLogger(__name__)


def extract_from_pdf(file_path: str) -> List[dict]:
    """
    Extract text from PDF file with page number tracking.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        List of dicts with 'text' and 'page_number' keys
        
    Raises:
        Exception: If PDF extraction fails
    """
    try:
        reader = PdfReader(file_path)
        pages = []
        
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if text.strip():  # Only include pages with text
                pages.append({
                    'text': text,
                    'page_number': page_num
                })
        
        logger.info(f"Extracted text from {len(pages)} pages in {file_path}")
        return pages
        
    except Exception as e:
        logger.error(f"Failed to extract text from PDF {file_path}: {e}")
        raise


def extract_from_txt(file_path: str) -> str:
    """
    Extract text from TXT file with encoding detection.
    
    Args:
        file_path: Path to TXT file
        
    Returns:
        Extracted text content
        
    Raises:
        Exception: If text extraction fails
    """
    try:
        # First, detect encoding
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding'] or 'utf-8'
        
        # Read with detected encoding
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            text = f.read()
        
        logger.info(f"Extracted text from {file_path} using {encoding} encoding")
        return text
        
    except Exception as e:
        logger.error(f"Failed to extract text from TXT {file_path}: {e}")
        raise


def chunk_text(
    text: str,
    filename: str,
    folder_path: str,
    page_number: Optional[int] = None,
    min_chunk_size: int = 500,
    max_chunk_size: int = 1000,
    overlap: int = 100
) -> List[DocumentChunk]:
    """
    Split text into chunks with overlap, preserving metadata.
    
    Chunks are created with 500-1000 characters and 100 character overlap
    between consecutive chunks.
    
    Args:
        text: Text content to chunk
        filename: Source filename
        folder_path: Source folder path
        page_number: Page number (for PDFs)
        min_chunk_size: Minimum chunk size in characters (default 500)
        max_chunk_size: Maximum chunk size in characters (default 1000)
        overlap: Overlap between chunks in characters (default 100)
        
    Returns:
        List of DocumentChunk objects with metadata
    """
    if not text or not text.strip():
        return []
    
    chunks = []
    text_length = len(text)
    start = 0
    chunk_index = 0
    
    while start < text_length:
        # Calculate end position for this chunk
        end = min(start + max_chunk_size, text_length)
        
        # Extract chunk
        chunk_text = text[start:end]
        
        # Create metadata
        metadata = {
            'filename': filename,
            'folder_path': folder_path,
            'file_type': 'text',
            'chunk_index': chunk_index,
            'char_start': start,
            'char_end': end
        }
        
        # Add page number if available
        if page_number is not None:
            metadata['page_number'] = page_number
        
        # Create DocumentChunk
        chunk = DocumentChunk(
            content=chunk_text,
            metadata=metadata
        )
        chunks.append(chunk)
        
        # Move to next chunk with overlap
        # If we're at the end, break
        if end >= text_length:
            break
            
        # Move start position forward, accounting for overlap
        start = end - overlap
        chunk_index += 1
    
    logger.info(f"Created {len(chunks)} chunks from {filename}")
    return chunks
