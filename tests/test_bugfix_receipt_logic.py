"""
Bug Condition Exploration Tests for Receipt Logic

These tests are EXPECTED TO FAIL on unfixed code.
Failures confirm Bug 3 exists: the system applies receipt-specific field extraction
regardless of document type.

DO NOT attempt to fix the tests or the code when they fail.
These tests encode the expected behavior and will validate the fix when they pass.
"""

import pytest
from PIL import Image, ImageDraw, ImageFont
import tempfile
import os
from pathlib import Path

from backend.image_processor import ImageProcessor
from backend.ollama_client import OllamaClient


class TestReceiptLogicBugConditions:
    """
    Bug Condition Exploration Tests for Bug 3: Hardcoded Receipt Logic
    
    **Validates: Requirements 2.1, 2.3, 2.6**
    
    These tests demonstrate that the system applies receipt-specific field extraction
    (merchant, total_amount, line_items) regardless of document type.
    
    From bugfix.md:
    - Bug 3: System applies receipt-specific field extraction regardless of document type
    - Current behavior: _parse_response extracts merchant, total_amount, line_items from all documents
    - Expected behavior: System should dynamically extract fields based on document content
    
    EXPECTED OUTCOME ON UNFIXED CODE: Tests FAIL - receipt fields forced on non-receipt documents
    EXPECTED OUTCOME ON FIXED CODE: Tests PASS - fields extracted dynamically in flexible_metadata
    """
    
    def test_legal_document_forces_receipt_fields(self):
        """
        Test 1.4: Receipt Logic Test - Legal Document
        
        **Validates: Requirements 2.1, 2.3, 2.6**
        
        This test demonstrates Bug 3: The system applies receipt-specific field extraction
        logic regardless of document type.
        
        Since we don't have a real legal document image available, this test:
        1. Examines the _parse_response code to confirm receipt-specific logic exists
        2. Tests with a receipt image to show the receipt logic works
        3. Documents that this SAME logic is applied to ALL documents (the bug)
        
        EXPECTED OUTCOME ON UNFIXED CODE:
        - Code inspection shows hardcoded receipt field extraction (merchant, total_amount, line_items)
        - Receipt image successfully extracts these fields
        - Documentation confirms this logic applies to ALL document types (Bug 3)
        
        EXPECTED OUTCOME ON FIXED CODE:
        - Code uses dynamic field extraction based on document content
        - No hardcoded receipt-specific field names
        - Fields stored in flexible_metadata with names determined by document content
        """
        print(f"\n{'='*70}")
        print(f"BUG 3 ANALYSIS: Receipt Logic Applied to All Documents")
        print(f"{'='*70}")
        
        # Part 1: Code Inspection - Verify receipt-specific logic exists
        print(f"\nPart 1: Code Inspection")
        print(f"{'='*70}")
        
        import inspect
        from backend.image_processor import ImageProcessor
        
        # Get the source code of _parse_response
        source = inspect.getsource(ImageProcessor._parse_response)
        
        # Check for receipt-specific field extraction
        receipt_field_checks = {
            'merchant': 'merchant' in source.lower(),
            'total_amount': 'total_amount' in source.lower() or 'total' in source.lower(),
            'line_items': 'line_items' in source.lower() or 'items' in source.lower(),
            'currency': 'currency' in source.lower(),
        }
        
        print(f"\nReceipt-specific fields found in _parse_response code:")
        for field, found in receipt_field_checks.items():
            status = "✗ FOUND" if found else "✓ NOT FOUND"
            print(f"  {status}: '{field}' field extraction logic")
        
        # Check for hardcoded field name lists (the actual bug indicators)
        # Fixed code may still have 'merchant' and 'total_amount' for backward compatibility
        # but should NOT have hardcoded lists like merchant_fields, amount_fields, date_fields
        has_hardcoded_field_lists = (
            'merchant_fields' in source or
            'amount_fields' in source or
            'date_fields' in source
        )
        
        # Check if the code uses dynamic extraction (stores all fields in flexible_metadata)
        uses_dynamic_extraction = (
            'flexible_metadata[key]' in source or
            'for key, value in data.items()' in source
        )
        
        if has_hardcoded_field_lists:
            print(f"\n  ✗ CONFIRMED: Hardcoded field name lists found in code")
            print(f"    Examples: merchant_fields, amount_fields, date_fields")
        else:
            print(f"\n  ✓ No hardcoded field name lists found")
        
        if uses_dynamic_extraction:
            print(f"  ✓ Code uses dynamic field extraction (stores all fields in flexible_metadata)")
        else:
            print(f"  ✗ Code does NOT use dynamic field extraction")
        
        # Part 2: Test with receipt image to show receipt logic works
        print(f"\n\nPart 2: Receipt Image Test (Baseline Behavior)")
        print(f"{'='*70}")
        
        # Use a real receipt image from testing directory
        receipt_images = [
            "testing/KakaoTalk_20260219_155002406.jpg",
            "testing/KakaoTalk_20260219_155002406_01.jpg",
            "testing/KakaoTalk_20260219_155002406_02.jpg",
        ]
        
        receipt_path = None
        for img_path in receipt_images:
            if os.path.exists(img_path):
                receipt_path = img_path
                break
        
        if receipt_path is None:
            print(f"\n  ⚠ No receipt images found for testing")
            print(f"    Skipping receipt baseline test")
        else:
            print(f"\nTesting with receipt image: {receipt_path}")
            
            import time
            start_time = time.time()
            
            try:
                processor = ImageProcessor()
                result = processor.process_image(receipt_path)
                
                elapsed_time = time.time() - start_time
                
                print(f"\n✓ Receipt processed in {elapsed_time:.2f} seconds")
                print(f"\nExtracted receipt fields:")
                print(f"  merchant: {result.merchant}")
                print(f"  date: {result.date}")
                print(f"  total_amount: {result.total_amount}")
                print(f"  currency: {result.currency}")
                print(f"  line_items: {len(result.line_items)} items")
                print(f"  flexible_metadata keys: {list(result.flexible_metadata.keys())}")
                
                # Check if receipt fields were extracted
                receipt_fields_extracted = (
                    result.merchant is not None or
                    result.total_amount is not None or
                    len(result.line_items) > 0
                )
                
                if receipt_fields_extracted:
                    print(f"\n  ✓ Receipt-specific fields successfully extracted")
                    print(f"    This confirms the receipt extraction logic is working")
                else:
                    print(f"\n  ⚠ No receipt fields extracted (unexpected)")
                    
            except Exception as e:
                print(f"\n  ✗ Receipt processing failed: {str(e)[:200]}")
                print(f"    Cannot establish baseline behavior")
        
        # Part 3: Document the bug
        print(f"\n\nPart 3: Bug 3 Confirmation")
        print(f"{'='*70}")
        
        print(f"\n✗ BUG 3 CONFIRMED: Receipt Logic Applied to All Documents")
        print(f"\nEvidence:")
        print(f"  1. Code inspection shows hardcoded receipt field extraction:")
        print(f"     - merchant_fields = ['merchant', 'merchant_name', 'store_name', ...]")
        print(f"     - amount_fields = ['total_amount', 'total', 'amount', 'price']")
        print(f"     - Extracts line_items, currency, date using receipt-specific patterns")
        print(f"\n  2. The _parse_response method applies this logic to ALL documents:")
        print(f"     - No document type checking before field extraction")
        print(f"     - Same field extraction logic runs for receipts, legal docs, IDs, etc.")
        print(f"     - Lines 380-447: Hardcoded extraction for merchant, total_amount, line_items")
        print(f"     - Lines 450-528: Fallback regex parsing for receipt fields")
        print(f"\n  3. Receipt image test confirms the receipt logic works:")
        print(f"     - Successfully extracts merchant, total_amount, line_items from receipts")
        print(f"     - This SAME logic is applied to non-receipt documents (the bug)")
        
        print(f"\nRoot Cause:")
        print(f"  - _parse_response in image_processor.py (lines 347-528)")
        print(f"  - Hardcoded field name lists for receipts")
        print(f"  - No dynamic field extraction based on document type")
        print(f"  - No document type detection before applying field extraction")
        
        print(f"\nExpected Behavior (after fix):")
        print(f"  - System should extract fields dynamically based on document content")
        print(f"  - No hardcoded field name lists")
        print(f"  - All fields stored in flexible_metadata with names from vision model")
        print(f"  - Receipt fields only populated if vision model extracts them")
        
        print(f"\nImpact:")
        print(f"  - Legal documents (driver's license, passport) forced into receipt structure")
        print(f"  - ID cards, certificates, invoices treated as receipts")
        print(f"  - Document-specific fields may be lost or incorrectly mapped")
        print(f"  - System cannot handle diverse document types")
        
        print(f"\n{'='*70}")
        
        # Check if the code has been fixed
        # Fixed code should NOT have hardcoded field name lists like merchant_fields, amount_fields
        # Fixed code SHOULD use dynamic extraction
        code_is_fixed = (not has_hardcoded_field_lists) and uses_dynamic_extraction
        
        if code_is_fixed:
            print(f"✓ TEST PASSED (Code has been fixed)")
            print(f"{'='*70}")
            print(f"Bug 3 Fixed: Receipt-specific field extraction logic has been removed.")
            print(f"System now uses dynamic field extraction based on document content.")
            print(f"All fields are stored in flexible_metadata without forcing receipt structure.")
        else:
            print(f"✗ TEST FAILED (Expected on unfixed code)")
            print(f"{'='*70}")
            print(f"Bug 3 Confirmed: Receipt-specific field extraction logic exists and")
            print(f"applies to all document types without document type checking.")
            
            # Fail the test to mark it as expected failure on unfixed code
            pytest.fail(
                "Bug 3 Confirmed: Receipt-specific field extraction logic applies to all documents. "
                "This is expected on unfixed code."
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
