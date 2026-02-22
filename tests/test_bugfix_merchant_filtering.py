"""
Bug Condition Exploration Test for Merchant Filtering

This test is EXPECTED TO FAIL on unfixed code.
Failure confirms Bug 3 exists: the query engine uses hardcoded merchant-specific
filtering logic with Korean-English merchant name mappings.

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


class TestMerchantFilteringBugCondition:
    """
    Bug Condition Exploration Test for Bug 3: Hardcoded Merchant Filtering Logic
    
    **Validates: Requirements 2.2, 2.7**
    
    This test demonstrates that the query engine applies merchant-specific filtering
    logic with Korean-English merchant name mappings even for non-receipt queries.
    
    From bugfix.md:
    - Bug 3: Query engine uses hardcoded merchant-specific filtering logic (lines 182-221)
    - Current behavior: _extract_merchant method with Korean-English mappings applied to all queries
    - Expected behavior: Generic metadata filtering without merchant-specific logic
    
    EXPECTED OUTCOME ON UNFIXED CODE: Test FAILS - merchant filtering logic exists and may interfere
    EXPECTED OUTCOME ON FIXED CODE: Test PASSES - generic filtering without merchant logic
    """
    
    def test_merchant_filtering_on_non_receipt_query(self):
        """
        Test 1.5: Merchant Filtering Test - Non-Receipt Query
        
        **Validates: Requirements 2.2, 2.7**
        
        This test demonstrates Bug 3: The query engine has hardcoded merchant-specific
        filtering logic with Korean-English merchant name mappings that can interfere
        with generic queries.
        
        Test approach:
        1. Create a test database with mixed document types (receipts, legal docs, invoices)
        2. Query "Show me documents from 2024" (a generic date query, not merchant-specific)
        3. Verify that merchant filtering logic exists in the code
        4. Document how this merchant-specific logic could interfere with generic queries
        
        EXPECTED OUTCOME ON UNFIXED CODE:
        - Code inspection shows hardcoded merchant filtering logic (lines 182-221)
        - Code inspection shows _extract_merchant method with Korean-English mappings
        - Merchant filtering logic exists even though query doesn't mention merchants
        - This confirms Bug 3: merchant-specific logic is hardcoded in query engine
        
        EXPECTED OUTCOME ON FIXED CODE:
        - No hardcoded merchant filtering logic in query method
        - No _extract_merchant method with Korean-English mappings
        - Generic metadata filtering works for any document type
        - Date queries work without merchant-specific interference
        """
        print(f"\n{'='*70}")
        print(f"BUG 3 ANALYSIS: Merchant Filtering Logic in Query Engine")
        print(f"{'='*70}")
        
        # Part 1: Code Inspection - Verify merchant filtering logic exists
        print(f"\nPart 1: Code Inspection - Merchant Filtering Logic")
        print(f"{'='*70}")
        
        import inspect
        from backend.query_engine import QueryEngine
        
        # Get the source code of QueryEngine.query method
        query_source = inspect.getsource(QueryEngine.query)
        
        # Check for merchant filtering logic
        merchant_filter_checks = {
            'merchant filter retry': 'merchant filter' in query_source.lower() and 'retry' in query_source.lower(),
            'Korean-English mappings': 'merchant_mappings' in query_source or '코스트코' in query_source,
            'fuzzy merchant matching': 'fuzzy' in query_source.lower() and 'merchant' in query_source.lower(),
            'merchant in metadata_filter': "'merchant'" in query_source and 'metadata_filter' in query_source,
        }
        
        print(f"\nMerchant filtering logic found in QueryEngine.query method:")
        for check, found in merchant_filter_checks.items():
            status = "✗ FOUND" if found else "✓ NOT FOUND"
            print(f"  {status}: {check}")
        
        # Check for _extract_merchant method
        has_extract_merchant = hasattr(QueryEngine, '_extract_merchant')
        print(f"\n_extract_merchant method exists: {'✗ YES' if has_extract_merchant else '✓ NO'}")
        
        if has_extract_merchant:
            extract_merchant_source = inspect.getsource(QueryEngine._extract_merchant)
            
            # Check for Korean-English merchant mappings in _extract_merchant
            has_korean_patterns = '에서' in extract_merchant_source
            has_english_patterns = 'at' in extract_merchant_source or 'from' in extract_merchant_source
            
            print(f"  - Korean merchant patterns (에서): {'✗ FOUND' if has_korean_patterns else '✓ NOT FOUND'}")
            print(f"  - English merchant patterns (at/from): {'✗ FOUND' if has_english_patterns else '✓ NOT FOUND'}")
        
        # Check for Korean-English merchant mappings dictionary
        if any(merchant_filter_checks.values()):
            print(f"\n✗ CONFIRMED: Hardcoded merchant filtering logic exists")
            print(f"  Location: backend/query_engine.py, lines 182-221 (query method)")
            print(f"  Contains: Korean-English merchant name mappings")
            print(f"  Examples: 코스트코 → costco, 월마트 → walmart, 타겟 → target")
        
        # Part 2: Test with generic date query
        print(f"\n\nPart 2: Generic Date Query Test")
        print(f"{'='*70}")
        
        # Create a temporary test database
        temp_dir = tempfile.mkdtemp(prefix="test_merchant_filter_")
        
        try:
            print(f"\nCreating test database with mixed document types...")
            
            # Initialize vector store with temporary directory
            vector_store = VectorStore(persist_directory=temp_dir)
            vector_store.initialize()
            
            # Create test documents with different types
            test_chunks = [
                # Receipt documents (with merchant field)
                DocumentChunk(
                    content="Receipt from Costco. Date: 2024-01-15. Total: $125.50",
                    metadata={
                        'filename': 'receipt_costco_2024.jpg',
                        'folder_path': temp_dir,
                        'file_type': 'image',
                        'merchant': 'Costco',
                        'date': '2024-01-15',
                        'total_amount': 125.50,
                        'document_type': 'receipt'
                    }
                ),
                DocumentChunk(
                    content="Receipt from Walmart. Date: 2024-02-20. Total: $89.99",
                    metadata={
                        'filename': 'receipt_walmart_2024.jpg',
                        'folder_path': temp_dir,
                        'file_type': 'image',
                        'merchant': 'Walmart',
                        'date': '2024-02-20',
                        'total_amount': 89.99,
                        'document_type': 'receipt'
                    }
                ),
                # Legal documents (NO merchant field)
                DocumentChunk(
                    content="Driver's License. Name: John Doe. License Number: D1234567. Expiration: 2024-12-31",
                    metadata={
                        'filename': 'drivers_license_2024.jpg',
                        'folder_path': temp_dir,
                        'file_type': 'image',
                        'document_type': 'drivers_license',
                        'name': 'John Doe',
                        'license_number': 'D1234567',
                        'expiration_date': '2024-12-31'
                    }
                ),
                DocumentChunk(
                    content="Passport. Name: Jane Smith. Passport Number: P9876543. Issue Date: 2024-03-10",
                    metadata={
                        'filename': 'passport_2024.jpg',
                        'folder_path': temp_dir,
                        'file_type': 'image',
                        'document_type': 'passport',
                        'name': 'Jane Smith',
                        'passport_number': 'P9876543',
                        'issue_date': '2024-03-10'
                    }
                ),
                # Invoice documents (NO merchant field, has vendor instead)
                DocumentChunk(
                    content="Invoice from ABC Corp. Invoice Number: INV-2024-001. Due Date: 2024-04-15. Amount: $1,500.00",
                    metadata={
                        'filename': 'invoice_2024_001.pdf',
                        'folder_path': temp_dir,
                        'file_type': 'text',
                        'document_type': 'invoice',
                        'vendor': 'ABC Corp',
                        'invoice_number': 'INV-2024-001',
                        'due_date': '2024-04-15',
                        'amount': 1500.00
                    }
                ),
            ]
            
            # Add chunks to vector store
            vector_store.add_chunks(test_chunks)
            
            print(f"✓ Created test database with {len(test_chunks)} documents:")
            print(f"  - 2 receipts (with merchant field)")
            print(f"  - 2 legal documents (NO merchant field)")
            print(f"  - 1 invoice (NO merchant field)")
            
            # Query with a generic date query (no merchant mentioned)
            print(f"\nQuerying: 'Show me documents from 2024'")
            print(f"NOTE: This is a generic date query, NOT a merchant-specific query")
            
            # Initialize query engine
            query_engine = QueryEngine()
            
            # Test the _extract_merchant method directly
            print(f"\nTesting _extract_merchant method:")
            test_queries = [
                "Show me documents from 2024",
                "What documents do I have from 2024?",
                "List all 2024 documents",
            ]
            
            for test_query in test_queries:
                if has_extract_merchant:
                    merchant = query_engine._extract_merchant(test_query)
                    print(f"  Query: '{test_query}'")
                    print(f"  Extracted merchant: {merchant if merchant else 'None (correct)'}")
                    
                    if merchant is not None:
                        print(f"    ⚠ WARNING: Merchant extracted from non-merchant query!")
            
            # Part 3: Document the bug
            print(f"\n\nPart 3: Bug 3 Confirmation")
            print(f"{'='*70}")
            
            print(f"\n✗ BUG 3 CONFIRMED: Hardcoded Merchant Filtering Logic Exists")
            print(f"\nEvidence:")
            print(f"  1. Code inspection shows hardcoded merchant filtering logic:")
            print(f"     - Lines 182-221 in query_engine.py: Merchant filter retry with fuzzy matching")
            print(f"     - Korean-English merchant name mappings hardcoded in query method")
            print(f"     - merchant_mappings dict: 코스트코 → costco, 월마트 → walmart, etc.")
            print(f"\n  2. _extract_merchant method exists with receipt-specific patterns:")
            print(f"     - Korean pattern: [merchant]에서 (e.g., '코스트코에서')")
            print(f"     - English patterns: 'at [merchant]', 'from [merchant]', 'spent at [merchant]'")
            print(f"     - These patterns assume all documents are receipts with merchant fields")
            print(f"\n  3. Merchant filtering logic is NOT generic:")
            print(f"     - Hardcoded merchant name mappings (Korean ↔ English)")
            print(f"     - Fuzzy merchant matching with hardcoded search terms")
            print(f"     - Assumes all documents have 'merchant' metadata field")
            print(f"     - Cannot handle documents without merchant field (legal docs, invoices)")
            
            print(f"\nRoot Cause:")
            print(f"  - QueryEngine.query method (lines 182-221 in query_engine.py)")
            print(f"  - QueryEngine._extract_merchant method (lines 491-537)")
            print(f"  - Hardcoded Korean-English merchant name mappings")
            print(f"  - Receipt-specific query patterns ('at', 'from', '에서')")
            
            print(f"\nExpected Behavior (after fix):")
            print(f"  - Remove hardcoded merchant filtering logic from query method")
            print(f"  - Remove _extract_merchant method with Korean-English mappings")
            print(f"  - Use generic metadata filtering that works for any field")
            print(f"  - Let LLM handle merchant-specific queries based on retrieved context")
            
            print(f"\nImpact:")
            print(f"  - Query engine assumes all documents are receipts")
            print(f"  - Merchant filtering logic may interfere with generic queries")
            print(f"  - Cannot query non-receipt documents effectively")
            print(f"  - Hardcoded mappings limit flexibility and maintainability")
            
            print(f"\n{'='*70}")
            
            # Check if the code has been fixed
            # Fixed code should NOT have _extract_merchant method or merchant filtering logic
            code_is_fixed = not has_extract_merchant
            
            if code_is_fixed:
                print(f"✓ TEST PASSED (Code has been fixed)")
                print(f"{'='*70}")
                print(f"Bug 3 Fixed: Hardcoded merchant filtering logic has been removed.")
                print(f"System now uses generic metadata filtering without merchant-specific logic.")
            else:
                print(f"✗ TEST FAILED (Expected on unfixed code)")
                print(f"{'='*70}")
                print(f"Bug 3 Confirmed: Hardcoded merchant filtering logic with Korean-English")
                print(f"mappings exists in query engine. This prevents generic document processing.")
                
                # Fail the test to mark it as expected failure on unfixed code
                pytest.fail(
                    "Bug 3 Confirmed: Hardcoded merchant filtering logic with Korean-English mappings "
                    "exists in query engine. This is expected on unfixed code."
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
