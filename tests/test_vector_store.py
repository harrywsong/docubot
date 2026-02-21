"""
Unit tests for the vector store.
"""

import pytest
import os
import shutil
from backend.vector_store import VectorStore, get_vector_store
from backend.models import DocumentChunk, QueryResult


@pytest.fixture
def temp_vector_store(tmp_path):
    """Create a temporary vector store for testing."""
    store_path = str(tmp_path / "test_chromadb")
    store = VectorStore(persist_directory=store_path)
    yield store
    # Cleanup - close ChromaDB client first to release file locks
    try:
        del store.collection
        del store.client
    except:
        pass
    # Give Windows time to release file locks
    import time
    time.sleep(0.1)
    # Cleanup with error handling for Windows file locks
    if os.path.exists(store_path):
        try:
            shutil.rmtree(store_path)
        except PermissionError:
            # Windows file locking - ignore cleanup errors
            pass


class TestVectorStore:
    """Test cases for VectorStore class."""
    
    def test_initialization(self, temp_vector_store):
        """Test that vector store initializes correctly."""
        store = temp_vector_store
        
        assert store.collection_name == "documents"
        assert store.collection is not None
        assert store.collection.count() == 0
    
    def test_add_single_chunk(self, temp_vector_store):
        """Test adding a single chunk to the vector store."""
        store = temp_vector_store
        
        chunk = DocumentChunk(
            content="This is a test document",
            metadata={
                "filename": "test.txt",
                "folder_path": "/test/folder",
                "file_type": "text",
                "page_number": 1
            },
            embedding=[0.1] * 384  # Mock embedding
        )
        
        store.add_chunks([chunk])
        
        assert store.collection.count() == 1
    
    def test_add_multiple_chunks(self, temp_vector_store):
        """Test adding multiple chunks to the vector store."""
        store = temp_vector_store
        
        chunks = [
            DocumentChunk(
                content=f"Document {i}",
                metadata={
                    "filename": f"doc{i}.txt",
                    "folder_path": "/test/folder",
                    "file_type": "text"
                },
                embedding=[0.1 * i] * 384
            )
            for i in range(5)
        ]
        
        store.add_chunks(chunks)
        
        assert store.collection.count() == 5
    
    def test_add_chunk_without_embedding(self, temp_vector_store):
        """Test that chunks without embeddings are skipped."""
        store = temp_vector_store
        
        chunks = [
            DocumentChunk(
                content="Valid chunk",
                metadata={"filename": "valid.txt"},
                embedding=[0.1] * 384
            ),
            DocumentChunk(
                content="Invalid chunk",
                metadata={"filename": "invalid.txt"},
                embedding=None  # No embedding
            )
        ]
        
        store.add_chunks(chunks)
        
        # Only the valid chunk should be added
        assert store.collection.count() == 1
    
    def test_add_empty_chunks_list(self, temp_vector_store):
        """Test adding empty list of chunks."""
        store = temp_vector_store
        
        store.add_chunks([])
        
        assert store.collection.count() == 0
    
    def test_query_basic(self, temp_vector_store):
        """Test basic querying of the vector store."""
        store = temp_vector_store
        
        # Add some chunks
        chunks = [
            DocumentChunk(
                content="Machine learning is great",
                metadata={"filename": "ml.txt", "file_type": "text"},
                embedding=[0.5] * 384
            ),
            DocumentChunk(
                content="Deep learning is powerful",
                metadata={"filename": "dl.txt", "file_type": "text"},
                embedding=[0.6] * 384
            ),
            DocumentChunk(
                content="Pizza is delicious",
                metadata={"filename": "food.txt", "file_type": "text"},
                embedding=[0.1] * 384
            )
        ]
        
        store.add_chunks(chunks)
        
        # Query with an embedding similar to the first chunk
        query_embedding = [0.5] * 384
        results = store.query(query_embedding, top_k=2)
        
        assert len(results) <= 2
        assert all(isinstance(r, QueryResult) for r in results)
        assert all(hasattr(r, 'content') for r in results)
        assert all(hasattr(r, 'metadata') for r in results)
        assert all(hasattr(r, 'similarity_score') for r in results)
    
    def test_query_empty_store(self, temp_vector_store):
        """Test querying an empty vector store."""
        store = temp_vector_store
        
        query_embedding = [0.5] * 384
        results = store.query(query_embedding, top_k=5)
        
        assert results == []
    
    def test_query_with_metadata_filter(self, temp_vector_store):
        """Test querying with metadata filters."""
        store = temp_vector_store
        
        # Add chunks with different metadata
        chunks = [
            DocumentChunk(
                content="Costco receipt",
                metadata={
                    "filename": "receipt1.jpg",
                    "file_type": "image",
                    "merchant": "Costco",
                    "date": "2026-02-11"
                },
                embedding=[0.5] * 384
            ),
            DocumentChunk(
                content="Walmart receipt",
                metadata={
                    "filename": "receipt2.jpg",
                    "file_type": "image",
                    "merchant": "Walmart",
                    "date": "2026-02-11"
                },
                embedding=[0.5] * 384
            ),
            DocumentChunk(
                content="Costco receipt different date",
                metadata={
                    "filename": "receipt3.jpg",
                    "file_type": "image",
                    "merchant": "Costco",
                    "date": "2026-02-12"
                },
                embedding=[0.5] * 384
            )
        ]
        
        store.add_chunks(chunks)
        
        # Query with merchant filter
        query_embedding = [0.5] * 384
        results = store.query(
            query_embedding,
            top_k=5,
            metadata_filter={"merchant": "Costco"}
        )
        
        assert len(results) == 2
        assert all(r.metadata.get("merchant") == "Costco" for r in results)
    
    def test_query_with_multiple_filters(self, temp_vector_store):
        """Test querying with multiple metadata filters."""
        store = temp_vector_store
        
        # Add chunks
        chunks = [
            DocumentChunk(
                content="Costco receipt Feb 11",
                metadata={
                    "filename": "receipt1.jpg",
                    "merchant": "Costco",
                    "date": "2026-02-11"
                },
                embedding=[0.5] * 384
            ),
            DocumentChunk(
                content="Costco receipt Feb 12",
                metadata={
                    "filename": "receipt2.jpg",
                    "merchant": "Costco",
                    "date": "2026-02-12"
                },
                embedding=[0.5] * 384
            )
        ]
        
        store.add_chunks(chunks)
        
        # Query with both merchant and date filters
        query_embedding = [0.5] * 384
        results = store.query(
            query_embedding,
            top_k=5,
            metadata_filter={"merchant": "Costco", "date": "2026-02-11"}
        )
        
        assert len(results) == 1
        assert results[0].metadata.get("merchant") == "Costco"
        assert results[0].metadata.get("date") == "2026-02-11"
    
    def test_delete_by_folder(self, temp_vector_store):
        """Test deleting chunks by folder path."""
        store = temp_vector_store
        
        # Add chunks from different folders
        chunks = [
            DocumentChunk(
                content="Doc in folder1",
                metadata={"filename": "doc1.txt", "folder_path": "/folder1"},
                embedding=[0.1] * 384
            ),
            DocumentChunk(
                content="Doc in folder2",
                metadata={"filename": "doc2.txt", "folder_path": "/folder2"},
                embedding=[0.2] * 384
            ),
            DocumentChunk(
                content="Another doc in folder1",
                metadata={"filename": "doc3.txt", "folder_path": "/folder1"},
                embedding=[0.3] * 384
            )
        ]
        
        store.add_chunks(chunks)
        assert store.collection.count() == 3
        
        # Delete folder1
        deleted_count = store.delete_by_folder("/folder1")
        
        assert deleted_count == 2
        assert store.collection.count() == 1
    
    def test_delete_by_nonexistent_folder(self, temp_vector_store):
        """Test deleting chunks from a folder that doesn't exist."""
        store = temp_vector_store
        
        deleted_count = store.delete_by_folder("/nonexistent")
        
        assert deleted_count == 0
    
    def test_get_stats(self, temp_vector_store):
        """Test getting vector store statistics."""
        store = temp_vector_store
        
        # Add some chunks
        chunks = [
            DocumentChunk(
                content=f"Doc {i}",
                metadata={"filename": f"doc{i}.txt"},
                embedding=[0.1] * 384
            )
            for i in range(3)
        ]
        
        store.add_chunks(chunks)
        
        stats = store.get_stats()
        
        assert stats["total_chunks"] == 3
        assert stats["collection_name"] == "documents"
        assert "persist_directory" in stats
    
    def test_reset(self, temp_vector_store):
        """Test resetting the vector store."""
        store = temp_vector_store
        
        # Add some chunks
        chunks = [
            DocumentChunk(
                content="Test doc",
                metadata={"filename": "test.txt"},
                embedding=[0.1] * 384
            )
        ]
        
        store.add_chunks(chunks)
        assert store.collection.count() == 1
        
        # Reset
        store.reset()
        
        assert store.collection.count() == 0
    
    def test_metadata_preparation(self, temp_vector_store):
        """Test that metadata is properly prepared for ChromaDB."""
        store = temp_vector_store
        
        # Test with various metadata types
        chunk = DocumentChunk(
            content="Test",
            metadata={
                "string_field": "value",
                "int_field": 42,
                "float_field": 3.14,
                "bool_field": True,
                "none_field": None,
                "list_field": ["a", "b", "c"]
            },
            embedding=[0.1] * 384
        )
        
        store.add_chunks([chunk])
        
        # Verify it was added successfully
        assert store.collection.count() == 1
    
    def test_singleton_pattern(self, tmp_path):
        """Test that get_vector_store returns the same instance."""
        # Note: This test uses the global singleton, not temp_vector_store
        store1 = get_vector_store()
        store2 = get_vector_store()
        
        assert store1 is store2
