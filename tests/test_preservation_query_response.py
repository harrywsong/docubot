"""
Preservation Property Tests for Query Response Relevance Fix
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import patch
from backend.query_engine import QueryEngine
from backend.models import QueryResult


class TestPreservationProperties:
    def test_preservation_english_query_spending(self):
        with patch('backend.query_engine.get_embedding_engine') as mock_emb:
            with patch('backend.query_engine.get_vector_store') as mock_vs:
                with patch('backend.query_engine.get_llm_generator') as mock_llm:
                    mock_emb.return_value.generate_embedding.return_value = [0.1] * 384
                    mock_llm.return_value.generate_spending_response.return_value = "You spent $127.45 at Costco on 2026-02-11"
                    mock_results = [
                        QueryResult(
                            chunk_id="receipt-1",
                            content="Receipt from Costco",
                            metadata={
                                'filename': 'costco_receipt.jpg',
                                'merchant': 'Costco',
                                'date': '2026-02-11',
                                'total_amount': 127.45
                            },
                            similarity_score=0.92
                        )
                    ]
                    mock_vs.return_value.query.return_value = mock_results
                    engine = QueryEngine()
                    response = engine.query("how much did i spend at costco on feb 11")
                    assert response['aggregated_amount'] == 127.45
    
    def test_preservation_payment_method_extraction(self):
        with patch('backend.query_engine.get_embedding_engine') as mock_emb:
            with patch('backend.query_engine.get_vector_store') as mock_vs:
                with patch('backend.query_engine.get_llm_generator') as mock_llm:
                    mock_emb.return_value.generate_embedding.return_value = [0.1] * 384
                    mock_llm.return_value.generate_general_response.return_value = "You used MasterCard"
                    mock_results = [
                        QueryResult(
                            chunk_id="receipt-1",
                            content="Receipt from Costco. Payment: MasterCard",
                            metadata={
                                'filename': 'costco_receipt.jpg',
                                'merchant': 'Costco',
                                'date': '2026-02-11',
                                'payment_method': 'MasterCard'
                            },
                            similarity_score=0.88
                        )
                    ]
                    mock_vs.return_value.query.return_value = mock_results
                    engine = QueryEngine()
                    response = engine.query("what card did i use?")
                    assert 'MasterCard' in response['answer']
    
    def test_preservation_spending_aggregation_multiple_receipts(self):
        with patch('backend.query_engine.get_embedding_engine') as mock_emb:
            with patch('backend.query_engine.get_vector_store') as mock_vs:
                with patch('backend.query_engine.get_llm_generator') as mock_llm:
                    mock_emb.return_value.generate_embedding.return_value = [0.1] * 384
                    mock_llm.return_value.generate_spending_response.return_value = "You spent $212.75 at Costco in February"
                    mock_results = [
                        QueryResult(
                            chunk_id="receipt-1",
                            content="Receipt from Costco. Total: .45",
                            metadata={
                                'filename': 'costco_receipt_1.jpg',
                                'merchant': 'Costco',
                                'date': '2026-02-11',
                                'total_amount': 127.45
                            },
                            similarity_score=0.92
                        ),
                        QueryResult(
                            chunk_id="receipt-2",
                            content="Receipt from Costco. Total: .30",
                            metadata={
                                'filename': 'costco_receipt_2.jpg',
                                'merchant': 'Costco',
                                'date': '2026-02-15',
                                'total_amount': 85.30
                            },
                            similarity_score=0.89
                        )
                    ]
                    mock_vs.return_value.query.return_value = mock_results
                    engine = QueryEngine()
                    response = engine.query("how much did i spend at costco in february")
                    assert response['aggregated_amount'] == 212.75
                    assert len(response['breakdown']) == 2
    
    def test_preservation_date_filtering_iso_format(self):
        engine = QueryEngine()
        date_result = engine._extract_date("how much did i spend on 2026-02-11")
        assert date_result is not None
        date, is_ambiguous = date_result
        assert date == "2026-02-11"
        assert is_ambiguous == False
    
    def test_preservation_merchant_extraction(self):
        engine = QueryEngine()
        merchant1 = engine._extract_merchant("how much did i spend at costco")
        merchant2 = engine._extract_merchant("receipts from walmart")
        assert merchant1 == "Costco"
        assert merchant2 == "Walmart"
    
    def test_preservation_no_results_helpful_message(self):
        with patch('backend.query_engine.get_embedding_engine') as mock_emb:
            with patch('backend.query_engine.get_vector_store') as mock_vs:
                mock_emb.return_value.generate_embedding.return_value = [0.1] * 384
                mock_vs.return_value.query.return_value = []
                engine = QueryEngine()
                response = engine.query("how much did i spend at nonexistent store")
                assert "couldn't find" in response['answer'].lower()
                assert len(response['sources']) == 0
    
    @given(
        amounts=st.lists(
            st.floats(min_value=0.01, max_value=1000.0, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_property_spending_aggregation_correctness(self, amounts):
        with patch('backend.query_engine.get_embedding_engine') as mock_emb:
            with patch('backend.query_engine.get_vector_store') as mock_vs:
                with patch('backend.query_engine.get_llm_generator') as mock_llm:
                    mock_emb.return_value.generate_embedding.return_value = [0.1] * 384
                    expected_total = sum(amounts)
                    mock_llm.return_value.generate_spending_response.return_value = f"You spent ${expected_total:.2f}"
                    mock_results = []
                    for i, amount in enumerate(amounts):
                        mock_results.append(
                            QueryResult(
                                chunk_id=f"receipt-{i}",
                                content=f"Receipt {i}",
                                metadata={
                                    'filename': f'receipt_{i}.jpg',
                                    'merchant': 'Test Merchant',
                                    'date': f'2026-02-{(i % 28) + 1:02d}',
                                    'total_amount': amount
                                },
                                similarity_score=0.9
                            )
                        )
                    mock_vs.return_value.query.return_value = mock_results
                    engine = QueryEngine()
                    response = engine.query("how much did i spend")
                    actual_total = response['aggregated_amount']
                    assert abs(actual_total - expected_total) < 0.01
                    assert len(response['breakdown']) == len(amounts)
