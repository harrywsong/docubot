"""
Vector Store for RAG Chatbot with Vision Processing

This module provides a ChromaDB wrapper for storing and querying document embeddings.
It supports persistent storage, metadata filtering, and similarity search.
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional, Any
import logging
import os
from pathlib import Path
import uuid

from backend.models import DocumentChunk, QueryResult

logger = logging.getLogger(__name__)


class VectorStore:
    """
    ChromaDB wrapper for storing and querying document embeddings.
    
    Features:
    - Persistent storage in data/chromadb/
    - Metadata filtering for date and merchant queries
    - Similarity search with top-k retrieval
    - Support for both text and image document chunks
    """
    
    def __init__(self, persist_directory: str = "data/chromadb"):
        """
        Initialize the vector store.
        
        Args:
            persist_directory: Directory for persistent ChromaDB storage
        """
        self.persist_directory = persist_directory
        self.collection_name = "documents"
        
        # Create directory if it doesn't exist
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initializing ChromaDB vector store at: {persist_directory}")
        
        # Initialize ChromaDB client with persistent storage
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Document chunks with embeddings for RAG chatbot"}
        )
        
        logger.info(f"Vector store initialized with collection: {self.collection_name}")
        logger.info(f"Current document count: {self.collection.count()}")
    
    def initialize(self) -> None:
        """
        Initialize or reset the vector store.
        This method is idempotent and can be called multiple times.
        """
        logger.info("Vector store initialization complete")
    
    def add_chunks(self, chunks: List[DocumentChunk]) -> None:
        """
        Add document chunks with embeddings to the vector store.
        
        Args:
            chunks: List of DocumentChunk objects with embeddings
        """
        if not chunks:
            logger.warning("No chunks provided to add_chunks")
            return
        
        # Prepare data for ChromaDB
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        
        for chunk in chunks:
            if chunk.embedding is None:
                logger.warning(f"Chunk missing embedding, skipping: {chunk.metadata.get('filename', 'unknown')}")
                continue
            
            # Generate unique ID for this chunk
            chunk_id = str(uuid.uuid4())
            ids.append(chunk_id)
            
            # Add embedding
            embeddings.append(chunk.embedding)
            
            # Add document content
            documents.append(chunk.content)
            
            # Add metadata (ChromaDB requires all values to be strings, ints, floats, or bools)
            metadata = self._prepare_metadata(chunk.metadata)
            metadatas.append(metadata)
        
        if not ids:
            logger.warning("No valid chunks to add after filtering")
            return
        
        logger.info(f"Adding {len(ids)} chunks to vector store")
        
        # Add to ChromaDB collection
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        
        logger.info(f"Successfully added {len(ids)} chunks. Total documents: {self.collection.count()}")
    
    def _prepare_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare metadata for ChromaDB storage.
        ChromaDB requires metadata values to be strings, ints, floats, or bools.
        
        Args:
            metadata: Raw metadata dictionary
            
        Returns:
            Cleaned metadata dictionary
        """
        cleaned = {}
        
        for key, value in metadata.items():
            if value is None:
                continue
            
            # Convert to appropriate type
            if isinstance(value, (str, int, float, bool)):
                cleaned[key] = value
            elif isinstance(value, list):
                # Convert lists to comma-separated strings
                cleaned[key] = ",".join(str(v) for v in value)
            else:
                # Convert other types to string
                cleaned[key] = str(value)
        
        return cleaned
    
    def query(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[QueryResult]:
        """
        Query the vector store for similar chunks.
        
        Args:
            query_embedding: Embedding vector for the query
            top_k: Number of results to return (default: 5)
            metadata_filter: Optional metadata filters (e.g., {"merchant": "Costco", "date": "2026-02-11"})
            
        Returns:
            List of QueryResult objects with content, metadata, and similarity scores
        """
        if not query_embedding:
            logger.warning("Empty query embedding provided")
            return []
        
        # Check if collection is empty
        if self.collection.count() == 0:
            logger.warning("Vector store is empty, no results to return")
            return []
        
        logger.info(f"Querying vector store with top_k={top_k}, filter={metadata_filter}")
        
        # Prepare where clause for metadata filtering
        where_clause = None
        if metadata_filter:
            where_clause = self._build_where_clause(metadata_filter)
        
        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count()),
            where=where_clause,
            include=["documents", "metadatas", "distances"]
        )
        
        # Parse results
        query_results = []
        
        if results and results['ids'] and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                chunk_id = results['ids'][0][i]
                content = results['documents'][0][i]
                metadata = results['metadatas'][0][i]
                distance = results['distances'][0][i]
                
                # Convert distance to similarity score (lower distance = higher similarity)
                # For cosine distance, similarity = 1 - distance
                similarity_score = 1.0 - distance
                
                query_results.append(QueryResult(
                    chunk_id=chunk_id,
                    content=content,
                    metadata=metadata,
                    similarity_score=similarity_score
                ))
        
        logger.info(f"Found {len(query_results)} matching chunks")
        return query_results
    
    def _build_where_clause(self, metadata_filter: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build ChromaDB where clause from metadata filter.
        
        Args:
            metadata_filter: Dictionary of metadata filters
            
        Returns:
            ChromaDB where clause
        """
        # ChromaDB where clause format: {"field": {"$eq": "value"}}
        # For multiple conditions, use {"$and": [condition1, condition2]}
        
        conditions = []
        
        for key, value in metadata_filter.items():
            if value is not None:
                conditions.append({key: {"$eq": value}})
        
        if len(conditions) == 0:
            return None
        elif len(conditions) == 1:
            return conditions[0]
        else:
            return {"$and": conditions}
    
    def delete_by_folder(self, folder_path: str) -> int:
        """
        Delete all chunks associated with a specific folder.
        
        Args:
            folder_path: Path of the folder whose chunks should be deleted
            
        Returns:
            Number of chunks deleted
        """
        logger.info(f"Deleting chunks for folder: {folder_path}")
        
        # Query for all chunks with this folder_path
        try:
            results = self.collection.get(
                where={"folder_path": {"$eq": folder_path}},
                include=["metadatas"]
            )
            
            if results and results['ids']:
                chunk_ids = results['ids']
                logger.info(f"Found {len(chunk_ids)} chunks to delete")
                
                # Delete the chunks
                self.collection.delete(ids=chunk_ids)
                
                logger.info(f"Successfully deleted {len(chunk_ids)} chunks")
                return len(chunk_ids)
            else:
                logger.info("No chunks found for this folder")
                return 0
                
        except Exception as e:
            logger.error(f"Error deleting chunks for folder {folder_path}: {e}")
            raise
    
    def delete_by_file(self, file_path: str) -> int:
        """
        Delete all chunks associated with a specific file.
        
        Args:
            file_path: Path of the file whose chunks should be deleted
            
        Returns:
            Number of chunks deleted
        """
        logger.info(f"Deleting chunks for file: {file_path}")
        
        # Query for all chunks with this file_path
        try:
            # ChromaDB stores filename in metadata, need to match full path
            results = self.collection.get(
                where={"filename": {"$eq": os.path.basename(file_path)}},
                include=["metadatas"]
            )
            
            if results and results['ids']:
                # Filter by full path to be precise
                chunk_ids_to_delete = []
                for i, metadata in enumerate(results['metadatas']):
                    # Reconstruct full path from metadata
                    stored_folder = metadata.get('folder_path', '')
                    stored_filename = metadata.get('filename', '')
                    stored_path = os.path.join(stored_folder, stored_filename)
                    
                    if stored_path == file_path:
                        chunk_ids_to_delete.append(results['ids'][i])
                
                if chunk_ids_to_delete:
                    logger.info(f"Found {len(chunk_ids_to_delete)} chunks to delete")
                    self.collection.delete(ids=chunk_ids_to_delete)
                    logger.info(f"Successfully deleted {len(chunk_ids_to_delete)} chunks")
                    return len(chunk_ids_to_delete)
            
            logger.info("No chunks found for this file")
            return 0
            
        except Exception as e:
            logger.error(f"Error deleting chunks for file {file_path}: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "total_chunks": self.collection.count(),
            "collection_name": self.collection_name,
            "persist_directory": self.persist_directory
        }
    
    def reset(self) -> None:
        """
        Reset the vector store by deleting all data.
        WARNING: This operation cannot be undone.
        """
        logger.warning("Resetting vector store - all data will be deleted")
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"description": "Document chunks with embeddings for RAG chatbot"}
        )
        logger.info("Vector store reset complete")


# Singleton instance for reuse across the application
_vector_store_instance = None


def get_vector_store() -> VectorStore:
    """
    Get or create the singleton vector store instance.
    
    Returns:
        VectorStore instance
    """
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance
