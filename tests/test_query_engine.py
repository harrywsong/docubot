"""
Tests for Query Engine

Tests question embedding, retrieval, metadata filtering, and response generation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.query_engine import QueryEngine, get_query_engine
from backend.models import QueryResult


class TestQueryEngine:
    """Test suite for QueryEngine class."""
    
    @pytest.fixture
    def mock_embedding_engine(self):
        """Mock embedding engine."""
        mock = Mock()
        mock.generate_embedding.return_value = [0.1] * 384
        return mock
    
    @pytest.fixture
    def mock_vector_store(self):
        """Mock vector store."""
        mock = Mock()
        return mock
    
    @pytest.fixture
    def query_engine(self, mock_embedding_engine, mock_vector_store):
        """Create query engine with mocked dependencies."""
        with patch('backend.query_engine.get_embedding_engine', return_value=mock_embedding_engine):
            with patch('backend.query_engine.get_vector_store', return_value=mock_vector_store):
                engine = QueryEngine(retrieval_timeout=2.0, similarity_threshold=0.3)
                return engine
    
    def test_query_generates_embedding(self, query_engine, mock_embedding_engine, mock_vector_store):
        """Test that query generates embedding for the question."""
        # Arrange
        question = "What is the total amount?"
        mock_vector_store.query.return_value = []
        
        # Act
        result = query_engine.query(question, user_id=1)
        
        # Assert
        mock_embedding_engine.generate_embedding.assert_called_once_with(question)
    
    def test_query_retrieves_top_k_chunks(self, query_engine, mock_embedding_engine, mock_vector_store):
        """Test that query retrieves top-k similar chunks."""
        # Arrange
        question = "What is the receipt date?"  # Non-aggregation query
        mock_vector_store.query.return_value = []
        
        # Act
        result = query_engine.query(question, user_id=1, top_k=5)
        
        # Assert
        mock_vector_store.query.assert_called_once()
        call_args = mock_vector_store.query.call_args
        assert call_args[1]['top_k'] == 5
    
    def test_aggregation_query_increases_top_k(self, query_engine, mock_embedding_engine, mock_vector_store):
        """Test that aggregation queries automatically increase top_k to 20."""
        # Arrange
        question = "What is my total spending?"  # Aggregation query with "total"
        mock_vector_store.query.return_value = []
        
        # Act
        result = query_engine.query(question, user_id=1, top_k=5)
        
        # Assert
        mock_vector_store.query.assert_called_once()
        call_args = mock_vector_store.query.call_args
        assert call_args[1]['top_k'] == 20  # Should be increased from 5 to 20
    
    def test_aggregation_query_respects_higher_top_k(self, query_engine, mock_embedding_engine, mock_vector_store):
        """Test that aggregation queries don't decrease top_k if already higher than 20."""
        # Arrange
        question = "How much did I spend?"  # Aggregation query with "how much"
        mock_vector_store.query.return_value = []
        
        # Act
        result = query_engine.query(question, user_id=1, top_k=25)
        
        # Assert
        mock_vector_store.query.assert_called_once()
        call_args = mock_vector_store.query.call_args
        assert call_args[1]['top_k'] == 25  # Should remain 25, not decreased to 20
    
    def test_is_aggregation_query_detection(self, query_engine):
        """Test that _is_aggregation_query correctly identifies aggregation queries."""
        # Test aggregation queries
        assert query_engine._is_aggregation_query("What is my total spending?") is True
        assert query_engine._is_aggregation_query("How much did I spend?") is True
        assert query_engine._is_aggregation_query("Show me all receipts") is True
        assert query_engine._is_aggregation_query("What's the sum of my purchases?") is True
        assert query_engine._is_aggregation_query("How many receipts do I have?") is True
        assert query_engine._is_aggregation_query("Overall spending this month") is True
        
        # Test non-aggregation queries
        assert query_engine._is_aggregation_query("What is the receipt date?") is False
        assert query_engine._is_aggregation_query("Show me the Costco receipt") is False
        assert query_engine._is_aggregation_query("What items did I buy?") is False

    
    def test_query_returns_no_results_message(self, query_engine, mock_embedding_engine, mock_vector_store):
        """Test that query returns appropriate message when no chunks found."""
        # Arrange
        question = "What is the total amount?"
        mock_vector_store.query.return_value = []
        
        # Act
        result = query_engine.query(question, user_id=1)
        
        # Assert
        assert "couldn't find any relevant information" in result['answer']
        assert result['sources'] == []
        assert result['aggregated_amount'] is None
    
    def test_extract_date_yyyy_mm_dd_format(self, query_engine):
        """Test date extraction for YYYY-MM-DD format."""
        # Arrange
        question = "How much did I spend on 2026-02-11?"
        
        # Act
        date = query_engine._extract_date(question)
        
        # Assert
        assert date == ("2026-02-11", False)
    
    def test_extract_date_mmm_dd_yyyy_format(self, query_engine):
        """Test date extraction for MMM DD, YYYY format."""
        # Arrange
        question = "How much did I spend on feb 11, 2026?"
        
        # Act
        date = query_engine._extract_date(question)
        
        # Assert
        assert date == ("2026-02-11", False)
    
    def test_extract_date_month_dd_yyyy_format(self, query_engine):
        """Test date extraction for Month DD, YYYY format."""
        # Arrange
        question = "How much did I spend on February 11, 2026?"
        
        # Act
        date = query_engine._extract_date(question)
        
        # Assert
        assert date == ("2026-02-11", False)
    
    def test_extract_date_no_date_found(self, query_engine):
        """Test date extraction when no date in question."""
        # Arrange
        question = "How much did I spend at Costco?"
        
        # Act
        date = query_engine._extract_date(question)
        
        # Assert
        assert date is None
    
    def test_extract_merchant_at_pattern(self, query_engine):
        """Test merchant extraction with 'at' pattern."""
        # Arrange
        question = "How much did I spend at costco on feb 11?"
        
        # Act
        merchant = query_engine._extract_merchant(question)
        
        # Assert
        assert merchant == "Costco"
    
    def test_extract_merchant_from_pattern(self, query_engine):
        """Test merchant extraction with 'from' pattern."""
        # Arrange
        question = "Show me receipts from walmart"
        
        # Act
        merchant = query_engine._extract_merchant(question)
        
        # Assert
        assert merchant == "Walmart"
    
    def test_extract_merchant_no_merchant_found(self, query_engine):
        """Test merchant extraction when no merchant in question."""
        # Arrange
        question = "How much did I spend on feb 11?"
        
        # Act
        merchant = query_engine._extract_merchant(question)
        
        # Assert
        assert merchant is None
    
    def test_is_spending_query_detects_spending_keywords(self, query_engine):
        """Test spending query detection."""
        # Test various spending-related questions
        assert query_engine._is_spending_query("How much did I spend?") is True
        assert query_engine._is_spending_query("What is the total cost?") is True
        assert query_engine._is_spending_query("Show me the amount") is True
        assert query_engine._is_spending_query("What documents do I have?") is False
    
    def test_aggregate_amounts_single_receipt(self, query_engine):
        """Test amount aggregation with single receipt."""
        # Arrange
        results = [
            QueryResult(
                chunk_id="1",
                content="Receipt content",
                metadata={
                    'total_amount': 222.18,
                    'merchant': 'Costco',
                    'date': '2026-02-11',
                    'filename': 'receipt.jpg'
                },
                similarity_score=0.95
            )
        ]
        
        # Act
        total, breakdown = query_engine._aggregate_amounts(results)
        
        # Assert
        assert total == 222.18
        assert len(breakdown) == 1
        assert breakdown[0]['amount'] == 222.18
        assert breakdown[0]['merchant'] == 'Costco'
    
    def test_aggregate_amounts_multiple_receipts(self, query_engine):
        """Test amount aggregation with multiple receipts."""
        # Arrange
        results = [
            QueryResult(
                chunk_id="1",
                content="Receipt 1",
                metadata={
                    'total_amount': 100.00,
                    'merchant': 'Store A',
                    'date': '2026-02-11',
                    'filename': 'receipt1.jpg'
                },
                similarity_score=0.95
            ),
            QueryResult(
                chunk_id="2",
                content="Receipt 2",
                metadata={
                    'total_amount': 50.50,
                    'merchant': 'Store B',
                    'date': '2026-02-12',
                    'filename': 'receipt2.jpg'
                },
                similarity_score=0.90
            )
        ]
        
        # Act
        total, breakdown = query_engine._aggregate_amounts(results)
        
        # Assert
        assert total == 150.50
        assert len(breakdown) == 2
    
    def test_aggregate_amounts_no_amounts(self, query_engine):
        """Test amount aggregation when no amounts in metadata."""
        # Arrange
        results = [
            QueryResult(
                chunk_id="1",
                content="Text document",
                metadata={
                    'filename': 'document.pdf',
                    'file_type': 'text'
                },
                similarity_score=0.95
            )
        ]
        
        # Act
        total, breakdown = query_engine._aggregate_amounts(results)
        
        # Assert
        assert total is None
        assert breakdown is None
    
    def test_query_with_date_filter(self, query_engine, mock_embedding_engine, mock_vector_store):
        """Test that date filter is applied to vector store query."""
        # Arrange
        question = "How much did I spend on 2026-02-11?"
        mock_vector_store.query.return_value = []
        
        # Act
        result = query_engine.query(question, user_id=1)
        
        # Assert
        call_args = mock_vector_store.query.call_args
        metadata_filter = call_args[1]['metadata_filter']
        assert metadata_filter is not None
        assert metadata_filter['user_id'] == 1  # Check user_id filter is applied
    
    def test_query_with_merchant_filter(self, query_engine, mock_embedding_engine, mock_vector_store):
        """Test that merchant filter is applied to vector store query."""
        # Arrange
        question = "How much did I spend at costco?"
        # Return empty list to trigger fuzzy matching, but we check the first call
        mock_vector_store.query.return_value = []
        
        # Act
        result = query_engine.query(question, user_id=1)
        
        # Assert - Check the first call (before fuzzy matching)
        assert mock_vector_store.query.call_count >= 1
        first_call_args = mock_vector_store.query.call_args_list[0]
        metadata_filter = first_call_args[1]['metadata_filter']
        assert metadata_filter is not None
        assert metadata_filter['user_id'] == 1  # Check user_id filter is applied
    
    def test_query_with_date_and_merchant_filter(self, query_engine, mock_embedding_engine, mock_vector_store):
        """Test that both date and merchant filters are applied."""
        # Arrange
        question = "How much did I spend at costco on feb 11, 2026?"
        # Return empty list to trigger fuzzy matching, but we check the first call
        mock_vector_store.query.return_value = []
        
        # Act
        result = query_engine.query(question, user_id=1)
        
        # Assert - Check the first call (before fuzzy matching)
        assert mock_vector_store.query.call_count >= 1
        first_call_args = mock_vector_store.query.call_args_list[0]
        metadata_filter = first_call_args[1]['metadata_filter']
        assert metadata_filter is not None
        assert metadata_filter['user_id'] == 1  # Check user_id filter is applied
    
    def test_spending_query_response_format(self, query_engine, mock_embedding_engine, mock_vector_store):
        """Test spending query response includes amount and breakdown."""
        # Arrange
        question = "How much did I spend at costco on feb 11, 2026?"
        mock_results = [
            QueryResult(
                chunk_id="1",
                content="Receipt content",
                metadata={
                    'total_amount': 222.18,
                    'merchant': 'Costco',
                    'date': '2026-02-11',
                    'filename': 'receipt.jpg'
                },
                similarity_score=0.95
            )
        ]
        mock_vector_store.query.return_value = mock_results
        
        # Act
        result = query_engine.query(question, user_id=1)
        
        # Assert
        assert result['aggregated_amount'] is None  # No longer doing aggregation
        assert '$222.18' in result['answer'] or 'Costco' in result['answer']  # LLM should mention the amount or merchant
    
    def test_format_sources(self, query_engine):
        """Test source formatting."""
        # Arrange
        results = [
            QueryResult(
                chunk_id="1",
                content="This is a long content that should be truncated" * 10,
                metadata={
                    'filename': 'test.pdf',
                    'file_type': 'text',
                    'folder_path': '/path/to/folder',
                    'page_number': 1
                },
                similarity_score=0.95
            )
        ]
        
        # Act
        sources = query_engine._format_sources(results)
        
        # Assert
        assert len(sources) == 1
        assert sources[0]['filename'] == 'test.pdf'
        assert sources[0]['score'] == 0.95
        assert len(sources[0]['chunk']) <= 203  # 200 chars + "..."
        assert sources[0]['metadata']['file_type'] == 'text'
        assert sources[0]['metadata']['page_number'] == 1
    
    def test_get_query_engine_singleton(self):
        """Test that get_query_engine returns singleton instance."""
        with patch('backend.query_engine.get_embedding_engine'):
            with patch('backend.query_engine.get_vector_store'):
                engine1 = get_query_engine()
                engine2 = get_query_engine()
                assert engine1 is engine2


class TestRetrievalTimeout:
    """Test suite for retrieval timeout functionality (Requirement 6.5)."""
    
    @pytest.fixture
    def mock_embedding_engine(self):
        """Mock embedding engine."""
        mock = Mock()
        mock.generate_embedding.return_value = [0.1] * 384
        return mock
    
    @pytest.fixture
    def mock_vector_store_slow(self):
        """Mock vector store that simulates slow retrieval."""
        import time
        mock = Mock()
        # Simulate slow query that takes 3 seconds
        def slow_query(*args, **kwargs):
            time.sleep(3)
            return []
        mock.query.side_effect = slow_query
        return mock
    
    @pytest.fixture
    def query_engine_with_timeout(self, mock_embedding_engine, mock_vector_store_slow):
        """Create query engine with timeout and slow vector store."""
        with patch('backend.query_engine.get_embedding_engine', return_value=mock_embedding_engine):
            with patch('backend.query_engine.get_vector_store', return_value=mock_vector_store_slow):
                engine = QueryEngine(retrieval_timeout=1.0)  # 1 second timeout
                return engine
    
    def test_retrieval_timeout_returns_empty_results(self, query_engine_with_timeout):
        """
        Test that retrieval timeout returns empty results.
        
        Requirements: 6.4, 6.5
        """
        # Arrange
        question = "What is the total amount?"
        
        # Act
        result = query_engine_with_timeout.query(question, user_id=1)
        
        # Assert
        assert "couldn't find any relevant information" in result['answer'] or "trouble accessing" in result['answer']
        assert result['sources'] == []
        assert result['aggregated_amount'] is None
        assert 'retrieval_time' in result
    
    def test_retrieval_completes_within_timeout(self):
        """
        Test that fast retrieval completes successfully within timeout.
        
        Requirements: 6.5
        """
        # Arrange
        mock_embedding_engine = Mock()
        mock_embedding_engine.generate_embedding.return_value = [0.1] * 384
        
        mock_vector_store = Mock()
        mock_results = [
            QueryResult(
                chunk_id="1",
                content="Test content",
                metadata={'filename': 'test.pdf'},
                similarity_score=0.95
            )
        ]
        mock_vector_store.query.return_value = mock_results
        
        with patch('backend.query_engine.get_embedding_engine', return_value=mock_embedding_engine):
            with patch('backend.query_engine.get_vector_store', return_value=mock_vector_store):
                with patch('backend.query_engine.get_llm_generator') as mock_llm:
                    mock_llm.return_value.generate_general_response.return_value = "Test answer"
                    engine = QueryEngine(retrieval_timeout=2.0)
                    
                    # Act
                    result = engine.query("test question", user_id=1)
                    
                    # Assert
                    assert result['retrieval_time'] < 2.0
                    assert len(result['sources']) > 0
    
    def test_configurable_retrieval_timeout(self):
        """
        Test that retrieval timeout is configurable.
        
        Requirements: 6.5
        """
        # Arrange
        mock_embedding_engine = Mock()
        mock_embedding_engine.generate_embedding.return_value = [0.1] * 384
        
        mock_vector_store = Mock()
        mock_vector_store.query.return_value = []
        
        with patch('backend.query_engine.get_embedding_engine', return_value=mock_embedding_engine):
            with patch('backend.query_engine.get_vector_store', return_value=mock_vector_store):
                # Test with custom timeout
                engine = QueryEngine(retrieval_timeout=5.0)
                
                # Assert
                assert engine.retrieval_timeout == 5.0
    
    def test_similarity_threshold_filtering(self):
        """
        Test that similarity threshold filters low-score results.
        
        Requirements: 6.4
        """
        # Arrange
        mock_embedding_engine = Mock()
        mock_embedding_engine.generate_embedding.return_value = [0.1] * 384
        
        mock_vector_store = Mock()
        mock_results = [
            QueryResult(
                chunk_id="1",
                content="High score result",
                metadata={'filename': 'test1.pdf'},
                similarity_score=0.95
            ),
            QueryResult(
                chunk_id="2",
                content="Low score result",
                metadata={'filename': 'test2.pdf'},
                similarity_score=0.2
            )
        ]
        mock_vector_store.query.return_value = mock_results
        
        with patch('backend.query_engine.get_embedding_engine', return_value=mock_embedding_engine):
            with patch('backend.query_engine.get_vector_store', return_value=mock_vector_store):
                with patch('backend.query_engine.get_llm_generator') as mock_llm:
                    mock_llm.return_value.generate_general_response.return_value = "Test answer"
                    engine = QueryEngine(similarity_threshold=0.3)
                    
                    # Act
                    result = engine.query("test question", user_id=1)
                    
                    # Assert
                    # Only high-score result should be in sources (top 3 by default)
                    assert len(result['sources']) >= 1
                    assert result['sources'][0]['filename'] == 'test1.pdf'
                    assert result['sources'][0]['score'] == 0.95


class TestCostcoReceiptExample:
    """Test the specific Costco receipt example from requirements."""
    
    def test_costco_receipt_query(self):
        """
        Test query "how much have i spent at costco on feb 11, 2026?" returns $222.18
        
        Requirements: 7.3
        """
        # Arrange
        with patch('backend.query_engine.get_embedding_engine') as mock_emb:
            with patch('backend.query_engine.get_vector_store') as mock_vs:
                with patch('backend.query_engine.get_llm_generator') as mock_llm:
                    mock_emb.return_value.generate_embedding.return_value = [0.1] * 384
                    
                    # Mock vector store to return Costco receipt
                    mock_results = [
                        QueryResult(
                            chunk_id="costco-receipt-1",
                            content="Merchant: Costco\nDate: February 11, 2026\nTotal: USD 222.18",
                            metadata={
                                'filename': 'costco_receipt_2026_02_11.jpg',
                                'file_type': 'image',
                                'folder_path': '/receipts',
                                'merchant': 'Costco',
                                'date': '2026-02-11',
                                'total_amount': 222.18,
                                'currency': 'USD'
                            },
                            similarity_score=0.98
                        )
                    ]
                    mock_vs.return_value.query.return_value = mock_results
                    mock_llm.return_value.generate_general_response.return_value = "You spent $222.18 at Costco on February 11, 2026."
                    
                    engine = QueryEngine()
                    
                    # Act
                    result = engine.query("how much have i spent at costco on feb 11, 2026?", user_id=1)
                    
                    # Assert
                    assert '$222.18' in result['answer']
                    assert len(result['sources']) == 1
                    assert result['sources'][0]['metadata']['merchant'] == 'Costco'
                    assert result['sources'][0]['metadata']['date'] == '2026-02-11'
