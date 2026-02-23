"""
Embedding Engine for RAG Chatbot with Vision Processing

This module provides text embedding generation using either:
1. Ollama models (mxbai-embed-large, nomic-embed-text, etc.)
2. Sentence-transformers models (fallback)

It supports batch processing for efficiency and hardware detection for acceleration.
"""

import torch
from sentence_transformers import SentenceTransformer
from typing import List, Union
import logging
import time
import requests

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """
    Generates embeddings for text chunks using Ollama or sentence-transformers.
    
    Features:
    - Supports Ollama models (mxbai-embed-large: 1024-dim, nomic-embed-text: 768-dim)
    - Falls back to sentence-transformers if Ollama not available
    - Batch processing with configurable batch size (default: 32)
    - Hardware detection (CUDA vs CPU) for acceleration
    """
    
    def __init__(self, model_name: str = "mxbai-embed-large", batch_size: int = 32, ollama_endpoint: str = "http://localhost:11434", remote_embedding_api: str = None):
        """
        Initialize the embedding engine.
        
        Args:
            model_name: Name of the model to use (Ollama or sentence-transformers)
            batch_size: Number of texts to process in each batch
            ollama_endpoint: Ollama API endpoint
            remote_embedding_api: Optional remote API endpoint for embeddings (e.g., "http://192.168.1.100:8000")
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.ollama_endpoint = ollama_endpoint
        self.remote_embedding_api = remote_embedding_api
        self.use_ollama = False
        self.use_remote = False
        self.device = self._detect_hardware()
        
        logger.info(f"Initializing embedding engine with model: {model_name}")
        
        # Try remote API first (if configured)
        if remote_embedding_api:
            if self._check_remote_api_available():
                logger.info(f"✓ Using remote embedding API: {remote_embedding_api}")
                self.use_remote = True
                self._embedding_dimension = self._get_remote_dimension()
                logger.info(f"Embedding engine initialized successfully")
                logger.info(f"Embedding dimension: {self._embedding_dimension}")
                return
            else:
                logger.warning(f"Remote embedding API not available: {remote_embedding_api}")
                logger.warning(f"Falling back to local embedding model")
        
        # Try to use Ollama
        if self._check_ollama_available():
            logger.info(f"✓ Using Ollama for embeddings: {model_name}")
            logger.info(f"✓ Ollama handles GPU acceleration automatically")
            self.use_ollama = True
            self._embedding_dimension = self._get_ollama_dimension()
        else:
            # Fall back to sentence-transformers
            logger.info(f"Ollama not available, falling back to sentence-transformers")
            logger.info(f"Using device: {self.device}")
            self.model = SentenceTransformer(model_name, device=self.device)
            self._embedding_dimension = self.model.get_sentence_embedding_dimension()
        
        logger.info(f"Embedding engine initialized successfully")
        logger.info(f"Embedding dimension: {self._embedding_dimension}")
    
    def _check_ollama_available(self) -> bool:
        """Check if Ollama is available and has the model."""
        try:
            response = requests.get(f"{self.ollama_endpoint}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                # Check if our model is available
                return any(self.model_name in name for name in model_names)
            return False
        except Exception as e:
            logger.debug(f"Ollama not available: {e}")
            return False
    
    def _get_ollama_dimension(self) -> int:
        """Get embedding dimension from Ollama model."""
        # Known dimensions for common models
        dimensions = {
            "mxbai-embed-large": 1024,
            "nomic-embed-text": 768,
            "all-minilm": 384,
            "qwen3-embedding": 4096,  # Qwen3 multilingual embedding model
            "bge-m3": 1024,  # BGE-M3 multilingual embedding model (excellent Korean-English cross-lingual)
        }
        
        for model_key, dim in dimensions.items():
            if model_key in self.model_name.lower():
                return dim
        
        # Default to testing with a sample
        try:
            test_embedding = self._generate_ollama_embedding("test")
            return len(test_embedding)
        except:
            logger.warning("Could not determine Ollama embedding dimension, defaulting to 1024")
            return 1024
    
    def _generate_ollama_embedding(self, text: str) -> List[float]:
        """Generate embedding using Ollama API."""
        try:
            # Truncate text if too long (Ollama has token limits)
            # bge-m3 supports 8192 tokens (~32k characters)
            max_chars = 30000
            if len(text) > max_chars:
                logger.warning(f"Text too long ({len(text)} chars), truncating to {max_chars}")
                text = text[:max_chars]
            
            response = requests.post(
                f"{self.ollama_endpoint}/api/embed",
                json={"model": self.model_name, "input": text},
                timeout=120  # Increased timeout for Pi with swap
            )
            response.raise_for_status()
            result = response.json()
            # Ollama returns embeddings in 'embeddings' field (list of lists)
            embeddings = result.get("embeddings", [[]])
            return embeddings[0] if embeddings else []
        except Exception as e:
            logger.error(f"Ollama embedding generation failed: {e}")
            raise
    
    def _detect_hardware(self) -> str:
        """
        Detect available hardware for acceleration.
        
        Note: This is only used for sentence-transformers fallback.
        Ollama handles GPU acceleration automatically.
        
        Returns:
            Device string: 'cuda' if NVIDIA GPU available, 'mps' if Apple Silicon, else 'cpu'
        """
        if torch.cuda.is_available():
            device = 'cuda'
            logger.debug(f"PyTorch CUDA detected: {torch.cuda.get_device_name(0)}")
        elif torch.backends.mps.is_available():
            device = 'mps'
            logger.debug("PyTorch MPS (Apple Silicon) detected")
        else:
            device = 'cpu'
            logger.debug("PyTorch will use CPU (Ollama handles GPU independently)")
        
        return device
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this model.
        
        Returns:
            Embedding dimension
        """
        return self._embedding_dimension
    
    def generate_embedding(self, text: str, max_retries: int = 3) -> List[float]:
        """
        Generate embedding for a single text with retry logic.
        
        Args:
            text: Input text to embed
            max_retries: Maximum number of retry attempts (default: 3)
            
        Returns:
            List of floats representing the embedding vector
            
        Raises:
            RuntimeError: If embedding generation fails after all retries
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding generation")
            # Return zero vector for empty text
            return [0.0] * self.get_embedding_dimension()
        
        # Truncate text if it's too long to prevent 400 Bad Request errors
        # qwen3-embedding supports 40960 tokens (~160k characters)
        # Being conservative but allowing much more text for better context
        MAX_CHARS = 32000
        if len(text) > MAX_CHARS:
            logger.warning(f"Text too long ({len(text)} chars), truncating to {MAX_CHARS} chars")
            text = text[:MAX_CHARS] + "... [truncated]"
        
        last_error = None
        for attempt in range(max_retries):
            try:
                if self.use_ollama:
                    embedding = self._generate_ollama_embedding(text)
                else:
                    embedding = self.model.encode(text, convert_to_tensor=False, show_progress_bar=False)
                    embedding = embedding.tolist()
                return embedding
            except Exception as e:
                last_error = e
                logger.warning(f"Embedding generation failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
        
        # All retries failed
        error_msg = f"Failed to generate embedding after {max_retries} attempts: {last_error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    def generate_embeddings_batch(self, texts: List[str], max_retries: int = 3) -> List[List[float]]:
        """
        Generate embeddings for multiple texts using batch processing with retry logic.
        
        Args:
            texts: List of input texts to embed
            max_retries: Maximum number of retry attempts (default: 3)
            
        Returns:
            List of embedding vectors (one per input text)
            
        Raises:
            RuntimeError: If embedding generation fails after all retries
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
        
        # Generate embeddings with batch processing and retry logic
        last_error = None
        for attempt in range(max_retries):
            try:
                if self.use_ollama:
                    # Ollama doesn't support batch processing well, so process individually
                    # but we can do it more efficiently
                    embeddings_list = []
                    for text in non_empty_texts:
                        emb = self._generate_ollama_embedding(text)
                        embeddings_list.append(emb)
                else:
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
                
            except Exception as e:
                last_error = e
                logger.warning(f"Batch embedding generation failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
        
        # All retries failed
        error_msg = f"Failed to generate batch embeddings after {max_retries} attempts: {last_error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
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
            "embedding_dimension": self.get_embedding_dimension(),
            "using_ollama": self.use_ollama
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


def get_embedding_engine(model_name: str = None, ollama_endpoint: str = None) -> EmbeddingEngine:
    """
    Get or create the singleton embedding engine instance.
    
    Args:
        model_name: Optional model name (uses config default if not provided)
        ollama_endpoint: Optional Ollama endpoint (uses config default if not provided)
    
    Returns:
        EmbeddingEngine instance
    """
    global _embedding_engine_instance
    if _embedding_engine_instance is None:
        from backend.config import Config
        model_name = model_name or Config.EMBEDDING_MODEL
        ollama_endpoint = ollama_endpoint or Config.OLLAMA_ENDPOINT
        _embedding_engine_instance = EmbeddingEngine(model_name=model_name, ollama_endpoint=ollama_endpoint)
    return _embedding_engine_instance
