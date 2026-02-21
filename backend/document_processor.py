"""
Document processor orchestrator for RAG chatbot.

Coordinates folder scanning, file routing, embedding generation, and vector storage.
Implements progress tracking and error handling for document processing.
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass

from backend.folder_manager import FolderManager
from backend.processing_state import ProcessingStateManager
from backend.text_processor import extract_from_pdf, extract_from_txt, chunk_text
from backend.image_processor import ImageProcessor
from backend.embedding_engine import EmbeddingEngine
from backend.vector_store import VectorStore
from backend.database import DatabaseManager
from backend.models import DocumentChunk

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of document processing operation."""
    processed: int
    skipped: int
    failed: int
    failed_files: List[Tuple[str, str]]  # List of (file_path, error_message)


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
        Process a text file (PDF or TXT).
        
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
                
                for page_data in pages:
                    page_chunks = chunk_text(
                        text=page_data['text'],
                        filename=path.name,
                        folder_path=str(path.parent),
                        page_number=page_data['page_number']
                    )
                    chunks.extend(page_chunks)
            
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
            
            # Generate embeddings
            texts = [chunk.content for chunk in chunks]
            embeddings = self.embedding_engine.generate_embeddings_batch(texts)
            
            # Attach embeddings to chunks
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding
            
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
    
    def _process_image_file(self, file_path: str, folder_id: int) -> str:
        """
        Process an image file.
        
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
            
            logger.info(f"Processing image file ({state}): {file_path}")
            
            # Process image with vision model
            extraction = self.image_processor.process_image(file_path)
            
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
            
            # Add extracted metadata
            if extraction.merchant:
                metadata['merchant'] = extraction.merchant
            if extraction.date:
                metadata['date'] = extraction.date
            if extraction.total_amount is not None:
                metadata['total_amount'] = extraction.total_amount
            if extraction.currency:
                metadata['currency'] = extraction.currency
            
            chunk = DocumentChunk(
                content=formatted_text,
                metadata=metadata
            )
            
            # Generate embedding
            embedding = self.embedding_engine.generate_embedding(formatted_text)
            chunk.embedding = embedding
            
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
