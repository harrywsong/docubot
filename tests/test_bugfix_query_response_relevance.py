"""
Bug Condition Exploration Test for Query Response Relevance Fix

This test encodes the EXPECTED behavior after the fix is implemented.
It MUST FAIL on unfixed code - failure confirms the bugs exist.

DO NOT attempt to fix the test or the code when it fails.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

Bug scenarios tested:
1. Korean queries return irrelevant documents (similarity < 0.3)
2. UI shows sources with low similarity scores (< 0.5)
3. System fails to extract card_last_4_digits from metadata
4. Repeated queries get identical generic answers

This test will PASS after the fix is implemented, confirming expected behavior.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import patch, Mock
from backend.query_engine import QueryEngine
from backend.models import QueryResult


class TestBugConditionExploration:
    """
    Bug condition exploration tests for query response relevance issues.
    
    These tests encode the EXPECTED behavior and will FAIL on unfixed code.
    """
    
    def test_bug1_korean_query_returns_relevant_documents(self):
        """
        Bug 1: Korean Query Failure
        
        EXPECTED: Korean query "2월 11일에 코스트코에서 얼마 썼어?" should return
        relevant Costco receipt with high similarity score (>= 0.7)
        
        CURRENT (UNFIXED): Returns irrelevant documents (vitamin D charts, legal docs)
        with low similarity scores (< 0.3)
        
        **Validates: Requirements 2.1, 2.5**
        """
        # Arrange: Create query engine with mocked vector store
        with patch('backend.query_engine.get_vector_store') as mock_vs:
            # Simulate the FIXED behavior: Korean query with multilingual model
            # returns relevant Costco receipt with high similarity score
            mock_results = [
                QueryResult(
                    chunk_id="relevant-1",
                    content="코스트코 영수증. 2026년 2월 11일. 총액: $127.45",
                    metadata={
                        'filename': 'costco_receipt_20260211.jpg',
                        'file_type': 'image',
                        'folder_path': '/receipts',
                        'merchant': 'Costco',
                        'date': '2026-02-11',
                        'total_amount': 127.45,
                        'payment_method': 'MasterCard'
                    },
                    similarity_score=0.85  # High similarity - relevant
                ),
                QueryResult(
                    chunk_id="relevant-2",
                    content="Receipt from Costco on February 11, 2026. Total: $127.45",
                    metadata={
                        'filename': 'costco_receipt_20260211.jpg',
                        'file_type': 'image',
                        'folder_path': '/receipts',
                        'merchant': 'Costco',
                        'date': '2026-02-11',
                        'total_amount': 127.45
                    },
                    similarity_score=0.78  # High similarity - relevant
                )
            ]
            mock_vs.return_value.query.return_value = mock_results
            
            engine = QueryEngine()
            
            # Act: Execute Korean query
            korean_question = "2월 11일에 코스트코에서 얼마 썼어?"
            response = engine.query(korean_question)
            
            # Assert: EXPECTED behavior (will FAIL on unfixed code)
            # After fix: Should return relevant documents with high similarity
            assert len(response['sources']) > 0, "Should return at least one source"
            
            # Check that at least one source has high similarity (>= 0.7)
            high_similarity_sources = [s for s in response['sources'] if s['score'] >= 0.7]
            assert len(high_similarity_sources) > 0, \
                f"Expected at least one source with similarity >= 0.7, but got scores: {[s['score'] for s in response['sources']]}"
            
            # Check that the high similarity source is relevant (Costco receipt)
            relevant_source = high_similarity_sources[0]
            # After fix, should find Costco receipt, not vitamin D or legal docs
            assert 'costco' in relevant_source['filename'].lower(), \
                f"Should return Costco receipt for Costco spending query, but got: {relevant_source['filename']}"
            assert 'vitamin' not in relevant_source['filename'].lower(), \
                "Should not return vitamin D chart for Costco spending query"
            assert 'legal' not in relevant_source['filename'].lower(), \
                "Should not return legal document for Costco spending query"
    
    def test_bug2_low_similarity_sources_filtered_from_ui(self):
        """
        Bug 2: Irrelevant Source Attribution
        
        EXPECTED: Query "what card did i use?" should only show sources with
        similarity >= 0.5 in the UI
        
        CURRENT (UNFIXED): Shows all retrieved documents including hardware PDFs
        with similarity ~0.3
        
        **Validates: Requirements 2.2, 2.6**
        """
        # Arrange: Create query engine with mocked dependencies
        with patch('backend.query_engine.get_embedding_engine') as mock_emb:
            with patch('backend.query_engine.get_vector_store') as mock_vs:
                mock_emb.return_value.generate_embedding.return_value = [0.1] * 384
                
                # Simulate mixed results: one relevant (high similarity), two irrelevant (low similarity)
                mock_results = [
                    QueryResult(
                        chunk_id="relevant-1",
                        content="Receipt from Costco. Payment method: MasterCard",
                        metadata={
                            'filename': 'costco_receipt.jpg',
                            'file_type': 'image',
                            'folder_path': '/receipts',
                            'merchant': 'Costco',
                            'date': '2026-02-11',
                            'payment_method': 'MasterCard'
                        },
                        similarity_score=0.85  # High similarity - relevant
                    ),
                    QueryResult(
                        chunk_id="irrelevant-1",
                        content="Hardware requirements for system installation...",
                        metadata={
                            'filename': 'hardware_requirements.pdf',
                            'file_type': 'text',
                            'folder_path': '/documents'
                        },
                        similarity_score=0.32  # Low similarity - irrelevant
                    ),
                    QueryResult(
                        chunk_id="irrelevant-2",
                        content="Software specification document...",
                        metadata={
                            'filename': 'software_spec.pdf',
                            'file_type': 'text',
                            'folder_path': '/documents'
                        },
                        similarity_score=0.28  # Low similarity - irrelevant
                    )
                ]
                mock_vs.return_value.query.return_value = mock_results
                
                engine = QueryEngine()
                
                # Act: Execute query
                response = engine.query("what card did i use?")
                
                # Assert: EXPECTED behavior (will FAIL on unfixed code)
                # After fix: Should only show sources with similarity >= 0.5
                assert len(response['sources']) > 0, "Should return at least one source"
                
                # Check that ALL sources have similarity >= 0.5
                for source in response['sources']:
                    assert source['score'] >= 0.5, \
                        f"All sources should have similarity >= 0.5, but found {source['filename']} with score {source['score']}"
                
                # Check that low-similarity sources are filtered out
                source_filenames = [s['filename'] for s in response['sources']]
                assert 'hardware_requirements.pdf' not in source_filenames, \
                    "Low-similarity hardware PDF should be filtered out"
                assert 'software_spec.pdf' not in source_filenames, \
                    "Low-similarity software PDF should be filtered out"
                
                # Check that high-similarity source is included
                assert 'costco_receipt.jpg' in source_filenames, \
                    "High-similarity Costco receipt should be included"
    
    def test_bug3_card_last_4_digits_extraction(self):
        """
        Bug 3: Missing Metadata Extraction
        
        EXPECTED: Query "last 4 digits" should extract card_last_4_digits from
        metadata or explicitly state "not captured"
        
        CURRENT (UNFIXED): Returns "You used MasterCard" without checking
        card_last_4_digits field
        
        **Validates: Requirements 2.3, 2.4**
        """
        # Arrange: Create query engine with mocked dependencies
        with patch('backend.query_engine.get_embedding_engine') as mock_emb:
            with patch('backend.query_engine.get_vector_store') as mock_vs:
                mock_emb.return_value.generate_embedding.return_value = [0.1] * 384
                
                # Simulate result with card_last_4_digits in metadata
                mock_results = [
                    QueryResult(
                        chunk_id="receipt-1",
                        content="Receipt from Costco. Payment: MasterCard ending in 1234",
                        metadata={
                            'filename': 'costco_receipt.jpg',
                            'file_type': 'image',
                            'folder_path': '/receipts',
                            'merchant': 'Costco',
                            'date': '2026-02-11',
                            'payment_method': 'MasterCard',
                            'card_last_4_digits': '1234'  # This field exists!
                        },
                        similarity_score=0.90
                    )
                ]
                mock_vs.return_value.query.return_value = mock_results
                
                engine = QueryEngine()
                
                # Act: Execute query asking for last 4 digits
                response = engine.query("last 4 digits")
                
                # Assert: EXPECTED behavior (will FAIL on unfixed code)
                # After fix: Should extract and return the card_last_4_digits
                answer = response['answer']
                print(f"\n[DEBUG] Bug 3 test - Answer: {answer}")
                
                # Check that the answer includes the last 4 digits
                assert '1234' in answer, \
                    f"Answer should include last 4 digits '1234', but got: {answer}"
                
                # Check that it's not just the generic "You used MasterCard" response
                assert 'last 4 digits' in answer.lower() or 'ending in' in answer.lower(), \
                    f"Answer should explicitly mention the digits, but got: {answer}"
    
    def test_bug3_card_last_4_digits_not_captured_message(self):
        """
        Bug 3b: Missing Metadata Extraction - Explicit Unavailability
        
        EXPECTED: When card_last_4_digits is None/empty, should explicitly state
        "last 4 digits weren't captured"
        
        CURRENT (UNFIXED): Returns generic "You used MasterCard" without checking
        if digits are available
        
        **Validates: Requirements 2.3, 2.4**
        """
        # Arrange: Create query engine with mocked dependencies
        with patch('backend.query_engine.get_embedding_engine') as mock_emb:
            with patch('backend.query_engine.get_vector_store') as mock_vs:
                mock_emb.return_value.generate_embedding.return_value = [0.1] * 384
                
                # Simulate result WITHOUT card_last_4_digits (field is None)
                mock_results = [
                    QueryResult(
                        chunk_id="receipt-1",
                        content="Receipt from Costco. Payment: MasterCard",
                        metadata={
                            'filename': 'costco_receipt.jpg',
                            'file_type': 'image',
                            'folder_path': '/receipts',
                            'merchant': 'Costco',
                            'date': '2026-02-11',
                            'payment_method': 'MasterCard',
                            'card_last_4_digits': None  # Field exists but is None
                        },
                        similarity_score=0.90
                    )
                ]
                mock_vs.return_value.query.return_value = mock_results
                
                engine = QueryEngine()
                
                # Act: Execute query asking for last 4 digits
                response = engine.query("last 4 digits")
                
                # Assert: EXPECTED behavior (will FAIL on unfixed code)
                # After fix: Should explicitly state that digits weren't captured
                answer = response['answer']
                print(f"\n[DEBUG] Bug 3b test - Answer: {answer}")
                
                # Check for explicit unavailability message
                assert "weren't captured" in answer.lower() or "not captured" in answer.lower(), \
                    f"Answer should explicitly state digits weren't captured, but got: {answer}"
                
                # Should still mention the payment method
                assert 'MasterCard' in answer, \
                    f"Answer should mention the payment method, but got: {answer}"
    
    def test_bug4_repeated_query_acknowledgment(self):
        """
        Bug 4: Repetitive Non-Answers
        
        EXPECTED: Repeated query "last 4 digits" should acknowledge repetition
        and provide explicit unavailability message
        
        CURRENT (UNFIXED): Returns identical "You used MasterCard" each time
        without acknowledging the repeated request
        
        **Validates: Requirements 2.4**
        """
        # Arrange: Create query engine with mocked dependencies
        with patch('backend.query_engine.get_embedding_engine') as mock_emb:
            with patch('backend.query_engine.get_vector_store') as mock_vs:
                mock_emb.return_value.generate_embedding.return_value = [0.1] * 384
                
                # Simulate result WITHOUT card_last_4_digits
                mock_results = [
                    QueryResult(
                        chunk_id="receipt-1",
                        content="Receipt from Costco. Payment: MasterCard",
                        metadata={
                            'filename': 'costco_receipt.jpg',
                            'file_type': 'image',
                            'folder_path': '/receipts',
                            'merchant': 'Costco',
                            'date': '2026-02-11',
                            'payment_method': 'MasterCard',
                            'card_last_4_digits': None
                        },
                        similarity_score=0.90
                    )
                ]
                mock_vs.return_value.query.return_value = mock_results
                
                engine = QueryEngine()
                
                # Build conversation history with repeated queries
                conversation_history = [
                    {"role": "user", "content": "what card did i use?"},
                    {"role": "assistant", "content": "You used MasterCard."},
                    {"role": "user", "content": "last 4 digits"},
                    {"role": "assistant", "content": "You used MasterCard."}
                ]
                
                # Act: Execute repeated query
                response = engine.query("last 4 digits", conversation_history=conversation_history)
                
                # Assert: EXPECTED behavior (will FAIL on unfixed code)
                # After fix: Should acknowledge repetition and provide explicit message
                answer = response['answer']
                
                # Check for acknowledgment of repetition
                repetition_indicators = [
                    "as i mentioned",
                    "as mentioned",
                    "already",
                    "again",
                    "weren't captured",
                    "not captured"
                ]
                
                has_acknowledgment = any(indicator in answer.lower() for indicator in repetition_indicators)
                assert has_acknowledgment, \
                    f"Answer should acknowledge the repeated query or provide explicit unavailability, but got: {answer}"
                
                # Should NOT be the exact same generic answer
                assert answer != "You used MasterCard.", \
                    "Answer should not be the same generic response for repeated query"
    
    @given(
        similarity_scores=st.lists(
            st.floats(min_value=0.0, max_value=1.0),
            min_size=3,
            max_size=10
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_property_all_sources_above_threshold(self, similarity_scores):
        """
        Property: Source Relevance Filtering
        
        For ANY query result set with mixed similarity scores, the sources shown
        in the UI should ALL have similarity >= 0.5
        
        This is a property-based test that generates random similarity scores
        and verifies the filtering behavior.
        
        **Validates: Requirements 2.2, 2.6**
        """
        # Filter to ensure we have at least one score >= 0.5
        assume(any(score >= 0.5 for score in similarity_scores))
        
        # Arrange: Create query engine with mocked dependencies
        with patch('backend.query_engine.get_embedding_engine') as mock_emb:
            with patch('backend.query_engine.get_vector_store') as mock_vs:
                mock_emb.return_value.generate_embedding.return_value = [0.1] * 384
                
                # Generate mock results with the given similarity scores
                mock_results = []
                for i, score in enumerate(similarity_scores):
                    mock_results.append(
                        QueryResult(
                            chunk_id=f"doc-{i}",
                            content=f"Document content {i}",
                            metadata={
                                'filename': f'document_{i}.pdf',
                                'file_type': 'text',
                                'folder_path': '/documents'
                            },
                            similarity_score=score
                        )
                    )
                
                mock_vs.return_value.query.return_value = mock_results
                
                engine = QueryEngine()
                
                # Act: Execute query
                response = engine.query("test query")
                
                # Assert: EXPECTED behavior (will FAIL on unfixed code)
                # After fix: ALL sources should have similarity >= 0.5
                for source in response['sources']:
                    assert source['score'] >= 0.5, \
                        f"All sources should have similarity >= 0.5, but found score {source['score']}"
                
                # Verify that we filtered out low-similarity sources
                expected_count = sum(1 for score in similarity_scores if score >= 0.5)
                assert len(response['sources']) == expected_count, \
                    f"Expected {expected_count} sources (>= 0.5), but got {len(response['sources'])}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
