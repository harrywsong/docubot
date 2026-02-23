"""
FAISS-based vector store for Pi deployment.

This module provides a lightweight alternative to ChromaDB that doesn't require
an embedding model on the Pi. It uses pre-computed embeddings and FAISS for fast
similarity search.

Key features:
- No embedding model needed on Pi (saves ~1.2GB RAM)
- Fast similarity search with FAISS
- Fallback to keyword-based search if needed
- Compatible with existing ChromaDB exports
"""

import json
import logging
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS not available - install with: pip install faiss-cpu")


class FAISSVectorStore:
    """
    Lightweight vector store using FAISS for Pi deployment.
    
    This store uses pre-computed embeddings and doesn't require an embedding
    model to be loaded on the Pi.
    """
    
    def __init__(self, index_path: str = "data/faiss_index"):
        """
        Initialize FAISS vector store.
        
        Args:
            index_path: Path to FAISS index directory
        """
        self.index_path = Path(index_path)
        self.index = None
        self.chunks = []
        self.metadata = []
        self.dimension = None
        
        if not FAISS_AVAILABLE:
            raise RuntimeError("FAISS is not installed. Install with: pip install faiss-cpu")
        
        # Load index if it exists
        if self.index_path.exists():
            self.load()
        else:
            logger.info(f"No FAISS index found at {index_path}")
    
    def build_from_chromadb(self, chromadb_collection, output_path: str = None):
        """
        Build FAISS index from existing ChromaDB collection.
        
        Args:
            chromadb_collection: ChromaDB collection object
            output_path: Optional output path (defaults to self.index_path)
        """
        logger.info("Building FAISS index from ChromaDB...")
        
        # Get all data from ChromaDB
        results = chromadb_collection.get(
            include=["embeddings", "documents", "metadatas"]
        )
        
        if not results['ids']:
            logger.warning("No data in ChromaDB collection")
            return
        
        # Extract embeddings and metadata
        embeddings = np.array(results['embeddings'], dtype=np.float32)
        self.chunks = results['documents']
        self.metadata = results['metadatas']
        self.dimension = embeddings.shape[1]
        
        logger.info(f"Building FAISS index with {len(embeddings)} vectors (dim={self.dimension})")
        
        # Build FAISS index
        # Using IndexFlatIP (inner product) for cosine similarity
        # Normalize vectors for cosine similarity
        faiss.normalize_L2(embeddings)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(embeddings)
        
        logger.info(f"✓ FAISS index built with {self.index.ntotal} vectors")
        
        # Save index
        save_path = Path(output_path) if output_path else self.index_path
        self.save(save_path)
    
    def save(self, path: Path = None):
        """
        Save FAISS index and metadata to disk.
        
        Args:
            path: Output directory path
        """
        path = path or self.index_path
        path.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        index_file = path / "index.faiss"
        faiss.write_index(self.index, str(index_file))
        logger.info(f"✓ Saved FAISS index to {index_file}")
        
        # Save chunks and metadata
        data_file = path / "data.pkl"
        with open(data_file, 'wb') as f:
            pickle.dump({
                'chunks': self.chunks,
                'metadata': self.metadata,
                'dimension': self.dimension
            }, f)
        logger.info(f"✓ Saved metadata to {data_file}")
    
    def load(self, path: Path = None):
        """
        Load FAISS index and metadata from disk.
        
        Args:
            path: Input directory path
        """
        path = path or self.index_path
        
        # Load FAISS index
        index_file = path / "index.faiss"
        if not index_file.exists():
            raise FileNotFoundError(f"FAISS index not found: {index_file}")
        
        self.index = faiss.read_index(str(index_file))
        logger.info(f"✓ Loaded FAISS index from {index_file} ({self.index.ntotal} vectors)")
        
        # Load chunks and metadata
        data_file = path / "data.pkl"
        if not data_file.exists():
            raise FileNotFoundError(f"Metadata file not found: {data_file}")
        
        with open(data_file, 'rb') as f:
            data = pickle.load(f)
            self.chunks = data['chunks']
            self.metadata = data['metadata']
            self.dimension = data['dimension']
        
        logger.info(f"✓ Loaded {len(self.chunks)} chunks (dim={self.dimension})")
    
    def query(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query FAISS index with pre-computed embedding.
        
        Args:
            query_embedding: Pre-computed query embedding vector
            top_k: Number of results to return
            metadata_filter: Optional metadata filters (e.g., {"user_id": 3})
            
        Returns:
            List of results with content, metadata, and similarity scores
        """
        if self.index is None:
            raise RuntimeError("FAISS index not loaded")
        
        # Convert to numpy array and normalize
        query_vec = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_vec)
        
        # Search FAISS index
        # Get more results if we need to filter
        search_k = top_k * 10 if metadata_filter else top_k
        distances, indices = self.index.search(query_vec, search_k)
        
        # Build results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue
            
            metadata = self.metadata[idx]
            
            # Apply metadata filter
            if metadata_filter:
                if not all(metadata.get(k) == v for k, v in metadata_filter.items()):
                    continue
            
            results.append({
                'content': self.chunks[idx],
                'metadata': metadata,
                'similarity_score': float(dist),
                'index': int(idx)
            })
            
            if len(results) >= top_k:
                break
        
        logger.info(f"FAISS query returned {len(results)} results")
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the FAISS index.
        
        Returns:
            Dictionary with index statistics
        """
        if self.index is None:
            return {
                'loaded': False,
                'total_vectors': 0,
                'dimension': None
            }
        
        return {
            'loaded': True,
            'total_vectors': self.index.ntotal,
            'dimension': self.dimension,
            'total_chunks': len(self.chunks)
        }


# Singleton instance
_faiss_store_instance = None


def get_faiss_store(index_path: str = None) -> FAISSVectorStore:
    """
    Get or create the singleton FAISS store instance.
    
    Args:
        index_path: Optional index path
    
    Returns:
        FAISSVectorStore instance
    """
    global _faiss_store_instance
    if _faiss_store_instance is None:
        _faiss_store_instance = FAISSVectorStore(index_path=index_path or "data/faiss_index")
    return _faiss_store_instance
