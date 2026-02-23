"""
Unit tests for metadata filter extraction in QueryEngine.

Tests the _extract_metadata_filters method to ensure it correctly
extracts store names from natural language queries and returns
ChromaDB-compatible filter dictionaries.
"""

import pytest
from backend.query_engine import QueryEngine


class TestMetadataFilterExtraction:
    """Test suite for _extract_metadata_filters method."""
    
    @pytest.fixture
    def query_engine(self):
        """Create a QueryEngine instance for testing."""
        return QueryEngine()
    
    def test_extract_store_with_at_pattern(self, query_engine):
        """Test extraction of store name using 'at <store>' pattern."""
        query = "How much did I spend at Costco?"
        filters = query_engine._extract_metadata_filters(query)
        
        assert filters is not None
        assert 'store' in filters
        assert filters['store'] == {'$eq': 'Costco'}
    
    def test_extract_store_with_from_pattern(self, query_engine):
        """Test extraction of store name using 'from <store>' pattern."""
        query = "Show me receipts from Walmart"
        filters = query_engine._extract_metadata_filters(query)
        
        assert filters is not None
        assert 'store' in filters
        assert filters['store'] == {'$eq': 'Walmart'}
    
    def test_extract_store_with_receipts_pattern(self, query_engine):
        """Test extraction of store name using '<store> receipts' pattern."""
        query = "Find all Target receipts"
        filters = query_engine._extract_metadata_filters(query)
        
        assert filters is not None
        assert 'store' in filters
        assert filters['store'] == {'$eq': 'Target'}
    
    def test_extract_store_with_in_pattern(self, query_engine):
        """Test extraction of store name using 'in <store>' pattern."""
        query = "What did I buy in Safeway?"
        filters = query_engine._extract_metadata_filters(query)
        
        assert filters is not None
        assert 'store' in filters
        assert filters['store'] == {'$eq': 'Safeway'}
    
    def test_extract_store_with_ampersand(self, query_engine):
        """Test extraction of store name with ampersand."""
        query = "Show me purchases at Bed & Bath"
        filters = query_engine._extract_metadata_filters(query)
        
        assert filters is not None
        assert 'store' in filters
        assert filters['store'] == {'$eq': 'Bed & Bath'}
    
    def test_extract_store_with_multiple_words(self, query_engine):
        """Test extraction of multi-word store names."""
        query = "How much did I spend at Trader Joes?"
        filters = query_engine._extract_metadata_filters(query)
        
        assert filters is not None
        assert 'store' in filters
        assert filters['store'] == {'$eq': 'Trader Joes'}
    
    def test_no_store_in_general_query(self, query_engine):
        """Test that general queries without store names return None."""
        query = "What did I buy last week?"
        filters = query_engine._extract_metadata_filters(query)
        
        assert filters is None
    
    def test_no_store_in_semantic_query(self, query_engine):
        """Test that semantic queries without store names return None."""
        query = "Show me all my receipts"
        filters = query_engine._extract_metadata_filters(query)
        
        assert filters is None
    
    def test_store_name_normalization(self, query_engine):
        """Test that store names are properly normalized (whitespace stripped)."""
        query = "How much did I spend at  Costco  ?"
        filters = query_engine._extract_metadata_filters(query)
        
        assert filters is not None
        assert 'store' in filters
        assert filters['store'] == {'$eq': 'Costco'}
    
    def test_extract_store_with_purchases_pattern(self, query_engine):
        """Test extraction of store name using '<store> purchases' pattern."""
        query = "Show me all Amazon purchases"
        filters = query_engine._extract_metadata_filters(query)
        
        assert filters is not None
        assert 'store' in filters
        assert filters['store'] == {'$eq': 'Amazon'}
    
    def test_extract_store_with_transactions_pattern(self, query_engine):
        """Test extraction of store name using '<store> transactions' pattern."""
        query = "Show me Costco transactions"
        filters = query_engine._extract_metadata_filters(query)
        
        assert filters is not None
        assert 'store' in filters
        assert filters['store'] == {'$eq': 'Costco'}
