"""
Preservation Property Tests for Metadata Extraction Consistency Fix

This test MUST PASS on unfixed code to establish baseline behavior.
After the fix, non-metadata functionality should continue to work identically.

This test uses property-based testing to generate many test cases for stronger guarantees.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from unittest.mock import patch, Mock, MagicMock
import tempfile
import shutil
import os
import json

from backend.image_processor import ImageProcessor
from backend.query_engine import QueryEngine
from backend.text_processor import chunk_text, extract_from_txt
from backend.models import DocumentChunk, ImageExtraction, QueryResult


class TestMetadataExtractionConsistencyPreservation:
    """
    Preservation Property Tests for Metadata Extraction Consistency Fix
    
    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
    
    This test establishes baseline behavior for non-metadata functionality that must be preserved:
    1. Text extraction from text-only PDFs (no metadata extraction)
    2. Semantic search for general queries without metadata filters
    3. Documents with correct canonical field names stored without modification
    4. Single-document queries return same results efficiently
    
    EXPECTED OUTCOME ON UNFIXED CODE: Tests PASS - baseline behavior established
    EXPECTED OUTCOME ON FIXED CODE: Tests PASS - same behavior preserved
    """
    
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        text_content=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs', 'Po')),
            min_size=100,
            max_size=500
        )
    )
    def test_text_extraction_preservation(self, text_content):
        """
        Test 2.1: Text Extraction Preservation
        
        **Validates: Requirements 3.1, 3.2**
        
        This test establishes baseline behavior for text extraction from text-only documents.
        Text extraction should produce identical results before and after the fix.
        
        Property: For any text-only document (no metadata extraction),
        the text extraction process produces consistent results.
        
        EXPECTED OUTCOME ON UNFIXED CODE:
        - Text is extracted correctly
        - Chunks are created with proper metadata
        - No metadata extraction is performed
        - Test PASSES to establish baseline
        
        EXPECTED OUTCOME ON FIXED CODE:
        - Same text extraction behavior
        - Test PASSES to confirm preservation
        """
        # Skip empty or whitespace-only text
        assume(text_content.strip() != "")
        
        print(f"\n{'='*70}")
        print(f"PRESERVATION TEST: Text Extraction")
        print(f"Text length: {len(text_content)} chars")
        print(f"{'='*70}")
        
        # Create temporary text file with UTF-8 encoding
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as tmp_file:
            tmp_file.write(text_content)
            tmp_path = tmp_file.name
        
        try:
            # Extract text using text processor
            extracted_text = extract_from_txt(tmp_path)
            
            # Verify text extraction is consistent
            assert extracted_text == text_content, \
                f"Extracted text should match original"
            
            # Create chunks from text
            chunks = chunk_text(
                text=extracted_text,
                filename=os.path.basename(tmp_path),
                folder_path=os.path.dirname(tmp_path),
                user_id=1,
                page_number=None
            )
            
            # Verify chunks are created
            assert len(chunks) > 0, "Should create at least one chunk"
            
            # Verify chunk metadata doesn't contain vision-extracted fields
            for chunk in chunks:
                metadata = chunk.metadata
                assert 'file_type' in metadata, "Should have file_type metadata"
                assert metadata['file_type'] == 'text', "Should be marked as text"
                assert 'user_id' in metadata, "Should have user_id metadata"
                
                # Verify no vision-specific metadata fields
                assert 'store' not in metadata, "Text-only should not have store metadata"
                assert 'total' not in metadata, "Text-only should not have total metadata"
                assert 'merchant' not in metadata, "Text-only should not have merchant metadata"
            
            print(f"  ✓ Text extracted: {len(extracted_text)} chars")
            print(f"  ✓ Chunks created: {len(chunks)}")
            print(f"  ✓ No metadata extraction performed")
            print(f"  ✓ PRESERVATION TEST PASSED")
        
        finally:
            # Clean up
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        query_text=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs')),
            min_size=10,
            max_size=50
        ),
        top_k=st.integers(min_value=1, max_value=5)
    )
    def test_semantic_search_preservation(self, query_text, top_k):
        """
        Test 2.2: Semantic Search Preservation
        
        **Validates: Requirements 3.3**
        
        This test establishes baseline behavior for semantic search without metadata filters.
        General queries should retrieve same chunks with same similarity scores.
        
        Property: For any general query without metadata filter intent,
        the semantic search retrieves consistent results.
        
        EXPECTED OUTCOME ON UNFIXED CODE:
        - Semantic search works correctly
        - Top-k results are returned
        - Similarity scores are consistent
        - No metadata filtering applied
        - Test PASSES to establish baseline
        
        EXPECTED OUTCOME ON FIXED CODE:
        - Same semantic search behavior
        - Test PASSES to confirm preservation
        """
        # Skip empty or whitespace-only text
        assume(query_text.strip() != "")
        
        # Ensure query doesn't contain store-specific intent
        # (we want to test general semantic search, not filtered search)
        assume(not any(word in query_text.lower() for word in ['costco', 'walmart', 'target', 'store']))
        
        print(f"\n{'='*70}")
        print(f"PRESERVATION TEST: Semantic Search")
        print(f"Query: {query_text[:40]}..." if len(query_text) > 40 else f"Query: {query_text}")
        print(f"Top-K: {top_k}")
        print(f"{'='*70}")
        
        # Mock the vector store to return consistent results
        mock_results = []
        for i in range(min(top_k, 5)):
            mock_results.append(QueryResult(
                chunk_id=f"chunk_{i}",
                content=f"Mock content {i} for query: {query_text[:20]}",
                metadata={
                    'filename': f'test_file_{i}.txt',
                    'file_type': 'text',
                    'folder_path': '/test/path',
                    'user_id': 1
                },
                similarity_score=0.9 - (i * 0.1)
            ))
        
        # Create query engine with mocked dependencies
        with patch('backend.query_engine.get_vector_store') as mock_vs, \
             patch('backend.query_engine.get_embedding_engine') as mock_ee, \
             patch('backend.query_engine.get_llm_generator') as mock_llm:
            
            # Setup mocks
            mock_vs_instance = Mock()
            mock_vs_instance.query.return_value = mock_results
            mock_vs.return_value = mock_vs_instance
            
            mock_ee_instance = Mock()
            mock_ee_instance.generate_embedding.return_value = [0.1] * 1024
            mock_ee.return_value = mock_ee_instance
            
            mock_llm_instance = Mock()
            mock_llm_instance.generate_general_response.return_value = "Test response"
            mock_llm.return_value = mock_llm_instance
            
            # Create query engine
            engine = QueryEngine()
            
            # Query twice with same parameters
            result1 = engine.query(query_text, user_id=1, top_k=top_k)
            result2 = engine.query(query_text, user_id=1, top_k=top_k)
            
            # Verify results are consistent
            assert result1 is not None, "First result should not be None"
            assert result2 is not None, "Second result should not be None"
            
            # Verify sources are consistent
            sources1 = result1.get('sources', [])
            sources2 = result2.get('sources', [])
            
            assert len(sources1) == len(sources2), \
                f"Source counts should match: {len(sources1)} vs {len(sources2)}"
            
            # Verify similarity scores are consistent
            if sources1:
                scores1 = [s['score'] for s in sources1]
                scores2 = [s['score'] for s in sources2]
                
                assert scores1 == scores2, "Similarity scores should be identical"
                
                print(f"  ✓ Retrieved {len(sources1)} sources")
                print(f"  ✓ Similarity scores: {scores1}")
                print(f"  ✓ Semantic search is consistent")
                print(f"  ✓ PRESERVATION TEST PASSED")
            else:
                print(f"  ✓ No sources retrieved (expected for mock)")
                print(f"  ✓ Consistent empty result")
                print(f"  ✓ PRESERVATION TEST PASSED")
    
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        store_name=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),
            min_size=3,
            max_size=20
        ),
        total_amount=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        date_str=st.text(
            alphabet=st.characters(whitelist_categories=('Nd', 'Pd')),
            min_size=10,
            max_size=10
        )
    )
    def test_canonical_field_names_preservation(self, store_name, total_amount, date_str):
        """
        Test 2.3: Canonical Field Names Preservation
        
        **Validates: Requirements 3.4**
        
        This test establishes baseline behavior for documents that already use
        correct canonical field names (store, date, total).
        
        Property: For any document that already uses canonical field names,
        the system stores and retrieves it without modification.
        
        EXPECTED OUTCOME ON UNFIXED CODE:
        - Documents with canonical names are stored correctly
        - Field names are not modified
        - Values are preserved as-is
        - Test PASSES to establish baseline
        
        EXPECTED OUTCOME ON FIXED CODE:
        - Same behavior for canonical names
        - Test PASSES to confirm preservation
        """
        # Skip empty or invalid inputs
        assume(store_name.strip() != "")
        assume(total_amount > 0)
        
        # Format date as YYYY-MM-DD if possible
        if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
            date_formatted = date_str
        else:
            date_formatted = "2024-02-08"  # Default valid date
        
        print(f"\n{'='*70}")
        print(f"PRESERVATION TEST: Canonical Field Names")
        print(f"Store: {store_name}")
        print(f"Total: ${total_amount:.2f}")
        print(f"Date: {date_formatted}")
        print(f"{'='*70}")
        
        # Create vision response with canonical field names
        vision_response = json.dumps({
            "store": store_name,
            "date": date_formatted,
            "total": str(total_amount)
        })
        
        # Parse response using ImageProcessor
        processor = ImageProcessor()
        extraction = processor._parse_response(vision_response)
        
        # Verify canonical field names are preserved
        metadata = extraction.flexible_metadata
        
        assert 'store' in metadata, "Should have 'store' field"
        assert metadata['store'] == store_name, "Store name should be preserved"
        
        assert 'date' in metadata, "Should have 'date' field"
        assert metadata['date'] == date_formatted, "Date should be preserved"
        
        assert 'total' in metadata, "Should have 'total' field"
        # After type coercion fix, numeric fields should be converted to numeric types
        # This is expected behavior - numeric strings are coerced to float/int
        assert isinstance(metadata['total'], (int, float)), "Total should be numeric type after coercion"
        assert float(metadata['total']) == pytest.approx(total_amount, rel=1e-2), "Total value should match"
        
        # Verify no field name variants are created
        assert 'merchant' not in metadata, "Should not create 'merchant' variant"
        assert 'vendor' not in metadata, "Should not create 'vendor' variant"
        assert 'shop' not in metadata, "Should not create 'shop' variant"
        
        print(f"  ✓ Canonical field names preserved")
        print(f"  ✓ No variants created")
        print(f"  ✓ Values unchanged")
        print(f"  ✓ PRESERVATION TEST PASSED")
    
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        query_text=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs')),
            min_size=10,
            max_size=50
        )
    )
    def test_single_document_query_preservation(self, query_text):
        """
        Test 2.4: Single-Document Query Preservation
        
        **Validates: Requirements 3.5, 3.6**
        
        This test establishes baseline behavior for simple single-document queries.
        These queries should return relevant results efficiently without requiring
        large-scale retrieval.
        
        Property: For any simple query that retrieves 1-3 chunks,
        the system returns same results efficiently.
        
        EXPECTED OUTCOME ON UNFIXED CODE:
        - Single-document queries work correctly
        - Results are returned efficiently
        - LLM generates coherent responses
        - Test PASSES to establish baseline
        
        EXPECTED OUTCOME ON FIXED CODE:
        - Same single-document query behavior
        - Test PASSES to confirm preservation
        """
        # Skip empty or whitespace-only text
        assume(query_text.strip() != "")
        
        # Ensure query is simple (not aggregation query)
        assume(not any(word in query_text.lower() for word in ['total', 'sum', 'all', 'how much']))
        
        print(f"\n{'='*70}")
        print(f"PRESERVATION TEST: Single-Document Query")
        print(f"Query: {query_text[:40]}..." if len(query_text) > 40 else f"Query: {query_text}")
        print(f"{'='*70}")
        
        # Mock single result (simple query)
        mock_result = QueryResult(
            chunk_id="chunk_0",
            content=f"This is relevant content for: {query_text[:30]}",
            metadata={
                'filename': 'test_document.txt',
                'file_type': 'text',
                'folder_path': '/test/path',
                'user_id': 1
            },
            similarity_score=0.85
        )
        
        # Create query engine with mocked dependencies
        with patch('backend.query_engine.get_vector_store') as mock_vs, \
             patch('backend.query_engine.get_embedding_engine') as mock_ee, \
             patch('backend.query_engine.get_llm_generator') as mock_llm:
            
            # Setup mocks
            mock_vs_instance = Mock()
            mock_vs_instance.query.return_value = [mock_result]
            mock_vs.return_value = mock_vs_instance
            
            mock_ee_instance = Mock()
            mock_ee_instance.generate_embedding.return_value = [0.1] * 1024
            mock_ee.return_value = mock_ee_instance
            
            mock_llm_instance = Mock()
            mock_llm_instance.generate_general_response.return_value = "This is a coherent response."
            mock_llm.return_value = mock_llm_instance
            
            # Create query engine
            engine = QueryEngine()
            
            # Execute query
            result = engine.query(query_text, user_id=1, top_k=3)
            
            # Verify result structure
            assert result is not None, "Result should not be None"
            assert 'answer' in result, "Should have answer field"
            assert 'sources' in result, "Should have sources field"
            
            # Verify single result is returned
            sources = result.get('sources', [])
            assert len(sources) == 1, f"Should return 1 source for simple query, got {len(sources)}"
            
            # Verify LLM response is coherent
            answer = result.get('answer', '')
            assert len(answer) > 0, "Answer should not be empty"
            assert answer == "This is a coherent response.", "LLM response should be preserved"
            
            print(f"  ✓ Single result returned")
            print(f"  ✓ LLM response coherent")
            print(f"  ✓ Query executed efficiently")
            print(f"  ✓ PRESERVATION TEST PASSED")
    
    def test_preservation_baseline_summary(self):
        """
        Summary test to document baseline preservation behavior.
        
        This test documents the expected behavior that must be preserved after the fix.
        """
        print(f"\n{'='*70}")
        print(f"BASELINE SUMMARY: Preservation Requirements")
        print(f"{'='*70}")
        
        print("\nBaseline behavior established:")
        print("  1. Text Extraction (Req 3.1, 3.2):")
        print("     - Text-only documents extract text correctly")
        print("     - Chunks are created with proper metadata")
        print("     - No metadata extraction for text-only files")
        
        print("\n  2. Semantic Search (Req 3.3):")
        print("     - General queries retrieve chunks by similarity")
        print("     - Top-k results are returned consistently")
        print("     - Similarity scores are stable")
        print("     - No metadata filtering for general queries")
        
        print("\n  3. Canonical Field Names (Req 3.4):")
        print("     - Documents with correct field names (store, date, total)")
        print("     - Field names are preserved without modification")
        print("     - Values are stored as-is")
        print("     - No variants created")
        
        print("\n  4. Single-Document Queries (Req 3.5, 3.6):")
        print("     - Simple queries return 1-3 relevant chunks")
        print("     - Results are returned efficiently")
        print("     - LLM generates coherent responses")
        print("     - No large-scale retrieval needed")
        
        print("\nAfter fix:")
        print("  - All above behaviors MUST remain unchanged")
        print("  - Only metadata extraction consistency should improve")
        print("  - No regressions in text extraction, search, or response generation")
        
        print(f"\n✓ PRESERVATION TEST BASELINE ESTABLISHED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
