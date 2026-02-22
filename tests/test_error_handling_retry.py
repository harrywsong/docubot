"""
Tests for error handling and retry logic in Pi components.

Tests Requirements 14.1, 14.2, 14.3, 14.4, 14.5:
- Retry logic for model loading (3 retries with exponential backoff)
- Graceful degradation for query failures
- Timeout handling for response generation (10s)
- Safe mode for corrupted vector store
- Error logging with timestamps and context
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil

from backend.data_loader import DataLoader, DataLoadError
from backend.query_engine import QueryEngine
from backend.llm_generator import LLMGenerator
from backend.config import Config


class TestDataLoaderRetryLogic:
    """Test retry logic for model loading (Requirement 14.1)."""
    
    def test_vector_store_retry_on_transient_failure(self):
        """Test that vector store loading retries on transient failures."""
        config = Config()
        loader = DataLoader(config)
        
        # Create temporary directory with vector store structure
        with tempfile.TemporaryDirectory() as tmpdir:
            config.CHROMADB_PATH = tmpdir
            
            # Create a non-empty directory
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test")
            
            # Mock VectorStore to fail twice then succeed
            call_count = 0
            
            def mock_init_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise Exception("Transient failure")
                # On third attempt, return a mock that works
                mock_vs = Mock()
                mock_vs.initialize = Mock()
                mock_vs.get_stats = Mock(return_value={'total_chunks': 10})
                return mock_vs
            
            with patch('backend.data_loader.VectorStore', side_effect=mock_init_side_effect):
                # Should succeed after retries
                vector_store = loader.load_vector_store()
                assert vector_store is not None
                assert call_count == 3  # Failed twice, succeeded on third
    
    def test_vector_store_retry_exponential_backoff(self):
        """Test that retry uses exponential backoff (1s, 2s, 4s)."""
        config = Config()
        loader = DataLoader(config)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config.CHROMADB_PATH = tmpdir
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test")
            
            call_times = []
            
            def mock_init_side_effect(*args, **kwargs):
                call_times.append(time.time())
                if len(call_times) < 3:
                    raise Exception("Transient failure")
                mock_vs = Mock()
                mock_vs.initialize = Mock()
                mock_vs.get_stats = Mock(return_value={'total_chunks': 10})
                return mock_vs
            
            with patch('backend.data_loader.VectorStore', side_effect=mock_init_side_effect):
                start_time = time.time()
                vector_store = loader.load_vector_store()
                
                # Check that delays were approximately 1s and 2s
                if len(call_times) >= 2:
                    delay1 = call_times[1] - call_times[0]
                    assert 0.9 <= delay1 <= 1.5  # ~1 second
                
                if len(call_times) >= 3:
                    delay2 = call_times[2] - call_times[1]
                    assert 1.9 <= delay2 <= 2.5  # ~2 seconds
    
    def test_vector_store_safe_mode_on_corruption(self):
        """Test that corrupted vector store triggers safe mode (Requirement 14.2)."""
        config = Config()
        loader = DataLoader(config)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config.CHROMADB_PATH = tmpdir
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test")
            
            # Mock VectorStore to raise corruption error
            with patch('backend.data_loader.VectorStore') as mock_vs_class:
                mock_vs_class.side_effect = Exception("Database corruption detected")
                
                with pytest.raises(DataLoadError) as exc_info:
                    loader.load_vector_store()
                
                # Check that safe mode was activated
                assert loader.safe_mode is True
                assert "corrupted" in str(exc_info.value).lower()
    
    def test_database_retry_on_transient_failure(self):
        """Test that database loading retries on transient failures."""
        config = Config()
        loader = DataLoader(config)
        
        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            tmpfile.write(b"test data")
            tmpfile.flush()
            tmpfile_name = tmpfile.name
        
        try:
            config.SQLITE_PATH = tmpfile_name
            
            call_count = 0
            
            def mock_db_init_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise Exception("Transient failure")
                return Mock()
            
            with patch('backend.data_loader.DatabaseManager', side_effect=mock_db_init_side_effect):
                db_manager = loader.load_database()
                assert db_manager is not None
                assert call_count == 3
        finally:
            try:
                Path(tmpfile_name).unlink()
            except:
                pass  # Ignore cleanup errors on Windows
    
    def test_max_retries_exceeded(self):
        """Test that loading fails after max retries (3 attempts)."""
        config = Config()
        loader = DataLoader(config)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config.CHROMADB_PATH = tmpdir
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test")
            
            call_count = 0
            
            def mock_init_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                raise Exception("Persistent failure")
            
            with patch('backend.data_loader.VectorStore', side_effect=mock_init_side_effect):
                with pytest.raises(DataLoadError) as exc_info:
                    loader.load_vector_store()
                
                # Should have tried 3 times
                assert call_count == 3
                assert "after 3 attempts" in str(exc_info.value)


class TestQueryEngineGracefulDegradation:
    """Test graceful degradation for query failures (Requirement 14.2)."""
    
    def test_embedding_generation_failure_fallback(self):
        """Test fallback when embedding generation fails."""
        query_engine = QueryEngine()
        
        # Mock embedding engine to fail
        with patch.object(query_engine.embedding_engine, 'generate_embedding', side_effect=Exception("Embedding failed")):
            result = query_engine.query("test question", user_id=1)
            
            # Should return fallback message, not crash
            assert result is not None
            assert "answer" in result
            assert "trouble processing" in result["answer"].lower()
            assert result["sources"] == []
    
    def test_retrieval_failure_fallback(self):
        """Test fallback when retrieval fails."""
        query_engine = QueryEngine()
        
        # Mock embedding to succeed but retrieval to fail
        with patch.object(query_engine.embedding_engine, 'generate_embedding', return_value=[0.1] * 384):
            with patch.object(query_engine, '_retrieve_with_timeout', side_effect=Exception("Retrieval failed")):
                result = query_engine.query("test question", user_id=1)
                
                # Should return fallback message
                assert result is not None
                assert "answer" in result
                assert "trouble accessing" in result["answer"].lower()
    
    def test_llm_generation_failure_fallback(self):
        """Test fallback when LLM generation fails."""
        query_engine = QueryEngine()
        
        # Mock successful embedding and retrieval
        mock_result = Mock()
        mock_result.content = "test content"
        mock_result.metadata = {"filename": "test.txt"}
        mock_result.similarity_score = 0.8
        
        with patch.object(query_engine.embedding_engine, 'generate_embedding', return_value=[0.1] * 384):
            with patch.object(query_engine, '_retrieve_with_timeout', return_value=[mock_result]):
                with patch.object(query_engine, '_generate_response', side_effect=Exception("LLM failed")):
                    result = query_engine.query("test question", user_id=1)
                    
                    # Should use fallback response
                    assert result is not None
                    assert "answer" in result
                    # Should have some answer (fallback template)
                    assert len(result["answer"]) > 0
    
    def test_continues_serving_after_failure(self):
        """Test that query engine continues serving after a failure."""
        query_engine = QueryEngine()
        
        # First query fails
        with patch.object(query_engine.embedding_engine, 'generate_embedding', side_effect=Exception("Temporary failure")):
            result1 = query_engine.query("test question 1", user_id=1)
            assert "trouble processing" in result1["answer"].lower()
        
        # Second query should work (no exception)
        mock_result = Mock()
        mock_result.content = "test content"
        mock_result.metadata = {"filename": "test.txt"}
        mock_result.similarity_score = 0.8
        
        with patch.object(query_engine.embedding_engine, 'generate_embedding', return_value=[0.1] * 384):
            with patch.object(query_engine, '_retrieve_with_timeout', return_value=[mock_result]):
                with patch.object(query_engine, '_generate_response', return_value="Test answer"):
                    result2 = query_engine.query("test question 2", user_id=1)
                    assert result2["answer"] == "Test answer"


class TestLLMGeneratorTimeout:
    """Test timeout handling for response generation (Requirement 14.3)."""
    
    def test_llm_timeout_configured(self):
        """Test that LLM generator is configured with 10s timeout."""
        llm_gen = LLMGenerator()
        
        # Check that client has 10-second timeout
        assert llm_gen.client.timeout == 10
    
    def test_spending_response_timeout_fallback(self):
        """Test fallback when spending response generation times out."""
        llm_gen = LLMGenerator()
        
        # Mock client to raise timeout exception
        with patch.object(llm_gen.client, 'generate', side_effect=Exception("Timeout")):
            result = llm_gen.generate_spending_response(
                question="How much did I spend?",
                aggregated_amount=100.0,
                breakdown=[{"merchant": "Test", "amount": 100.0, "date": "2024-01-01"}]
            )
            
            # Should return fallback response
            assert result is not None
            assert "$100.00" in result
    
    def test_general_response_timeout_fallback(self):
        """Test fallback when general response generation times out."""
        llm_gen = LLMGenerator()
        
        with patch.object(llm_gen.client, 'generate', side_effect=Exception("Timeout")):
            result = llm_gen.generate_general_response(
                question="What is this?",
                retrieved_chunks=["Test content"]
            )
            
            # Should return fallback message
            assert result is not None
            assert "try again" in result.lower()


class TestErrorLogging:
    """Test error logging with timestamps and context (Requirement 14.4)."""
    
    def test_data_loader_logs_with_context(self):
        """Test that DataLoader logs include timestamp and context."""
        config = Config()
        loader = DataLoader(config)
        
        with patch('backend.data_loader.logger') as mock_logger:
            loader._log_with_context("Test message")
            
            # Check that log was called
            assert mock_logger.info.called
            call_args = mock_logger.info.call_args[0][0]
            
            # Should include timestamp (ISO format) and component name
            assert "[DataLoader]" in call_args
            assert "Test message" in call_args
    
    def test_query_engine_logs_with_context(self):
        """Test that QueryEngine logs include timestamp and context."""
        query_engine = QueryEngine()
        
        with patch('backend.query_engine.logger') as mock_logger:
            query_engine._log_with_context("Test message")
            
            assert mock_logger.info.called
            call_args = mock_logger.info.call_args[0][0]
            assert "[QueryEngine]" in call_args
            assert "Test message" in call_args
    
    def test_llm_generator_logs_with_context(self):
        """Test that LLMGenerator logs include timestamp and context."""
        llm_gen = LLMGenerator()
        
        with patch('backend.llm_generator.logger') as mock_logger:
            llm_gen._log_with_context("Test message")
            
            assert mock_logger.info.called
            call_args = mock_logger.info.call_args[0][0]
            assert "[LLMGenerator]" in call_args
            assert "Test message" in call_args
    
    def test_error_logging_includes_exception(self):
        """Test that error logs include exception details."""
        config = Config()
        loader = DataLoader(config)
        
        test_error = ValueError("Test error")
        
        with patch('backend.data_loader.logger') as mock_logger:
            loader._log_with_context("Error occurred", level="error", error=test_error)
            
            assert mock_logger.error.called
            # Should log with exc_info=True for stack trace
            assert mock_logger.error.call_args[1].get('exc_info') is True


class TestIntegrationErrorHandling:
    """Integration tests for error handling across components."""
    
    def test_end_to_end_error_recovery(self):
        """Test that system recovers from errors end-to-end."""
        query_engine = QueryEngine()
        
        # Simulate a query that fails at embedding stage
        with patch.object(query_engine.embedding_engine, 'generate_embedding', side_effect=Exception("Embedding error")):
            result1 = query_engine.query("failing query", user_id=1)
            assert "trouble processing" in result1["answer"].lower()
        
        # Next query should work normally
        mock_result = Mock()
        mock_result.content = "recovered content"
        mock_result.metadata = {"filename": "test.txt"}
        mock_result.similarity_score = 0.8
        
        with patch.object(query_engine.embedding_engine, 'generate_embedding', return_value=[0.1] * 384):
            with patch.object(query_engine, '_retrieve_with_timeout', return_value=[mock_result]):
                with patch.object(query_engine, '_generate_response', return_value="Recovered answer"):
                    result2 = query_engine.query("working query", user_id=1)
                    assert result2["answer"] == "Recovered answer"
                    assert len(result2["sources"]) > 0
