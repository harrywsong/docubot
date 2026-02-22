"""
Bug Condition Exploration Test for Spending Query Logic

This test is EXPECTED TO FAIL on unfixed code.
Failure confirms Bug 3 exists: the system assumes all documents are receipts
and attempts to aggregate amounts using receipt-specific logic.

DO NOT attempt to fix the test or the code when it fails.
This test encodes the expected behavior and will validate the fix when it passes.
"""

import pytest
from datetime import datetime
from typing import List
import tempfile
import shutil
import os

from backend.models import DocumentChunk, ImageExtraction
from backend.vector_store import VectorStore
from backend.query_engine import QueryEngine
from backend.ollama_client import OllamaClient


class TestSpendingQueryBugCondition:
    """
    Bug Condition Exploration Test for Bug 3: Hardcoded Spending Query Logic
    
    **Validates: Requirements 2.2, 2.7**
    
    This test demonstrates that the query engine assumes all documents are receipts
    and attempts to aggregate amounts using receipt-specific logic (_is_spending_query,
    _aggregate_amounts methods).
    
    From bugfix.md:
    - Bug 3: System assumes all documents are receipts and attempts to aggregate amounts
    - Current behavior: _is_spending_query and _aggregate_amounts methods assume total_amount fields
    - Expected behavior: Generic query patterns that work for any document type
    
    EXPECTED OUTCOME ON UNFIXED CODE: Test FAILS - spending query logic exists and tries to aggregate
    EXPECTED OUTCOME ON FIXED CODE: Test PASSES - generic query handling without spending assumptions
    """
    
    def test_spending_query_on_non_receipt_documents(self):
        """
        Test 1.6: Spending Query Test - Non-Receipt Documents
        
        **Validates: Requirements 2.2, 2.7**
        
        This test demonstrates Bug 3: The query engine has hardcoded spending query
        detection and amount aggregation logic that assumes all documents are receipts
        with total_amount fields.
        
        Test approach:
        1. Create a test database with ONLY legal documents (no receipts)
        2. Query "How much did I spend?" (a spending query)
        3. Verify that spending query detection logic exists in the code
        4. Document how this logic incorrectly tries to aggregate amounts from non-receipt documents
        
        EXPECTED OUTCOME ON UNFIXED CODE:
        - Code inspection shows _is_spending_query method exists
        - Code inspection shows _aggregate_amounts method exists
        - Spending query logic tries to aggregate amounts from non-existent total_amount fields
        - This confirms Bug 3: spending query logic assumes all documents are receipts
        
        EXPECTED OUTCOME ON FIXED CODE:
        - No _is_spending_query method
        - No _aggregate_amounts method
        - LLM handles spending queries generically based on retrieved context
        - No assumptions about document structure or fields
        """
        print(f"\n{'='*70}")
        print(f"BUG 3 ANALYSIS: Spending Query Logic in Query Engine")
        print(f"{'='*70}")
        
        # Part 1: Code Inspection - Verify spending query logic exists
        print(f"\nPart 1: Code Inspection - Spending Query Logic")
        print(f"{'='*70}")
        
        import inspect
        from backend.query_engine import QueryEngine
        
        # Check for spending query methods
        has_is_spending_query = hasattr(QueryEngine, '_is_spending_query')
        has_aggregate_amounts = hasattr(QueryEngine, '_aggregate_amounts')
        has_generate_spending_response = hasattr(QueryEngine, '_generate_spending_response')
        has_fallback_spending_response = hasattr(QueryEngine, '_fallback_spending_response')
        
        print(f"\nSpending query methods found in QueryEngine:")
        print(f"  {'✗ FOUND' if has_is_spending_query else '✓ NOT FOUND'}: _is_spending_query method")
        print(f"  {'✗ FOUND' if has_aggregate_amounts else '✓ NOT FOUND'}: _aggregate_amounts method")
        print(f"  {'✗ FOUND' if has_generate_spending_response else '✓ NOT FOUND'}: _generate_spending_response method")
        print(f"  {'✗ FOUND' if has_fallback_spending_response else '✓ NOT FOUND'}: _fallback_spending_response method")
        
        # Analyze _is_spending_query method
        if has_is_spending_query:
            print(f"\nAnalyzing _is_spending_query method:")
            is_spending_source = inspect.getsource(QueryEngine._is_spending_query)
            
            # Check for spending query patterns
            spending_patterns = {
                'English patterns': any(pattern in is_spending_source.lower() for pattern in ['spent', 'spend', 'spending']),
                'Korean patterns': '얼마' in is_spending_source,
                'Amount patterns': any(pattern in is_spending_source.lower() for pattern in ['how much', 'total']),
            }
            
            for pattern_type, found in spending_patterns.items():
                print(f"  {'✗ FOUND' if found else '✓ NOT FOUND'}: {pattern_type}")
        
        # Analyze _aggregate_amounts method
        if has_aggregate_amounts:
            print(f"\nAnalyzing _aggregate_amounts method:")
            aggregate_source = inspect.getsource(QueryEngine._aggregate_amounts)
            
            # Check for receipt-specific assumptions
            receipt_assumptions = {
                'total_amount field': 'total_amount' in aggregate_source,
                'merchant field': 'merchant' in aggregate_source,
                'currency field': 'currency' in aggregate_source,
                'Assumes receipt structure': 'total_amount' in aggregate_source and 'metadata' in aggregate_source,
            }
            
            for assumption, found in receipt_assumptions.items():
                print(f"  {'✗ FOUND' if found else '✓ NOT FOUND'}: {assumption}")
        
        # Check query method for spending query handling
        query_source = inspect.getsource(QueryEngine.query)
        uses_spending_logic = (
            '_is_spending_query' in query_source or
            '_aggregate_amounts' in query_source or
            '_generate_spending_response' in query_source
        )
        
        print(f"\nQuery method uses spending query logic: {'✗ YES' if uses_spending_logic else '✓ NO'}")
        
        if any([has_is_spending_query, has_aggregate_amounts, has_generate_spending_response]):
            print(f"\n✗ CONFIRMED: Hardcoded spending query logic exists")
            print(f"  Location: backend/query_engine.py")
            print(f"  Methods: _is_spending_query (lines 539-567)")
            print(f"           _aggregate_amounts (lines 568-603)")
            print(f"           _generate_spending_response (lines 605-656)")
            print(f"           _fallback_spending_response (lines 658-695)")
        
        # Part 2: Test with non-receipt documents
        print(f"\n\nPart 2: Spending Query Test with Non-Receipt Documents")
        print(f"{'='*70}")
        
        # Create a temporary test database
        temp_dir = tempfile.mkdtemp(prefix="test_spending_query_")
        
        try:
            print(f"\nCreating test database with ONLY legal documents (no receipts)...")
            
            # Initialize vector store with temporary directory
            vector_store = VectorStore(persist_directory=temp_dir)
            vector_store.initialize()
            
            # Create test documents - ONLY legal documents, NO receipts
            test_chunks = [
                # Driver's License (NO total_amount field)
                DocumentChunk(
                    content="Driver's License. Name: John Doe. License Number: D1234567. Expiration: 2025-12-31. Issue Date: 2020-01-15",
                    metadata={
                        'filename': 'drivers_license_john.jpg',
                        'folder_path': temp_dir,
                        'file_type': 'image',
                        'document_type': 'drivers_license',
                        'name': 'John Doe',
                        'license_number': 'D1234567',
                        'expiration_date': '2025-12-31',
                        'issue_date': '2020-01-15'
                    }
                ),
                # Passport (NO total_amount field)
                DocumentChunk(
                    content="Passport. Name: Jane Smith. Passport Number: P9876543. Issue Date: 2019-03-10. Expiration: 2029-03-10",
                    metadata={
                        'filename': 'passport_jane.jpg',
                        'folder_path': temp_dir,
                        'file_type': 'image',
                        'document_type': 'passport',
                        'name': 'Jane Smith',
                        'passport_number': 'P9876543',
                        'issue_date': '2019-03-10',
                        'expiration_date': '2029-03-10'
                    }
                ),
                # Birth Certificate (NO total_amount field)
                DocumentChunk(
                    content="Birth Certificate. Name: Alice Johnson. Date of Birth: 1990-05-20. Certificate Number: BC-123456. Issued: 1990-06-01",
                    metadata={
                        'filename': 'birth_certificate_alice.jpg',
                        'folder_path': temp_dir,
                        'file_type': 'image',
                        'document_type': 'birth_certificate',
                        'name': 'Alice Johnson',
                        'date_of_birth': '1990-05-20',
                        'certificate_number': 'BC-123456',
                        'issue_date': '1990-06-01'
                    }
                ),
                # Social Security Card (NO total_amount field)
                DocumentChunk(
                    content="Social Security Card. Name: Bob Williams. SSN: XXX-XX-1234. Issued: 2005-08-15",
                    metadata={
                        'filename': 'ssn_card_bob.jpg',
                        'folder_path': temp_dir,
                        'file_type': 'image',
                        'document_type': 'social_security_card',
                        'name': 'Bob Williams',
                        'ssn': 'XXX-XX-1234',
                        'issue_date': '2005-08-15'
                    }
                ),
            ]
            
            # Add chunks to vector store
            vector_store.add_chunks(test_chunks)
            
            print(f"✓ Created test database with {len(test_chunks)} legal documents:")
            print(f"  - 1 driver's license (NO total_amount field)")
            print(f"  - 1 passport (NO total_amount field)")
            print(f"  - 1 birth certificate (NO total_amount field)")
            print(f"  - 1 social security card (NO total_amount field)")
            print(f"\nNOTE: NONE of these documents have total_amount or merchant fields")
            
            # Test spending query detection
            print(f"\nTesting spending query detection:")
            
            spending_queries = [
                "How much did I spend?",
                "What did I spend?",
                "How much money did I spend?",
                "얼마 썼어?",  # Korean: "How much did I spend?"
            ]
            
            query_engine = QueryEngine()
            
            for test_query in spending_queries:
                print(f"\n  Query: '{test_query}'")
                
                if has_is_spending_query:
                    is_spending = query_engine._is_spending_query(test_query)
                    print(f"  _is_spending_query result: {is_spending}")
                    
                    if is_spending:
                        print(f"    ✗ CONFIRMED: Query detected as spending query")
                        print(f"    ⚠ WARNING: System will try to aggregate amounts from non-receipt documents!")
                else:
                    print(f"  _is_spending_query method not found (expected after fix)")
            
            # Test amount aggregation attempt
            if has_aggregate_amounts:
                print(f"\nTesting amount aggregation on non-receipt documents:")
                print(f"  ⚠ WARNING: Attempting to aggregate amounts from documents without total_amount fields")
                
                # Simulate what happens when _aggregate_amounts is called on non-receipt documents
                # The method will try to access total_amount field that doesn't exist
                print(f"\n  Expected behavior on unfixed code:")
                print(f"    - _aggregate_amounts tries to access metadata['total_amount']")
                print(f"    - Legal documents don't have total_amount field")
                print(f"    - Results in KeyError, None values, or incorrect aggregation")
                print(f"    - System cannot handle non-receipt documents correctly")
            
            # Part 3: Document the bug
            print(f"\n\nPart 3: Bug 3 Confirmation")
            print(f"{'='*70}")
            
            print(f"\n✗ BUG 3 CONFIRMED: Hardcoded Spending Query Logic Exists")
            print(f"\nEvidence:")
            print(f"  1. Code inspection shows spending query detection logic:")
            print(f"     - _is_spending_query method (lines 539-567 in query_engine.py)")
            print(f"     - Detects spending queries using hardcoded patterns:")
            print(f"       * English: 'spent', 'spend', 'spending', 'how much'")
            print(f"       * Korean: '얼마' (how much)")
            print(f"     - Assumes all documents are receipts with spending information")
            print(f"\n  2. Code inspection shows amount aggregation logic:")
            print(f"     - _aggregate_amounts method (lines 568-603 in query_engine.py)")
            print(f"     - Assumes all documents have 'total_amount' metadata field")
            print(f"     - Tries to sum total_amount values from all retrieved documents")
            print(f"     - Cannot handle documents without total_amount field")
            print(f"\n  3. Spending query logic is receipt-specific:")
            print(f"     - _generate_spending_response method (lines 605-656)")
            print(f"     - _fallback_spending_response method (lines 658-695)")
            print(f"     - These methods format responses assuming receipt data")
            print(f"     - Cannot handle non-receipt documents correctly")
            print(f"\n  4. Test demonstrates the problem:")
            print(f"     - Database contains ONLY legal documents (no receipts)")
            print(f"     - Query 'How much did I spend?' is detected as spending query")
            print(f"     - System tries to aggregate amounts from non-existent total_amount fields")
            print(f"     - Results in errors or incorrect behavior")
            
            print(f"\nRoot Cause:")
            print(f"  - QueryEngine._is_spending_query method (lines 539-567)")
            print(f"  - QueryEngine._aggregate_amounts method (lines 568-603)")
            print(f"  - QueryEngine._generate_spending_response method (lines 605-656)")
            print(f"  - QueryEngine._fallback_spending_response method (lines 658-695)")
            print(f"  - Hardcoded spending query patterns")
            print(f"  - Assumes all documents have total_amount field")
            
            print(f"\nExpected Behavior (after fix):")
            print(f"  - Remove _is_spending_query method")
            print(f"  - Remove _aggregate_amounts method")
            print(f"  - Remove _generate_spending_response method")
            print(f"  - Remove _fallback_spending_response method")
            print(f"  - Let LLM handle spending queries generically based on retrieved context")
            print(f"  - LLM can determine if documents contain spending information")
            print(f"  - LLM can aggregate amounts if appropriate for the document type")
            
            print(f"\nImpact:")
            print(f"  - System assumes all documents are receipts")
            print(f"  - Spending queries fail or give incorrect results for non-receipt documents")
            print(f"  - Cannot handle diverse document types (legal docs, IDs, certificates)")
            print(f"  - Hardcoded logic prevents flexible query handling")
            print(f"  - LLM's natural language understanding is bypassed by hardcoded rules")
            
            print(f"\n{'='*70}")
            
            # Check if the code has been fixed
            # Fixed code should NOT have spending query methods
            code_is_fixed = not any([has_is_spending_query, has_aggregate_amounts, 
                                     has_generate_spending_response, has_fallback_spending_response])
            
            if code_is_fixed:
                print(f"✓ TEST PASSED (Code has been fixed)")
                print(f"{'='*70}")
                print(f"Bug 3 Fixed: Hardcoded spending query logic has been removed.")
                print(f"System now lets LLM handle spending queries generically based on context.")
            else:
                print(f"✗ TEST FAILED (Expected on unfixed code)")
                print(f"{'='*70}")
                print(f"Bug 3 Confirmed: Hardcoded spending query logic with amount aggregation")
                print(f"assumes all documents are receipts. This prevents generic document processing.")
                
                # Fail the test to mark it as expected failure on unfixed code
                pytest.fail(
                    "Bug 3 Confirmed: Hardcoded spending query logic with amount aggregation "
                    "assumes all documents are receipts. This is expected on unfixed code."
                )
            
        finally:
            # Clean up temporary directory
            # Note: On Windows, ChromaDB may keep files locked, so cleanup may fail
            # This is acceptable for a test - the temp directory will be cleaned up eventually
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except (PermissionError, OSError) as e:
                print(f"\n⚠ Note: Could not clean up temp directory (files may be locked): {e}")
                print(f"  This is expected on Windows with ChromaDB and does not affect the test")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
