"""
Test Korean language detection and response generation
"""

import pytest
from unittest.mock import patch, Mock
from backend.query_engine import QueryEngine
from backend.models import QueryResult


class TestKoreanResponse:
    """Test Korean language detection and response generation."""
    
    def test_detect_korean_with_korean_text(self):
        """Test that Korean text is detected correctly."""
        engine = QueryEngine()
        
        assert engine._detect_korean("2월 11일에 코스트코에서 얼마 썼어?") is True
        assert engine._detect_korean("안녕하세요") is True
        assert engine._detect_korean("how much did i spend") is False
        assert engine._detect_korean("hello world") is False
    
    def test_korean_spending_response(self):
        """Test that Korean queries get Korean responses."""
        with patch('backend.query_engine.get_embedding_engine') as mock_emb:
            with patch('backend.query_engine.get_vector_store') as mock_vs:
                mock_emb.return_value.generate_embedding.return_value = [0.1] * 384
                
                # Mock Costco receipt result
                mock_results = [
                    QueryResult(
                        chunk_id="receipt-1",
                        content="Receipt from Costco",
                        metadata={
                            'filename': 'costco_receipt.jpg',
                            'merchant': 'Costco',
                            'date': '2026-02-11',
                            'total_amount': 222.18
                        },
                        similarity_score=0.92
                    )
                ]
                mock_vs.return_value.query.return_value = mock_results
                
                engine = QueryEngine()
                
                # Korean query
                korean_question = "2월 11일에 코스트코에서 얼마 썼어?"
                response = engine.query(korean_question)
                
                # Response should be in Korean
                assert 'Costco' in response['answer']
                assert '2026-02-11' in response['answer']
                assert '222.18' in response['answer']
                # Check for Korean characters in response
                assert engine._detect_korean(response['answer']) is True
                # Should contain Korean spending phrase
                assert '사용하셨습니다' in response['answer'] or '썼습니다' in response['answer']
    
    def test_english_spending_response_unchanged(self):
        """Test that English queries still get English responses."""
        with patch('backend.query_engine.get_embedding_engine') as mock_emb:
            with patch('backend.query_engine.get_vector_store') as mock_vs:
                mock_emb.return_value.generate_embedding.return_value = [0.1] * 384
                
                # Mock Costco receipt result
                mock_results = [
                    QueryResult(
                        chunk_id="receipt-1",
                        content="Receipt from Costco",
                        metadata={
                            'filename': 'costco_receipt.jpg',
                            'merchant': 'Costco',
                            'date': '2026-02-11',
                            'total_amount': 222.18
                        },
                        similarity_score=0.92
                    )
                ]
                mock_vs.return_value.query.return_value = mock_results
                
                engine = QueryEngine()
                
                # English query
                english_question = "how much did i spend at costco on feb 11"
                response = engine.query(english_question)
                
                # Response should be in English
                assert 'Costco' in response['answer']
                assert '2026-02-11' in response['answer']
                assert '222.18' in response['answer']
                # Should NOT contain Korean characters
                assert engine._detect_korean(response['answer']) is False
                # Should contain English spending phrase
                assert 'spent' in response['answer'].lower() or 'used' in response['answer'].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
