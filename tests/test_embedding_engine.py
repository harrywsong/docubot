"""
Unit tests for the embedding engine.
"""

import pytest
from backend.embedding_engine import EmbeddingEngine, get_embedding_engine


class TestEmbeddingEngine:
    """Test cases for EmbeddingEngine class."""
    
    def test_initialization(self):
        """Test that embedding engine initializes correctly."""
        engine = EmbeddingEngine()
        
        assert engine.model_name == "paraphrase-multilingual-MiniLM-L12-v2"
        assert engine.batch_size == 32
        assert engine.device in ['cuda', 'mps', 'cpu']
        assert engine.model is not None
    
    def test_embedding_dimension(self):
        """Test that embedding dimension is correct for paraphrase-multilingual-MiniLM-L12-v2."""
        engine = EmbeddingEngine()
        
        dim = engine.get_embedding_dimension()
        assert dim == 384  # paraphrase-multilingual-MiniLM-L12-v2 produces 384-dimensional embeddings
    
    def test_generate_single_embedding(self):
        """Test generating embedding for a single text."""
        engine = EmbeddingEngine()
        
        text = "This is a test document about machine learning."
        embedding = engine.generate_embedding(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)
    
    def test_generate_empty_text_embedding(self):
        """Test that empty text returns zero vector."""
        engine = EmbeddingEngine()
        
        embedding = engine.generate_embedding("")
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(x == 0.0 for x in embedding)
    
    def test_generate_batch_embeddings(self):
        """Test generating embeddings for multiple texts."""
        engine = EmbeddingEngine()
        
        texts = [
            "First document about AI",
            "Second document about machine learning",
            "Third document about neural networks"
        ]
        
        embeddings = engine.generate_embeddings_batch(texts)
        
        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)
        assert all(isinstance(emb, list) for emb in embeddings)
    
    def test_generate_batch_with_empty_texts(self):
        """Test batch generation with some empty texts."""
        engine = EmbeddingEngine()
        
        texts = [
            "Valid text",
            "",
            "Another valid text",
            "   ",  # Whitespace only
            "Final valid text"
        ]
        
        embeddings = engine.generate_embeddings_batch(texts)
        
        assert len(embeddings) == 5
        # Empty texts should have zero vectors
        assert all(x == 0.0 for x in embeddings[1])
        assert all(x == 0.0 for x in embeddings[3])
        # Valid texts should have non-zero embeddings
        assert any(x != 0.0 for x in embeddings[0])
        assert any(x != 0.0 for x in embeddings[2])
        assert any(x != 0.0 for x in embeddings[4])
    
    def test_generate_empty_batch(self):
        """Test that empty batch returns empty list."""
        engine = EmbeddingEngine()
        
        embeddings = engine.generate_embeddings_batch([])
        
        assert embeddings == []
    
    def test_device_info(self):
        """Test getting device information."""
        engine = EmbeddingEngine()
        
        info = engine.get_device_info()
        
        assert "device" in info
        assert "model_name" in info
        assert "batch_size" in info
        assert "embedding_dimension" in info
        assert info["device"] in ['cuda', 'mps', 'cpu']
        assert info["model_name"] == "paraphrase-multilingual-MiniLM-L12-v2"
        assert info["batch_size"] == 32
        assert info["embedding_dimension"] == 384
    
    def test_singleton_pattern(self):
        """Test that get_embedding_engine returns the same instance."""
        engine1 = get_embedding_engine()
        engine2 = get_embedding_engine()
        
        assert engine1 is engine2
    
    def test_custom_batch_size(self):
        """Test initialization with custom batch size."""
        engine = EmbeddingEngine(batch_size=16)
        
        assert engine.batch_size == 16
    
    def test_embeddings_are_consistent(self):
        """Test that same text produces same embedding."""
        engine = EmbeddingEngine()
        
        text = "Consistency test"
        embedding1 = engine.generate_embedding(text)
        embedding2 = engine.generate_embedding(text)
        
        # Embeddings should be identical for same input
        assert embedding1 == embedding2
    
    def test_different_texts_produce_different_embeddings(self):
        """Test that different texts produce different embeddings."""
        engine = EmbeddingEngine()
        
        text1 = "Machine learning is fascinating"
        text2 = "I love pizza and pasta"
        
        embedding1 = engine.generate_embedding(text1)
        embedding2 = engine.generate_embedding(text2)
        
        # Embeddings should be different
        assert embedding1 != embedding2
