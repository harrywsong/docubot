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
    
    Also analyzes PDF to determine if vision processing is needed.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        List of dicts with 'text', 'page_number', and 'needs_vision' keys
        
    Raises:
        Exception: If PDF extraction fails
    """
    try:
        reader = PdfReader(file_path)
        pages = []
        
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            
            # Analyze if this page needs vision processing
            needs_vision = _should_use_vision_for_page(page, text)
            
            if text.strip():  # Only include pages with text
                pages.append({
                    'text': text,
                    'page_number': page_num,
                    'needs_vision': needs_vision
                })
            else:
                # No text extracted - definitely needs vision
                pages.append({
                    'text': '',
                    'page_number': page_num,
                    'needs_vision': True
                })
        
        logger.info(f"Extracted text from {len(pages)} pages in {file_path}")
        
        # Log vision processing recommendation
        vision_pages = sum(1 for p in pages if p.get('needs_vision', False))
        if vision_pages > 0:
            logger.info(f"Vision processing recommended for {vision_pages}/{len(pages)} pages")
        
        return pages
        
    except Exception as e:
        logger.error(f"Failed to extract text from PDF {file_path}: {e}")
        raise


def _should_use_vision_for_page(page, extracted_text: str) -> bool:
    """
    Determine if a PDF page needs vision model processing.
    
    Vision processing is recommended when:
    1. Page has SIGNIFICANT images (large, likely containing important info)
    2. Text extraction quality is poor (garbled text)
    3. Text is very sparse (suggests visual-heavy content)
    4. Page contains complex tables/charts
    
    Args:
        page: pypdf page object
        extracted_text: Text extracted from the page
        
    Returns:
        True if vision processing is recommended
    """
    # Check 1: Does page have SIGNIFICANT images?
    # Only trigger vision if images are large enough to contain meaningful content
    has_significant_images = False
    try:
        if '/XObject' in page.get('/Resources', {}):
            xobjects = page['/Resources']['/XObject']
            if hasattr(xobjects, 'get_object'):
                xobjects = xobjects.get_object()
            
            for obj_name in xobjects:
                obj = xobjects[obj_name]
                if hasattr(obj, 'get'):
                    if obj.get('/Subtype') == '/Image':
                        # Check image size - only consider "significant" images
                        width = obj.get('/Width', 0)
                        height = obj.get('/Height', 0)
                        
                        # Image is significant if:
                        # - Large enough (> 200x200 pixels) - likely contains content
                        # - Takes up significant page space
                        if width > 200 and height > 200:
                            has_significant_images = True
                            break
                        
                        # Small images (logos, icons) are likely decorative - skip them
    except Exception:
        pass  # If we can't check, assume no images
    
    # Check 2: Is text VERY sparse? (less than 100 characters suggests visual-heavy content)
    # Increased threshold - only trigger if really sparse
    text_length = len(extracted_text.strip())
    is_very_sparse = text_length < 100
    
    # Check 3: Does text contain COMPLEX table patterns?
    # Only trigger for tables that are likely to have visual structure
    has_complex_table = False
    if text_length > 0:
        lines = extracted_text.split('\n')
        # Look for tables with multiple columns (3+ spaces or tabs)
        complex_table_lines = sum(1 for line in lines if line.count('   ') >= 2 or '\t\t' in line)
        # Only trigger if 40%+ of lines are complex tables (not just simple spacing)
        has_complex_table = complex_table_lines > len(lines) * 0.4
    
    # Check 4: Is text quality VERY poor? (likely scanned/image-based)
    # Increased threshold - only trigger for really poor quality
    has_very_poor_quality = False
    if text_length > 50:  # Only check if there's enough text to analyze
        import re
        alphanumeric = len(re.findall(r'[a-zA-Z0-9\s]', extracted_text))
        quality_ratio = alphanumeric / text_length if text_length > 0 else 0
        # Only trigger if less than 50% readable (very garbled)
        has_very_poor_quality = quality_ratio < 0.5
    
    # Check 5: Does the text suggest this is a visual document?
    # Look for keywords that indicate charts, diagrams, figures
    has_visual_indicators = False
    if text_length > 0:
        text_lower = extracted_text.lower()
        visual_keywords = ['figure', 'chart', 'graph', 'diagram', 'table', 'illustration']
        # If text mentions visual elements, they're probably important
        has_visual_indicators = any(keyword in text_lower for keyword in visual_keywords)
    
    # Decision: Use vision only if there's strong evidence of important visual content
    # Require either:
    # - Significant images AND (sparse text OR visual indicators)
    # - Very sparse text (< 100 chars) - likely image-only
    # - Very poor quality text - likely scanned
    # - Complex tables that need visual understanding
    
    needs_vision = (
        (has_significant_images and (is_very_sparse or has_visual_indicators)) or
        is_very_sparse or
        has_very_poor_quality or
        has_complex_table
    )
    
    return needs_vision


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
    user_id: int,
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
        user_id: User ID to tag the chunks with
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
            'user_id': user_id,  # Tag with user ID
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
