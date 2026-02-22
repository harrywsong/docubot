"""
Document processor orchestrator for RAG chatbot.

Coordinates folder scanning, file routing, embedding generation, and vector storage.
Implements progress tracking and error handling for document processing.
"""

import logging
import os
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from PIL import Image

from backend.folder_manager import FolderManager
from backend.processing_state import ProcessingStateManager
from backend.text_processor import extract_from_pdf, extract_from_txt, chunk_text
from backend.image_processor import ImageProcessor
from backend.embedding_engine import EmbeddingEngine
from backend.vector_store import VectorStore
from backend.database import DatabaseManager
from backend.models import DocumentChunk

logger = logging.getLogger(__name__)

# Poppler path configuration for Windows
POPPLER_PATH = r"C:\poppler\poppler-24.08.0\Library\bin"
if os.path.exists(POPPLER_PATH):
    logger.info(f"Using poppler from: {POPPLER_PATH}")
else:
    POPPLER_PATH = None
    logger.warning("Poppler not found at expected location, pdf2image will use system PATH")

# Blacklist for images that crash the vision model
# Store file hashes to identify problematic images
VISION_MODEL_BLACKLIST: Set[str] = set()


@dataclass
class ProcessingResult:
    """Result of document processing operation."""
    processed: int
    skipped: int
    failed: int
    failed_files: List[Tuple[str, str]]  # List of (file_path, error_message)


def _get_file_hash(file_path: str) -> str:
    """
    Get MD5 hash of a file for blacklist identification.
    
    Args:
        file_path: Path to file
        
    Returns:
        MD5 hash string
    """
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return ""


def _is_blacklisted(file_path: str) -> bool:
    """
    Check if a file is blacklisted from vision processing.
    
    Args:
        file_path: Path to file
        
    Returns:
        True if file is blacklisted
    """
    file_hash = _get_file_hash(file_path)
    return file_hash in VISION_MODEL_BLACKLIST if file_hash else False


def _add_to_blacklist(file_path: str):
    """
    Add a file to the vision model blacklist.
    
    Args:
        file_path: Path to file that crashes vision model
    """
    file_hash = _get_file_hash(file_path)
    if file_hash:
        VISION_MODEL_BLACKLIST.add(file_hash)
        logger.warning(f"Added {Path(file_path).name} to vision model blacklist (hash: {file_hash[:8]}...)")


class DocumentProcessor:
    """Orchestrates document processing pipeline."""
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        folder_manager: FolderManager,
        state_manager: ProcessingStateManager,
        embedding_engine: EmbeddingEngine,
        vector_store: VectorStore,
        image_processor: ImageProcessor
    ):
        """
        Initialize document processor.
        
        Args:
            db_manager: Database manager instance
            folder_manager: Folder manager instance
            state_manager: Processing state manager instance
            embedding_engine: Embedding engine instance
            vector_store: Vector store instance
            image_processor: Image processor instance
        """
        self.db = db_manager
        self.folder_manager = folder_manager
        self.state_manager = state_manager
        self.embedding_engine = embedding_engine
        self.vector_store = vector_store
        self.image_processor = image_processor
    
    def process_folders(self) -> ProcessingResult:
        """
        Process all watched folders.
        
        Scans all watched folders, routes files to appropriate processors,
        generates embeddings, stores in vector store, and updates processing state.
        
        Returns:
            ProcessingResult with counts of processed, skipped, and failed files
        """
        logger.info("Starting document processing")
        
        # Initialize counters
        processed_count = 0
        skipped_count = 0
        failed_count = 0
        failed_files = []
        
        # Get all watched folders
        folders = self.folder_manager.list_folders()
        
        if not folders:
            logger.info("No watched folders to process")
            return ProcessingResult(
                processed=0,
                skipped=0,
                failed=0,
                failed_files=[]
            )
        
        logger.info(f"Processing {len(folders)} watched folders")
        
        # Process each folder
        for folder in folders:
            logger.info(f"Scanning folder: {folder.path}")
            
            # Scan folder for files
            text_files, image_files = self.folder_manager.scan_folder(folder.path)
            all_files = text_files + image_files
            
            logger.info(f"Found {len(text_files)} text files and {len(image_files)} image files")
            
            # Process each file
            for file_path in text_files:
                result = self._process_text_file(file_path, folder.id)
                if result == "processed":
                    processed_count += 1
                elif result == "skipped":
                    skipped_count += 1
                elif isinstance(result, str) and result.startswith("failed:"):
                    failed_count += 1
                    error_msg = result[7:]  # Remove "failed:" prefix
                    failed_files.append((file_path, error_msg))
            
            for file_path in image_files:
                result = self._process_image_file(file_path, folder.id)
                if result == "processed":
                    processed_count += 1
                elif result == "skipped":
                    skipped_count += 1
                elif isinstance(result, str) and result.startswith("failed:"):
                    failed_count += 1
                    error_msg = result[7:]  # Remove "failed:" prefix
                    failed_files.append((file_path, error_msg))
        
        logger.info(
            f"Processing complete: {processed_count} processed, "
            f"{skipped_count} skipped, {failed_count} failed"
        )
        
        return ProcessingResult(
            processed=processed_count,
            skipped=skipped_count,
            failed=failed_count,
            failed_files=failed_files
        )
    
    def _process_text_file(self, file_path: str, folder_id: int) -> str:
        """
        Process a text file (PDF or TXT) with hybrid approach.
        
        For PDFs: Extracts text AND processes pages with vision model to capture
        information from images/tables that text extraction might miss.
        
        Args:
            file_path: Path to file
            folder_id: ID of folder containing the file
            
        Returns:
            "processed", "skipped", or "failed:<error_message>"
        """
        try:
            # Check processing state
            state = self.state_manager.check_file_state(file_path)
            
            if state == "unchanged":
                logger.debug(f"Skipping unchanged file: {file_path}")
                return "skipped"
            
            logger.info(f"Processing text file ({state}): {file_path}")
            
            # Extract text based on file type
            path = Path(file_path)
            ext = path.suffix.lower()
            
            chunks = []
            
            if ext == '.pdf':
                # Extract from PDF with page tracking
                pages = extract_from_pdf(file_path)
                
                # Check if PDF has extractable text
                if not pages or len(pages) == 0:
                    logger.warning(f"PDF has no extractable text, treating as image-only: {file_path}")
                    # Fall back to image processing for image-only PDFs
                    return self._process_pdf_as_image(file_path, folder_id)
                
                # Process text content
                for page_data in pages:
                    if page_data['text'].strip():  # Only create chunks for pages with text
                        page_chunks = chunk_text(
                            text=page_data['text'],
                            filename=path.name,
                            folder_path=str(path.parent),
                            page_number=page_data['page_number']
                        )
                        chunks.extend(page_chunks)
                
                logger.info(f"Extracted {len(chunks)} text chunks from PDF")
                
                # SMART HYBRID PROCESSING: Only use vision model on pages that need it
                # Check if any pages need vision processing
                pages_needing_vision = [p for p in pages if p.get('needs_vision', False)]
                
                if pages_needing_vision:
                    logger.info(f"Applying vision model to {len(pages_needing_vision)}/{len(pages)} pages that need it")
                    vision_chunks = self._process_pdf_pages_with_vision(
                        file_path, 
                        path, 
                        page_numbers=[p['page_number'] for p in pages_needing_vision]
                    )
                    
                    if vision_chunks:
                        logger.info(f"Extracted {len(vision_chunks)} vision chunks from PDF")
                        chunks.extend(vision_chunks)
                    else:
                        logger.warning(f"Vision processing yielded no additional chunks")
                else:
                    logger.info(f"Text extraction sufficient - skipping vision processing")
            
            elif ext == '.txt':
                # Extract from TXT
                text = extract_from_txt(file_path)
                chunks = chunk_text(
                    text=text,
                    filename=path.name,
                    folder_path=str(path.parent)
                )
            
            else:
                logger.warning(f"Unsupported text file type: {ext}")
                return f"failed:Unsupported file type: {ext}"
            
            if not chunks:
                logger.warning(f"No chunks extracted from {file_path}")
                return "skipped"
            
            # Generate embeddings with retry logic
            try:
                texts = [chunk.content for chunk in chunks]
                embeddings = self.embedding_engine.generate_embeddings_batch(texts)
                
                # Attach embeddings to chunks
                for chunk, embedding in zip(chunks, embeddings):
                    chunk.embedding = embedding
                    
            except RuntimeError as e:
                # Embedding generation failed after retries
                error_msg = f"Embedding generation failed after retries: {e}"
                logger.error(f"Failed to process {file_path}: {error_msg}")
                return f"failed:{error_msg}"
            
            # Store in vector store
            self.vector_store.add_chunks(chunks)
            
            # Update processing state
            self.state_manager.update_file_state(file_path, folder_id, "text")
            
            logger.info(f"Successfully processed {file_path}: {len(chunks)} chunks")
            return "processed"
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to process text file {file_path}: {error_msg}")
            return f"failed:{error_msg}"
    
    def _process_pdf_pages_with_vision(self, file_path: str, path: Path, page_numbers: List[int]) -> List[DocumentChunk]:
        """
        Process specific PDF pages with vision model to extract visual information.
        
        This is used for smart hybrid processing: only processes pages that need vision.
        Captures information from images, tables, charts, and visual elements.
        
        Args:
            file_path: Path to PDF file
            path: Path object for the file
            page_numbers: List of page numbers to process (1-indexed)
            
        Returns:
            List of DocumentChunk objects with vision-extracted content
        """
        try:
            from pdf2image import convert_from_path
            import tempfile
            import os
            
            # Convert only the specified pages to images
            try:
                if POPPLER_PATH:
                    # Convert all pages first (pdf2image doesn't support selective page conversion easily)
                    all_images = convert_from_path(file_path, dpi=150, fmt='png', poppler_path=POPPLER_PATH)
                else:
                    all_images = convert_from_path(file_path, dpi=150, fmt='png')
                
                # Filter to only the pages we need
                images = [all_images[i-1] for i in page_numbers if i <= len(all_images)]
                
            except Exception as e:
                logger.error(f"Failed to convert PDF pages to images for vision processing: {e}")
                return []
            
            if not images:
                return []
            
            logger.info(f"Processing {len(images)} selected pages with vision model")
            
            # Process each page with vision model
            vision_chunks = []
            
            for idx, page_num in enumerate(page_numbers[:len(images)]):
                image = images[idx]
                
                try:
                    # Convert image to RGB mode (removes alpha channel and ensures consistent format)
                    # This prevents GGML assertion errors in the vision model
                    if image.mode != 'RGB':
                        logger.debug(f"Converting page {page_num} from {image.mode} to RGB")
                        image = image.convert('RGB')
                    
                    # Resize image if too large (vision models have size limits)
                    # Keep aspect ratio but limit max dimension to 2048px
                    max_dimension = 2048
                    width, height = image.size
                    if width > max_dimension or height > max_dimension:
                        if width > height:
                            new_width = max_dimension
                            new_height = int(height * (max_dimension / width))
                        else:
                            new_height = max_dimension
                            new_width = int(width * (max_dimension / height))
                        logger.debug(f"Resizing page {page_num} from {width}x{height} to {new_width}x{new_height}")
                        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # Save image to temporary file as JPEG (more reliable for vision models)
                    # JPEG doesn't support alpha channels and has simpler format
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                        tmp_path = tmp_file.name
                        image.save(tmp_path, 'JPEG', quality=95)
                    
                    # Process with vision model (with error handling)
                    try:
                        extraction = self.image_processor.process_image(tmp_path)
                    except Exception as vision_error:
                        logger.warning(f"Vision model failed on page {page_num}: {vision_error}")
                        os.unlink(tmp_path)
                        continue  # Skip this page but continue with others
                    
                    # Clean up temp file
                    os.unlink(tmp_path)
                    
                    # Format as structured text
                    formatted_text = extraction.format_as_text()
                    
                    if not formatted_text.strip():
                        continue
                    
                    # Create document chunk with metadata
                    metadata = {
                        'filename': path.name,
                        'folder_path': str(path.parent),
                        'file_type': 'pdf_vision',  # Mark as vision-extracted
                        'chunk_index': page_num - 1,
                        'page_number': page_num
                    }
                    
                    # Add all flexible metadata fields dynamically (model decides what fields to extract)
                    if extraction.flexible_metadata:
                        for key, value in extraction.flexible_metadata.items():
                            metadata[key] = value
                    
                    chunk = DocumentChunk(
                        content=formatted_text,
                        metadata=metadata
                    )
                    
                    vision_chunks.append(chunk)
                    
                except Exception as page_error:
                    logger.warning(f"Failed to process page {page_num} with vision: {page_error}")
                    continue  # Skip this page but continue with others
            
            return vision_chunks
            
        except Exception as e:
            logger.error(f"Failed to process PDF pages with vision: {e}")
            return []
    
    def _process_image_file(self, file_path: str, folder_id: int) -> str:
        """
        Process an image file with vision model.
        
        Includes error handling for vision model crashes and blacklist management.
        
        Args:
            file_path: Path to file
            folder_id: ID of folder containing the file
            
        Returns:
            "processed", "skipped", or "failed:<error_message>"
        """
        try:
            # Check processing state
            state = self.state_manager.check_file_state(file_path)
            
            if state == "unchanged":
                logger.debug(f"Skipping unchanged file: {file_path}")
                return "skipped"
            
            # Check if file is blacklisted
            if _is_blacklisted(file_path):
                logger.warning(f"Skipping blacklisted file: {file_path}")
                return "skipped"
            
            logger.info(f"Processing image file ({state}): {file_path}")
            
            # Process image with vision model (with error handling)
            try:
                extraction = self.image_processor.process_image(file_path)
            except Exception as vision_error:
                error_msg = str(vision_error)
                logger.error(f"Vision model failed on {file_path}: {error_msg}")
                
                # Check if it's a model crash (GGML assertion error)
                if "GGML_ASSERT" in error_msg or "status 500" in error_msg:
                    # Add to blacklist to skip in future
                    _add_to_blacklist(file_path)
                    logger.warning(f"Image may have orientation issues or be corrupted. Try rotating/fixing the image manually.")
                    return f"failed:Vision model crash (blacklisted, may need manual rotation): {error_msg}"
                else:
                    return f"failed:{error_msg}"
            
            # Format as structured text
            formatted_text = extraction.format_as_text()
            
            if not formatted_text.strip():
                logger.warning(f"No content extracted from {file_path}")
                return "skipped"
            
            # Create document chunk with metadata
            path = Path(file_path)
            metadata = {
                'filename': path.name,
                'folder_path': str(path.parent),
                'file_type': 'image',
                'chunk_index': 0
            }
            
            # Add all flexible metadata fields dynamically
            if extraction.flexible_metadata:
                for key, value in extraction.flexible_metadata.items():
                    metadata[key] = value
                logger.info(f"Added {len(extraction.flexible_metadata)} flexible metadata fields to chunk")
            else:
                logger.warning(f"No flexible metadata extracted from {file_path}")
            
            chunk = DocumentChunk(
                content=formatted_text,
                metadata=metadata
            )
            
            # Generate embedding with retry logic
            try:
                embedding = self.embedding_engine.generate_embedding(formatted_text)
                chunk.embedding = embedding
                
            except RuntimeError as e:
                # Embedding generation failed after retries
                error_msg = f"Embedding generation failed after retries: {e}"
                logger.error(f"Failed to process {file_path}: {error_msg}")
                return f"failed:{error_msg}"
            
            # Store in vector store
            self.vector_store.add_chunks([chunk])
            
            # Update processing state
            self.state_manager.update_file_state(file_path, folder_id, "image")
            
            logger.info(f"Successfully processed {file_path}")
            return "processed"
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to process image file {file_path}: {error_msg}")
            return f"failed:{error_msg}"

    def _process_pdf_as_image(self, file_path: str, folder_id: int) -> str:
        """
        Process a PDF by converting pages to images and using vision model.
        
        Uses pdf2image library for reliable PDF to image conversion.
        Processes all pages and combines results.
        
        Args:
            file_path: Path to PDF file
            folder_id: ID of folder containing the file
            
        Returns:
            "processed", "skipped", or "failed:<error_message>"
        """
        try:
            logger.info(f"Processing PDF as image: {file_path}")
            
            from pdf2image import convert_from_path
            import tempfile
            import os
            
            # Convert PDF pages to images
            try:
                if POPPLER_PATH:
                    images = convert_from_path(file_path, dpi=150, fmt='png', poppler_path=POPPLER_PATH)
                else:
                    images = convert_from_path(file_path, dpi=150, fmt='png')
            except Exception as e:
                logger.error(f"Failed to convert PDF to images: {e}")
                return f"failed:PDF conversion error: {str(e)}"
            
            if not images:
                logger.warning(f"No images extracted from PDF: {file_path}")
                return "skipped"
            
            logger.info(f"Converted {len(images)} pages from PDF")
            
            # Process each page with vision model
            all_chunks = []
            path = Path(file_path)
            
            for page_num, image in enumerate(images, start=1):
                try:
                    # Convert image to RGB mode (removes alpha channel and ensures consistent format)
                    # This prevents GGML assertion errors in the vision model
                    if image.mode != 'RGB':
                        logger.debug(f"Converting page {page_num} from {image.mode} to RGB")
                        image = image.convert('RGB')
                    
                    # Resize image if too large (vision models have size limits)
                    # Keep aspect ratio but limit max dimension to 2048px
                    max_dimension = 2048
                    width, height = image.size
                    if width > max_dimension or height > max_dimension:
                        if width > height:
                            new_width = max_dimension
                            new_height = int(height * (max_dimension / width))
                        else:
                            new_height = max_dimension
                            new_width = int(width * (max_dimension / height))
                        logger.debug(f"Resizing page {page_num} from {width}x{height} to {new_width}x{new_height}")
                        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # Save image to temporary file as JPEG (more reliable for vision models)
                    # JPEG doesn't support alpha channels and has simpler format
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                        tmp_path = tmp_file.name
                        image.save(tmp_path, 'JPEG', quality=95)
                    
                    # Process with vision model (with error handling)
                    try:
                        extraction = self.image_processor.process_image(tmp_path)
                    except Exception as vision_error:
                        logger.error(f"Vision model failed on page {page_num}: {vision_error}")
                        # Clean up temp file
                        os.unlink(tmp_path)
                        continue  # Skip this page but continue with others
                    
                    # Clean up temp file
                    os.unlink(tmp_path)
                    
                    # Format as structured text
                    formatted_text = extraction.format_as_text()
                    
                    if not formatted_text.strip():
                        logger.warning(f"No content extracted from page {page_num}")
                        continue
                    
                    # Create document chunk with metadata
                    metadata = {
                        'filename': path.name,
                        'folder_path': str(path.parent),
                        'file_type': 'pdf_image',
                        'chunk_index': page_num - 1,
                        'page_number': page_num
                    }
                    
                    # Add all flexible metadata fields dynamically
                    if extraction.flexible_metadata:
                        for key, value in extraction.flexible_metadata.items():
                            metadata[key] = value
                    
                    chunk = DocumentChunk(
                        content=formatted_text,
                        metadata=metadata
                    )
                    
                    # Generate embedding with retry logic
                    try:
                        embedding = self.embedding_engine.generate_embedding(formatted_text)
                        chunk.embedding = embedding
                        
                    except RuntimeError as e:
                        # Embedding generation failed after retries
                        logger.error(f"Failed to generate embedding for page {page_num}: {e}")
                        continue  # Skip this page but continue with others
                    
                    all_chunks.append(chunk)
                    
                except Exception as page_error:
                    logger.error(f"Failed to process page {page_num}: {page_error}")
                    continue  # Skip this page but continue with others
            
            if not all_chunks:
                logger.warning(f"No chunks extracted from PDF: {file_path}")
                return "skipped"
            
            # Store all chunks in vector store
            self.vector_store.add_chunks(all_chunks)
            
            # Update processing state
            self.state_manager.update_file_state(file_path, folder_id, "pdf_image")
            
            logger.info(f"Successfully processed PDF as image: {file_path} ({len(all_chunks)} pages)")
            return "processed"
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to process PDF as image {file_path}: {error_msg}")
            return f"failed:{error_msg}"
