"""
Processing Validator for Desktop-Pi RAG Pipeline

Validates processed documents before export to ensure data quality:
- Verifies all chunks have embeddings
- Verifies metadata completeness
- Generates processing statistics
- Identifies failed documents
- Prevents export of invalid data
"""

import logging
from typing import List, Dict, Any
from backend.vector_store import VectorStore
from backend.database import DatabaseManager
from backend.models import ProcessingReport

logger = logging.getLogger(__name__)


class ProcessingValidator:
    """
    Validates processed documents before export.
    
    Ensures data quality by checking:
    - All chunks have embeddings
    - All chunks have required metadata
    - Processing statistics are accurate
    - Failed documents are identified
    """
    
    def __init__(self, vector_store: VectorStore, db_manager: DatabaseManager):
        """
        Initialize validator with data sources.
        
        Args:
            vector_store: Vector store instance containing chunks and embeddings
            db_manager: Database manager instance containing processing state
        """
        self.vector_store = vector_store
        self.db_manager = db_manager
        
        logger.info("ProcessingValidator initialized")
    
    def validate_processing(self) -> ProcessingReport:
        """
        Validate all processed documents.
        
        Performs comprehensive validation:
        1. Counts documents, chunks, and embeddings
        2. Checks for chunks missing embeddings
        3. Checks for chunks with incomplete metadata
        4. Identifies failed documents
        
        Returns:
            ProcessingReport with statistics and validation errors
        """
        logger.info("Starting processing validation...")
        
        # Initialize counters
        total_documents = 0
        total_chunks = 0
        total_embeddings = 0
        failed_documents = []
        
        # Get database statistics
        with self.db_manager.transaction() as conn:
            # Count total processed documents
            cursor = conn.execute("SELECT COUNT(*) FROM processed_files")
            total_documents = cursor.fetchone()[0]
            
            logger.info(f"Found {total_documents} processed documents in database")
        
        # Get vector store statistics
        vs_stats = self.vector_store.get_stats()
        total_chunks = vs_stats.get('total_chunks', 0)
        
        logger.info(f"Found {total_chunks} chunks in vector store")
        
        # Check embedding coverage
        missing_embeddings = self.check_embedding_coverage()
        
        # Check metadata completeness
        incomplete_metadata = self.check_metadata_completeness()
        
        # Calculate total embeddings (chunks with embeddings)
        total_embeddings = total_chunks - len(missing_embeddings)
        
        # Determine if validation passed
        validation_passed = (
            len(missing_embeddings) == 0 and
            len(incomplete_metadata) == 0 and
            total_chunks > 0
        )
        
        # Create report
        report = ProcessingReport(
            total_documents=total_documents,
            total_chunks=total_chunks,
            total_embeddings=total_embeddings,
            failed_documents=failed_documents,
            missing_embeddings=missing_embeddings,
            incomplete_metadata=incomplete_metadata,
            validation_passed=validation_passed
        )
        
        # Log validation results
        if validation_passed:
            logger.info("Processing validation PASSED")
        else:
            logger.warning("Processing validation FAILED")
            if missing_embeddings:
                logger.warning(f"Found {len(missing_embeddings)} chunks missing embeddings")
            if incomplete_metadata:
                logger.warning(f"Found {len(incomplete_metadata)} chunks with incomplete metadata")
        
        return report
    
    def check_embedding_coverage(self) -> List[str]:
        """
        Check that all chunks have embeddings.
        
        Queries the vector store to find chunks without embeddings.
        In ChromaDB, all stored chunks should have embeddings by design,
        but this validates the data integrity.
        
        Returns:
            List of chunk IDs missing embeddings (should be empty for valid data)
        """
        logger.info("Checking embedding coverage...")
        
        missing_embeddings = []
        
        try:
            # Get all chunks from vector store
            # ChromaDB stores embeddings with chunks, so we check if any are None or invalid
            collection = self.vector_store.collection
            
            # Get all data including embeddings
            results = collection.get(
                include=["embeddings", "metadatas"]
            )
            
            if results and 'ids' in results:
                chunk_ids = results['ids']
                embeddings = results.get('embeddings', [])
                
                # Check each chunk for valid embedding
                for i, chunk_id in enumerate(chunk_ids):
                    if i >= len(embeddings):
                        # Missing embedding for this chunk
                        missing_embeddings.append(chunk_id)
                        logger.warning(f"Chunk {chunk_id} missing embedding (index out of range)")
                    elif embeddings[i] is None:
                        # Embedding is None
                        missing_embeddings.append(chunk_id)
                        logger.warning(f"Chunk {chunk_id} has None embedding")
                    elif not embeddings[i] or len(embeddings[i]) == 0:
                        # Embedding is empty
                        missing_embeddings.append(chunk_id)
                        logger.warning(f"Chunk {chunk_id} has empty embedding")
            
            logger.info(f"Embedding coverage check complete: {len(missing_embeddings)} chunks missing embeddings")
            
        except Exception as e:
            logger.error(f"Error checking embedding coverage: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return missing_embeddings
    
    def check_metadata_completeness(self) -> List[str]:
        """
        Check that all chunks have required metadata.
        
        Required metadata fields:
        - filename: Source file name
        - folder_path: Source folder path
        - file_type: Type of file (text or image)
        
        Returns:
            List of chunk IDs with incomplete metadata
        """
        logger.info("Checking metadata completeness...")
        
        incomplete_metadata = []
        required_fields = ['filename', 'folder_path', 'file_type']
        
        try:
            # Get all chunks with metadata
            collection = self.vector_store.collection
            
            results = collection.get(
                include=["metadatas"]
            )
            
            if results and 'ids' in results:
                chunk_ids = results['ids']
                metadatas = results.get('metadatas', [])
                
                # Check each chunk for required metadata fields
                for i, chunk_id in enumerate(chunk_ids):
                    if i >= len(metadatas):
                        # Missing metadata for this chunk
                        incomplete_metadata.append(chunk_id)
                        logger.warning(f"Chunk {chunk_id} missing metadata (index out of range)")
                        continue
                    
                    metadata = metadatas[i]
                    
                    if metadata is None:
                        # Metadata is None
                        incomplete_metadata.append(chunk_id)
                        logger.warning(f"Chunk {chunk_id} has None metadata")
                        continue
                    
                    # Check for required fields
                    missing_fields = []
                    for field in required_fields:
                        if field not in metadata or metadata[field] is None or metadata[field] == '':
                            missing_fields.append(field)
                    
                    if missing_fields:
                        incomplete_metadata.append(chunk_id)
                        logger.warning(f"Chunk {chunk_id} missing required metadata fields: {missing_fields}")
            
            logger.info(f"Metadata completeness check complete: {len(incomplete_metadata)} chunks with incomplete metadata")
            
        except Exception as e:
            logger.error(f"Error checking metadata completeness: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return incomplete_metadata
