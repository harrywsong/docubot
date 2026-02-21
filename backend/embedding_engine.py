"""
Embedding Engine for RAG Chatbot with Vision Processing

This module provides text embedding generation using sentence-transformers.
It supports batch processing for efficiency and hardware detection for acceleration.
"""

import torch
from sentence_transformers import SentenceTransformer
from typing import List, Union
import logging

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """
    Generates embeddings for text chunks using sentence-transformers.
    
    Features:
    - Uses all-MiniLM-L6-v2 model (384-dimensional embeddings)
    - Batch processing with configurable batch size (default: 32)
    - Hardware detection (CUDA vs CPU) for acceleration
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", batch_size: int = 32):
        """
        Initialize the embedding engine.
        
        Args:
            model_name: Name of the sentence-transformers model to use
            batch_size: Number of texts to process in each batch
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.device = self._detect_hardware()
        
        logger.info(f"Initializing embedding engine with model: {model_name}")
        logger.info(f"Using device: {self.device}")
        
        # Load the model
        self.model = SentenceTransformer(model_name, device=self.device)
        
        logger.info(f"Embedding engine initialized successfully")
        logger.info(f"Embedding dimension: {self.get_embedding_dimension()}")
    
    def _detect_hardware(self) -> str:
        """
        Detect available hardware for acceleration.
        
        Returns:
            Device string: 'cuda' if NVIDIA GPU available, 'mps' if Apple Silicon, else 'cpu'
        """
        if torch.cuda.is_available():
            device = 'cuda'
            logger.info(f"CUDA detected: {torch.cuda.get_device_name(0)}")
        elif torch.backends.mps.is_available():
            device = 'mps'
            logger.info("Apple Silicon (MPS) detected")
        else:
            device = 'cpu'
            logger.info("No GPU acceleration available, using CPU")
        
        return device
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this model.
        
        Returns:
            Embedding dimension (384 for all-MiniLM-L6-v2)
        """
        return self.model.get_sentence_embedding_dimension()
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding generation")
            # Return zero vector for empty text
            return [0.0] * self.get_embedding_dimension()
        
        embedding = self.model.encode(text, convert_to_tensor=False, show_progress_bar=False)
        return embedding.tolist()
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts using batch processing.
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of embedding vectors (one per input text)
        """
        if not texts:
            logger.warning("Empty text list provided for batch embedding generation")
            return []
        
        # Filter out empty texts but keep track of indices
        non_empty_texts = []
        non_empty_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                non_empty_texts.append(text)
                non_empty_indices.append(i)
        
        if not non_empty_texts:
            logger.warning("All texts in batch are empty")
            # Return zero vectors for all texts
            dim = self.get_embedding_dimension()
            return [[0.0] * dim for _ in texts]
        
        logger.info(f"Generating embeddings for {len(non_empty_texts)} texts (batch size: {self.batch_size})")
        
        # Generate embeddings with batch processing
        embeddings = self.model.encode(
            non_empty_texts,
            batch_size=self.batch_size,
            convert_to_tensor=False,
            show_progress_bar=len(non_empty_texts) > 100  # Show progress for large batches
        )
        
        # Convert to list of lists
        embeddings_list = [emb.tolist() for emb in embeddings]
        
        # Reconstruct full list with zero vectors for empty texts
        dim = self.get_embedding_dimension()
        result = []
        non_empty_idx = 0
        for i in range(len(texts)):
            if i in non_empty_indices:
                result.append(embeddings_list[non_empty_idx])
                non_empty_idx += 1
            else:
                result.append([0.0] * dim)
        
        logger.info(f"Successfully generated {len(result)} embeddings")
        return result
    
    def get_device_info(self) -> dict:
        """
        Get information about the hardware being used.
        
        Returns:
            Dictionary with device information
        """
        info = {
            "device": self.device,
            "model_name": self.model_name,
            "batch_size": self.batch_size,
            "embedding_dimension": self.get_embedding_dimension()
        }
        
        if self.device == 'cuda':
            info["gpu_name"] = torch.cuda.get_device_name(0)
            info["gpu_memory_allocated"] = torch.cuda.memory_allocated(0)
            info["gpu_memory_reserved"] = torch.cuda.memory_reserved(0)
        elif self.device == 'mps':
            info["acceleration"] = "Apple Silicon (Metal)"
        
        return info


# Singleton instance for reuse across the application
_embedding_engine_instance = None


def get_embedding_engine() -> EmbeddingEngine:
    """
    Get or create the singleton embedding engine instance.
    
    Returns:
        EmbeddingEngine instance
    """
    global _embedding_engine_instance
    if _embedding_engine_instance is None:
        _embedding_engine_instance = EmbeddingEngine()
    return _embedding_engine_instance
