"""
Incremental Merger for Desktop-Pi RAG Pipeline

Handles merging of incremental export packages with existing data on Pi.
Supports:
- Incremental package validation
- Chunk merging with conflict resolution
- Database state updates
- Merge integrity verification
"""

import os
import json
import shutil
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from backend.vector_store import VectorStore
from backend.database import DatabaseManager
from backend.models import MergeResult, DocumentChunk

logger = logging.getLogger(__name__)


class IncrementalMerger:
    """
    Manages merging of incremental updates with existing data.
    
    Features:
    - Validates incremental package compatibility
    - Merges new chunks into vector store
    - Updates database with new processing state
    - Handles conflicts with "newer wins" strategy
    - Verifies merge integrity
    """
    
    def __init__(self, vector_store: VectorStore, db_manager: DatabaseManager):
        """
        Initialize incremental merger.
        
        Args:
            vector_store: Vector store instance (must not be in read-only mode for merging)
            db_manager: Database manager instance
        """
        self.vector_store = vector_store
        self.db_manager = db_manager
        
        logger.info("IncrementalMerger initialized")
    
    def merge_incremental_package(self, package_path: str) -> MergeResult:
        """
        Merge incremental export package with existing data.
        
        Args:
            package_path: Path to incremental export package directory
            
        Returns:
            MergeResult with merge statistics
            
        Raises:
            MergeError: If merge fails or data is incompatible
        """
        logger.info(f"Starting incremental merge from package: {package_path}")
        
        start_time = time.time()
        errors = []
        merged_chunks = 0
        updated_chunks = 0
        deleted_chunks = 0
        
        try:
            package = Path(package_path)
            
            # Step 1: Validate package exists
            if not package.exists():
                error_msg = f"Package directory not found: {package_path}"
                logger.error(error_msg)
                errors.append(error_msg)
                return MergeResult(
                    success=False,
                    merged_chunks=0,
                    updated_chunks=0,
                    deleted_chunks=0,
                    errors=errors,
                    merge_time_seconds=time.time() - start_time
                )
            
            # Step 2: Load and validate manifest
            manifest_path = package / "manifest.json"
            if not manifest_path.exists():
                error_msg = "Manifest file not found in package"
                logger.error(error_msg)
                errors.append(error_msg)
                return MergeResult(
                    success=False,
                    merged_chunks=0,
                    updated_chunks=0,
                    deleted_chunks=0,
                    errors=errors,
                    merge_time_seconds=time.time() - start_time
                )
            
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            logger.info("Loaded manifest from package")
            
            # Step 3: Validate compatibility
            if not self.validate_compatibility(manifest):
                error_msg = "Incremental package is not compatible with existing data"
                logger.error(error_msg)
                errors.append(error_msg)
                return MergeResult(
                    success=False,
                    merged_chunks=0,
                    updated_chunks=0,
                    deleted_chunks=0,
                    errors=errors,
                    merge_time_seconds=time.time() - start_time
                )
            
            logger.info("Package compatibility validated")
            
            # Step 4: Check if this is actually an incremental package
            if not manifest.get("incremental", {}).get("is_incremental", False):
                error_msg = "Package is not marked as incremental"
                logger.error(error_msg)
                errors.append(error_msg)
                return MergeResult(
                    success=False,
                    merged_chunks=0,
                    updated_chunks=0,
                    deleted_chunks=0,
                    errors=errors,
                    merge_time_seconds=time.time() - start_time
                )
            
            # Step 5: Load chunks from incremental ChromaDB
            chromadb_path = package / "chromadb"
            if not chromadb_path.exists():
                error_msg = "ChromaDB directory not found in package"
                logger.error(error_msg)
                errors.append(error_msg)
                return MergeResult(
                    success=False,
                    merged_chunks=0,
                    updated_chunks=0,
                    deleted_chunks=0,
                    errors=errors,
                    merge_time_seconds=time.time() - start_time
                )
            
            logger.info("Loading chunks from incremental package...")
            new_chunks = self._load_chunks_from_chromadb(chromadb_path)
            logger.info(f"Loaded {len(new_chunks)} chunks from incremental package")
            
            if not new_chunks:
                logger.warning("No chunks found in incremental package")
                return MergeResult(
                    success=True,
                    merged_chunks=0,
                    updated_chunks=0,
                    deleted_chunks=0,
                    errors=errors,
                    merge_time_seconds=time.time() - start_time
                )
            
            # Step 6: Handle conflicts with "newer wins" strategy
            # For files that exist in both old and new data, delete old chunks first
            logger.info("Handling conflicts with 'newer wins' strategy...")
            files_in_package = self._get_files_from_chunks(new_chunks)
            logger.info(f"Found {len(files_in_package)} unique files in incremental package")
            
            for file_path in files_in_package:
                try:
                    deleted = self.vector_store.delete_by_file(file_path)
                    deleted_chunks += deleted
                    if deleted > 0:
                        logger.info(f"Deleted {deleted} old chunks for file: {file_path}")
                except Exception as e:
                    logger.warning(f"Error deleting old chunks for {file_path}: {e}")
                    # Continue with merge even if deletion fails
            
            logger.info(f"Total deleted chunks: {deleted_chunks}")
            
            # Step 7: Merge new chunks into vector store
            logger.info("Merging new chunks into vector store...")
            try:
                self.vector_store.add_chunks(new_chunks)
                merged_chunks = len(new_chunks)
                logger.info(f"Successfully merged {merged_chunks} chunks")
            except Exception as e:
                error_msg = f"Error merging chunks into vector store: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                return MergeResult(
                    success=False,
                    merged_chunks=0,
                    updated_chunks=0,
                    deleted_chunks=deleted_chunks,
                    errors=errors,
                    merge_time_seconds=time.time() - start_time
                )
            
            # Step 8: Update database with new processing state
            logger.info("Updating database with new processing state...")
            db_path = package / "app.db"
            if db_path.exists():
                try:
                    updated_chunks = self._merge_database_state(db_path)
                    logger.info(f"Updated {updated_chunks} file records in database")
                except Exception as e:
                    error_msg = f"Error updating database: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    # Don't fail the merge if database update fails
            else:
                logger.warning("Database file not found in package, skipping database update")
            
            # Step 9: Verify merge integrity
            logger.info("Verifying merge integrity...")
            if not self._verify_merge_integrity(merged_chunks):
                error_msg = "Merge integrity verification failed"
                logger.error(error_msg)
                errors.append(error_msg)
                # Don't fail the merge, just log the warning
            
            merge_time = time.time() - start_time
            logger.info(f"Incremental merge completed successfully in {merge_time:.2f} seconds")
            logger.info(f"Merged: {merged_chunks}, Updated: {updated_chunks}, Deleted: {deleted_chunks}")
            
            return MergeResult(
                success=True,
                merged_chunks=merged_chunks,
                updated_chunks=updated_chunks,
                deleted_chunks=deleted_chunks,
                errors=errors,
                merge_time_seconds=merge_time
            )
            
        except Exception as e:
            logger.error(f"Unexpected error during incremental merge: {e}")
            import traceback
            logger.error(traceback.format_exc())
            errors.append(str(e))
            
            return MergeResult(
                success=False,
                merged_chunks=merged_chunks,
                updated_chunks=updated_chunks,
                deleted_chunks=deleted_chunks,
                errors=errors,
                merge_time_seconds=time.time() - start_time
            )
    
    def validate_compatibility(self, manifest: Dict[str, Any]) -> bool:
        """
        Validate that incremental package is compatible with existing data.
        
        Checks:
        - Embedding dimensions match
        - Model compatibility
        - Manifest structure is valid
        
        Args:
            manifest: Manifest from incremental package
            
        Returns:
            True if compatible, False otherwise
        """
        logger.info("Validating incremental package compatibility")
        
        try:
            # Check manifest has required fields
            if "pi_requirements" not in manifest:
                logger.error("Manifest missing pi_requirements")
                return False
            
            if "desktop_config" not in manifest:
                logger.error("Manifest missing desktop_config")
                return False
            
            # Get embedding dimensions from manifest
            pi_requirements = manifest.get("pi_requirements", {})
            desktop_config = manifest.get("desktop_config", {})
            
            manifest_embedding_dim = pi_requirements.get("embedding_dimension")
            if manifest_embedding_dim is None:
                logger.error("Manifest missing embedding_dimension in pi_requirements")
                return False
            
            # Get embedding dimension from existing vector store
            existing_embedding_dim = self.vector_store.get_embedding_dimension()
            
            # If vector store is empty, any dimension is compatible
            if existing_embedding_dim is None:
                logger.info("Vector store is empty, accepting any embedding dimension")
                return True
            
            # Check if dimensions match
            if manifest_embedding_dim != existing_embedding_dim:
                logger.error(
                    f"Embedding dimension mismatch: "
                    f"existing={existing_embedding_dim}, package={manifest_embedding_dim}"
                )
                return False
            
            logger.info(f"Embedding dimensions match: {manifest_embedding_dim}")
            
            # Check that desktop and Pi dimensions match in manifest
            desktop_embedding_dim = desktop_config.get("embedding_dimension")
            if desktop_embedding_dim != manifest_embedding_dim:
                logger.error(
                    f"Manifest has mismatched embedding dimensions: "
                    f"desktop={desktop_embedding_dim}, pi={manifest_embedding_dim}"
                )
                return False
            
            logger.info("Incremental package is compatible with existing data")
            return True
            
        except Exception as e:
            logger.error(f"Error validating compatibility: {e}")
            return False
    
    def _load_chunks_from_chromadb(self, chromadb_path: Path) -> List[DocumentChunk]:
        """
        Load chunks from incremental ChromaDB directory.
        
        Args:
            chromadb_path: Path to ChromaDB directory
            
        Returns:
            List of DocumentChunk objects
        """
        import chromadb
        from chromadb.config import Settings
        
        chunks = []
        
        try:
            # Initialize ChromaDB client for incremental package
            client = chromadb.PersistentClient(
                path=str(chromadb_path),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get the collection (should have same name as main collection)
            collection_name = self.vector_store.collection.name
            collection = client.get_collection(name=collection_name)
            
            # Get all data from collection
            all_data = collection.get(
                include=["documents", "metadatas", "embeddings"]
            )
            
            # Convert to DocumentChunk objects
            if all_data and all_data['ids']:
                for i in range(len(all_data['ids'])):
                    chunk = DocumentChunk(
                        content=all_data['documents'][i],
                        metadata=all_data['metadatas'][i],
                        embedding=all_data['embeddings'][i]
                    )
                    chunks.append(chunk)
            
            logger.info(f"Loaded {len(chunks)} chunks from incremental ChromaDB")
            
        except Exception as e:
            logger.error(f"Error loading chunks from ChromaDB: {e}")
            raise
        
        return chunks
    
    def _get_files_from_chunks(self, chunks: List[DocumentChunk]) -> set:
        """
        Extract unique file paths from chunks.
        
        Args:
            chunks: List of DocumentChunk objects
            
        Returns:
            Set of file paths
        """
        files = set()
        
        for chunk in chunks:
            metadata = chunk.metadata
            if 'filename' in metadata and 'folder_path' in metadata:
                # Construct file path from metadata
                folder_path = metadata['folder_path']
                filename = metadata['filename']
                file_path = os.path.join(folder_path, filename)
                files.add(file_path)
        
        return files
    
    def _merge_database_state(self, db_path: Path) -> int:
        """
        Merge database state from incremental package.
        
        Updates processed_files table with new/modified files.
        Uses "newer wins" strategy - updates existing records with newer data.
        
        Args:
            db_path: Path to incremental database file
            
        Returns:
            Number of file records updated
        """
        import sqlite3
        
        updated_count = 0
        
        try:
            # Connect to incremental database
            inc_conn = sqlite3.connect(str(db_path))
            inc_conn.row_factory = sqlite3.Row
            inc_cursor = inc_conn.cursor()
            
            # Get all processed files from incremental database
            inc_cursor.execute("""
                SELECT file_path, folder_id, file_hash, modified_at, processed_at, file_type
                FROM processed_files
            """)
            
            inc_files = inc_cursor.fetchall()
            logger.info(f"Found {len(inc_files)} file records in incremental database")
            
            # Merge into main database
            with self.db_manager.transaction() as conn:
                for row in inc_files:
                    file_path = row['file_path']
                    
                    # Check if file already exists in main database
                    cursor = conn.execute(
                        "SELECT id, processed_at FROM processed_files WHERE file_path = ?",
                        (file_path,)
                    )
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Update existing record with newer data
                        conn.execute("""
                            UPDATE processed_files
                            SET folder_id = ?, file_hash = ?, modified_at = ?, 
                                processed_at = ?, file_type = ?
                            WHERE file_path = ?
                        """, (
                            row['folder_id'],
                            row['file_hash'],
                            row['modified_at'],
                            row['processed_at'],
                            row['file_type'],
                            file_path
                        ))
                        logger.debug(f"Updated existing file record: {file_path}")
                    else:
                        # Insert new record
                        conn.execute("""
                            INSERT INTO processed_files 
                            (file_path, folder_id, file_hash, modified_at, processed_at, file_type)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            file_path,
                            row['folder_id'],
                            row['file_hash'],
                            row['modified_at'],
                            row['processed_at'],
                            row['file_type']
                        ))
                        logger.debug(f"Inserted new file record: {file_path}")
                    
                    updated_count += 1
            
            inc_conn.close()
            logger.info(f"Successfully merged {updated_count} file records")
            
        except Exception as e:
            logger.error(f"Error merging database state: {e}")
            raise
        
        return updated_count
    
    def _verify_merge_integrity(self, expected_chunks: int) -> bool:
        """
        Verify merge integrity by checking vector store state.
        
        Args:
            expected_chunks: Expected number of chunks merged
            
        Returns:
            True if integrity check passes, False otherwise
        """
        try:
            # Get current vector store stats
            stats = self.vector_store.get_stats()
            total_chunks = stats.get('total_chunks', 0)
            
            logger.info(f"Vector store now contains {total_chunks} total chunks")
            
            # Basic sanity check - we should have at least the merged chunks
            if total_chunks < expected_chunks:
                logger.error(
                    f"Integrity check failed: "
                    f"expected at least {expected_chunks} chunks, found {total_chunks}"
                )
                return False
            
            # Check that embedding dimension is still valid
            embedding_dim = self.vector_store.get_embedding_dimension()
            if embedding_dim is None:
                logger.error("Integrity check failed: cannot determine embedding dimension")
                return False
            
            logger.info(f"Integrity check passed: {total_chunks} chunks, dimension={embedding_dim}")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying merge integrity: {e}")
            return False


class MergeError(Exception):
    """Exception raised when merge operation fails."""
    pass
