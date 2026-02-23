"""
Bug Condition Exploration Test for Metadata Extraction Consistency

This test is EXPECTED TO FAIL on unfixed code.
Failure confirms the bugs exist: field name inconsistencies, type issues,
filter extraction failures, insufficient retrieval, response instability,
and incomplete metadata display.

DO NOT attempt to fix the test or the code when it fails.
This test encodes the expected behavior and will validate the fix when it passes.
"""

import pytest
from datetime import datetime
from typing import List, Dict, Any
import tempfile
import shutil
import os
import json

from backend.models import DocumentChunk, ImageExtraction
from backend.vector_store import VectorStore
from backend.query_engine import QueryEngine
from backend.image_processor import ImageProcessor
from backend.llm_generator import LLMGenerator


class TestMetadataExtractionConsistencyBugCondition:
    """
    Bug Condition Exploration Test for Metadata Extraction Consistency Bugs
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8**
    
    This test demonstrates multiple bugs in the metadata extraction and retrieval system:
    1. Field name inconsistencies (store vs merchant vs vendor)
    2. Type inconsistencies (numeric values stored as strings)
    3. Filter extraction failures (_extract_metadata_filters returns None)
    4. Insufficient chunk retrieval (only 5 chunks for multi-document queries)
    5. Vision response instability (long responses, repetition loops)
    6. Incomplete metadata display (only store/total/date shown in LLM prompts)
    
    EXPECTED OUTCOME ON UNFIXED CODE: Test FAILS - bugs are confirmed
    EXPECTED OUTCOME ON FIXED CODE: Test PASSES - all bugs are fixed
    """
    
    def test_field_name_inconsistency(self):
        """
        Test 1.1: Field Name Inconsistency
        
        **Validates: Requirements 2.1, 2.7**
        
        This test demonstrates that the vision model produces inconsistent field names
        for the same concept (store vs merchant vs vendor) despite prompt instructions.
        
        Test approach:
        1. Simulate vision model responses with field name variants
        2. Parse responses using ImageProcessor._parse_response
        3. Verify that field names are inconsistent (no normalization)
        
        EXPECTED OUTCOME ON UNFIXED CODE:
        - Field names vary: "store", "merchant", "vendor" for same concept
        - No normalization applied
        - Test FAILS (this is correct - proves bug exists)
        
        EXPECTED OUTCOME ON FIXED CODE:
        - All field names normalized to canonical "store"
        - Test PASSES
        """
        print(f"\n{'='*70}")
        print(f"BUG 1 ANALYSIS: Field Name Inconsistency")
        print(f"{'='*70}")
        
        # Simulate vision model responses with field name variants
        vision_responses = [
            '{"store": "Costco", "date": "2024-02-08", "total": "411.89"}',
            '{"merchant": "Costco", "date": "2024-02-08", "total": "411.89"}',
            '{"vendor": "Costco", "date": "2024-02-08", "total": "411.89"}',
        ]
        
        print(f"\nSimulating 3 identical Costco receipts with different field names:")
        
        processor = ImageProcessor()
        field_names_used = []
        
        for i, response in enumerate(vision_responses):
            extraction = processor._parse_response(response)
            metadata = extraction.flexible_metadata
            
            # Check which field name was used for the store
            store_field = None
            if 'store' in metadata:
                store_field = 'store'
            elif 'merchant' in metadata:
                store_field = 'merchant'
            elif 'vendor' in metadata:
                store_field = 'vendor'
            
            field_names_used.append(store_field)
            print(f"  Receipt {i+1}: Field name = '{store_field}', Value = '{metadata.get(store_field)}'")
        
        # Check if field names are consistent
        unique_field_names = set(field_names_used)
        is_consistent = len(unique_field_names) == 1 and 'store' in unique_field_names
        
        print(f"\nField names used: {unique_field_names}")
        print(f"Consistent (all 'store'): {is_consistent}")
        
        if is_consistent:
            print(f"\n✓ TEST PASSED: Field names are normalized to 'store'")
        else:
            print(f"\n✗ BUG 1 CONFIRMED: Field name inconsistency detected")
            print(f"  Expected: All receipts use 'store'")
            print(f"  Actual: Receipts use {unique_field_names}")
            print(f"  Impact: Queries for 'Costco' will only match receipts with matching field name")
            
            pytest.fail(
                f"Bug 1 Confirmed: Field name inconsistency - receipts use {unique_field_names} "
                f"instead of canonical 'store'. This is expected on unfixed code."
            )
    
    def test_type_inconsistency(self):
        """
        Test 1.2: Type Inconsistency
        
        **Validates: Requirements 2.2**
        
        This test demonstrates that numeric fields are stored as strings instead of
        numeric types, preventing range queries and mathematical operations.
        
        Test approach:
        1. Simulate vision model response with numeric fields as strings
        2. Parse response using ImageProcessor._parse_response
        3. Verify that numeric fields are strings (no type coercion)
        
        EXPECTED OUTCOME ON UNFIXED CODE:
        - Numeric fields are strings: "411.89" instead of 411.89
        - Test FAILS (this is correct - proves bug exists)
        
        EXPECTED OUTCOME ON FIXED CODE:
        - Numeric fields are float/int: 411.89
        - Test PASSES
        """
        print(f"\n{'='*70}")
        print(f"BUG 2 ANALYSIS: Type Inconsistency")
        print(f"{'='*70}")
        
        # Simulate vision model response with numeric fields as strings
        vision_response = '{"store": "Costco", "date": "2024-02-08", "total": "411.89", "subtotal": "380.00", "tax": "31.89"}'
        
        print(f"\nSimulating receipt with numeric fields:")
        print(f"  Vision response: {vision_response}")
        
        processor = ImageProcessor()
        extraction = processor._parse_response(vision_response)
        metadata = extraction.flexible_metadata
        
        # Check types of numeric fields
        numeric_fields = ['total', 'subtotal', 'tax']
        type_issues = []
        
        print(f"\nChecking types of numeric fields:")
        for field in numeric_fields:
            if field in metadata:
                value = metadata[field]
                value_type = type(value).__name__
                is_numeric = isinstance(value, (int, float))
                
                print(f"  {field}: value={value}, type={value_type}, is_numeric={is_numeric}")
                
                if not is_numeric:
                    type_issues.append(field)
        
        if not type_issues:
            print(f"\n✓ TEST PASSED: All numeric fields have correct types")
        else:
            print(f"\n✗ BUG 2 CONFIRMED: Type inconsistency detected")
            print(f"  Fields with wrong types: {type_issues}")
            print(f"  Expected: float or int")
            print(f"  Actual: str")
            print(f"  Impact: Range queries like 'total > 400' will fail")
            
            pytest.fail(
                f"Bug 2 Confirmed: Type inconsistency - numeric fields {type_issues} "
                f"are stored as strings instead of numeric types. This is expected on unfixed code."
            )
    
    def test_filter_extraction_failure(self):
        """
        Test 1.3: Filter Extraction Failure
        
        **Validates: Requirements 2.3, 2.4**
        
        This test demonstrates that _extract_metadata_filters always returns None,
        failing to extract store filters from natural language queries.
        
        Test approach:
        1. Call _extract_metadata_filters with store-specific queries
        2. Verify that it returns None (not extracting filters)
        
        EXPECTED OUTCOME ON UNFIXED CODE:
        - _extract_metadata_filters returns None for all queries
        - Test FAILS (this is correct - proves bug exists)
        
        EXPECTED OUTCOME ON FIXED CODE:
        - _extract_metadata_filters returns filter dict like {"store": {"$eq": "Costco"}}
        - Test PASSES
        """
        print(f"\n{'='*70}")
        print(f"BUG 3 ANALYSIS: Filter Extraction Failure")
        print(f"{'='*70}")
        
        query_engine = QueryEngine()
        
        # Test queries with store-specific intent
        test_queries = [
            "How much did I spend at Costco?",
            "Show me receipts from Walmart",
            "What did I buy at Target?",
        ]
        
        print(f"\nTesting _extract_metadata_filters with store-specific queries:")
        
        extraction_failures = []
        
        for query in test_queries:
            filters = query_engine._extract_metadata_filters(query)
            
            print(f"\n  Query: '{query}'")
            print(f"  Extracted filters: {filters}")
            
            if filters is None or 'store' not in filters:
                extraction_failures.append(query)
                print(f"    ✗ FAILED: No store filter extracted")
            else:
                print(f"    ✓ SUCCESS: Store filter extracted")
        
        if not extraction_failures:
            print(f"\n✓ TEST PASSED: All store filters extracted correctly")
        else:
            print(f"\n✗ BUG 3 CONFIRMED: Filter extraction failure")
            print(f"  Queries that failed: {len(extraction_failures)}/{len(test_queries)}")
            print(f"  Expected: Filter dict like {{'store': {{'$eq': 'Costco'}}}}")
            print(f"  Actual: None")
            print(f"  Impact: Store-specific queries retrieve all receipts, not just matching store")
            
            pytest.fail(
                f"Bug 3 Confirmed: _extract_metadata_filters returns None for store-specific queries. "
                f"This is expected on unfixed code."
            )
    
    def test_insufficient_retrieval(self):
        """
        Test 1.4: Insufficient Retrieval
        
        **Validates: Requirements 2.5**
        
        This test demonstrates that aggregation queries only retrieve 5 chunks,
        which is insufficient when 10+ receipts exist.
        
        Test approach:
        1. Create test database with 15 receipts
        2. Query "What's my total spending?"
        3. Verify that fewer than 15 chunks are retrieved
        
        EXPECTED OUTCOME ON UNFIXED CODE:
        - Only 5 chunks retrieved (insufficient for 15 receipts)
        - Test FAILS (this is correct - proves bug exists)
        
        EXPECTED OUTCOME ON FIXED CODE:
        - At least 15 chunks retrieved
        - Test PASSES
        """
        print(f"\n{'='*70}")
        print(f"BUG 4 ANALYSIS: Insufficient Retrieval")
        print(f"{'='*70}")
        
        # Create temporary test database
        temp_dir = tempfile.mkdtemp(prefix="test_insufficient_retrieval_")
        
        try:
            print(f"\nCreating test database with 15 receipts...")
            
            # Initialize vector store
            vector_store = VectorStore(persist_directory=temp_dir)
            vector_store.initialize()
            
            # Create 15 test receipts
            test_chunks = []
            for i in range(15):
                chunk = DocumentChunk(
                    content=f"Receipt {i+1} from Store {i+1}. Total: ${100 + i*10}.00",
                    metadata={
                        'filename': f'receipt_{i+1}.jpg',
                        'folder_path': temp_dir,
                        'file_type': 'image',
                        'store': f'Store {i+1}',
                        'total': f'{100 + i*10}.00',
                        'user_id': 1
                    }
                )
                test_chunks.append(chunk)
            
            vector_store.add_chunks(test_chunks)
            print(f"✓ Created {len(test_chunks)} receipts")
            
            # Query for total spending (aggregation query)
            print(f"\nQuerying: 'What's my total spending?'")
            
            query_engine = QueryEngine()
            
            # Check the default top_k parameter in query method
            import inspect
            query_signature = inspect.signature(QueryEngine.query)
            default_top_k = query_signature.parameters['top_k'].default
            
            print(f"  Default top_k parameter: {default_top_k}")
            
            # Simulate query (we'll check the retrieval count)
            # Note: We can't easily test the actual query without embeddings,
            # so we'll check the code behavior
            
            if default_top_k < 15:
                print(f"\n✗ BUG 4 CONFIRMED: Insufficient retrieval")
                print(f"  Default top_k: {default_top_k}")
                print(f"  Required for 15 receipts: 15")
                print(f"  Impact: Aggregation queries miss {15 - default_top_k} receipts")
                
                pytest.fail(
                    f"Bug 4 Confirmed: Default top_k={default_top_k} is insufficient for "
                    f"aggregation queries with 15+ receipts. This is expected on unfixed code."
                )
            else:
                print(f"\n✓ TEST PASSED: Sufficient retrieval (top_k={default_top_k})")
        
        finally:
            # Clean up
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except (PermissionError, OSError):
                pass
    
    def test_response_instability(self):
        """
        Test 1.5: Response Instability
        
        **Validates: Requirements 2.6**
        
        This test demonstrates that vision model responses can be unstable:
        - Responses may exceed 5000 characters
        - Responses may contain repetition loops
        
        Test approach:
        1. Simulate long vision response with repetition
        2. Check if _fix_repetition_loop detects and fixes it
        3. Verify response length limits
        
        EXPECTED OUTCOME ON UNFIXED CODE:
        - Long responses not prevented (num_predict=2048 allows long output)
        - Repetition loops may not be caught by _fix_repetition_loop
        - Test FAILS (this is correct - proves bug exists)
        
        EXPECTED OUTCOME ON FIXED CODE:
        - Response length limited (num_predict reduced to 1024)
        - Repetition loops detected and fixed
        - Test PASSES
        """
        print(f"\n{'='*70}")
        print(f"BUG 5 ANALYSIS: Response Instability")
        print(f"{'='*70}")
        
        processor = ImageProcessor()
        
        # Check num_predict setting in process_image
        import inspect
        process_image_source = inspect.getsource(processor.process_image)
        
        # Extract num_predict value
        import re
        num_predict_match = re.search(r'"num_predict":\s*(\d+)', process_image_source)
        num_predict = int(num_predict_match.group(1)) if num_predict_match else None
        
        print(f"\nChecking vision model configuration:")
        print(f"  num_predict: {num_predict}")
        
        # Simulate a response with repetition loop
        repetitive_response = '{"store": "Costco", "date": "2024-02-08", "total": "411.89", ' * 50
        repetitive_response += '"store": "Costco"}'  # Close JSON
        
        print(f"\nSimulating repetitive response:")
        print(f"  Original length: {len(repetitive_response)} chars")
        print(f"  Contains repetition: Yes")
        
        # Test _fix_repetition_loop
        fixed_response = processor._fix_repetition_loop(repetitive_response)
        
        print(f"\nAfter _fix_repetition_loop:")
        print(f"  Fixed length: {len(fixed_response)} chars")
        print(f"  Reduction: {len(repetitive_response) - len(fixed_response)} chars")
        
        # Check if response is still too long or has repetition
        issues = []
        
        if num_predict and num_predict > 1024:
            issues.append(f"num_predict={num_predict} allows long responses (should be ≤1024)")
        
        if len(fixed_response) > 5000:
            issues.append(f"Fixed response still too long ({len(fixed_response)} chars)")
        
        # Check if repetition was actually fixed
        store_count = fixed_response.count('"store": "Costco"')
        if store_count > 2:
            issues.append(f"Repetition not fully fixed (still {store_count} occurrences)")
        
        if not issues:
            print(f"\n✓ TEST PASSED: Response instability prevented")
        else:
            print(f"\n✗ BUG 5 CONFIRMED: Response instability issues")
            for issue in issues:
                print(f"  - {issue}")
            print(f"  Impact: Vision model may generate excessively long or repetitive responses")
            
            pytest.fail(
                f"Bug 5 Confirmed: Response instability - {'; '.join(issues)}. "
                f"This is expected on unfixed code."
            )
    
    def test_incomplete_metadata_display(self):
        """
        Test 1.6: Incomplete Metadata Display
        
        **Validates: Requirements 2.8**
        
        This test demonstrates that LLM prompts only include store/total/date fields,
        missing other metadata like subtotal, tax, payment_method.
        
        Test approach:
        1. Create mock QueryResult with full metadata
        2. Call LLMGenerator.generate_general_response
        3. Check if all metadata fields appear in the prompt
        
        EXPECTED OUTCOME ON UNFIXED CODE:
        - Only store, total, date appear in prompt
        - Other fields (subtotal, tax, payment_method) missing
        - Test FAILS (this is correct - proves bug exists)
        
        EXPECTED OUTCOME ON FIXED CODE:
        - All metadata fields appear in prompt
        - Test PASSES
        """
        print(f"\n{'='*70}")
        print(f"BUG 6 ANALYSIS: Incomplete Metadata Display")
        print(f"{'='*70}")
        
        # Check the generate_general_response method
        import inspect
        from backend.llm_generator import LLMGenerator
        
        llm_gen = LLMGenerator()
        
        # Get source code of generate_general_response
        gen_response_source = inspect.getsource(llm_gen.generate_general_response)
        
        print(f"\nAnalyzing generate_general_response method:")
        
        # Check if it only extracts specific fields
        hardcoded_fields = []
        if "metadata.get('store'" in gen_response_source:
            hardcoded_fields.append('store')
        if "metadata.get('total'" in gen_response_source:
            hardcoded_fields.append('total')
        if "metadata.get('date'" in gen_response_source:
            hardcoded_fields.append('date')
        
        # Check if it iterates through all metadata fields
        iterates_all_fields = 'for' in gen_response_source and 'metadata.items()' in gen_response_source
        
        print(f"  Hardcoded field extraction: {hardcoded_fields if hardcoded_fields else 'None'}")
        print(f"  Iterates all metadata fields: {iterates_all_fields}")
        
        if hardcoded_fields and not iterates_all_fields:
            print(f"\n✗ BUG 6 CONFIRMED: Incomplete metadata display")
            print(f"  Only extracts: {hardcoded_fields}")
            print(f"  Missing: subtotal, tax, payment_method, and other fields")
            print(f"  Impact: LLM cannot answer questions about missing metadata fields")
            
            pytest.fail(
                f"Bug 6 Confirmed: generate_general_response only extracts {hardcoded_fields}, "
                f"missing other metadata fields. This is expected on unfixed code."
            )
        else:
            print(f"\n✓ TEST PASSED: All metadata fields included in prompt")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
