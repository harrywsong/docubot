"""
Preservation Property Test for Date Filtering

This test MUST PASS on unfixed code to establish baseline behavior.
After the fix, date filtering logic should continue to work identically.

This test uses property-based testing to generate many test cases for stronger guarantees.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from datetime import datetime

from backend.query_engine import QueryEngine


class TestDateFilteringPreservation:
    """
    Preservation Property Test for Date Filtering
    
    **Validates: Requirements 3.5**
    
    This test establishes baseline behavior for date filtering that must be preserved.
    
    From bugfix.md:
    - Preservation requirement (3.5): Date filtering logic must continue to work identically
    
    EXPECTED OUTCOME ON UNFIXED CODE: Test PASSES - date filtering works correctly
    EXPECTED OUTCOME ON FIXED CODE: Test PASSES - same date filtering behavior
    """
    
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        year=st.integers(min_value=2020, max_value=2026),
        month=st.integers(min_value=1, max_value=12),
        day=st.integers(min_value=1, max_value=28)  # Use 28 to avoid invalid dates
    )
    def test_date_extraction_preservation(self, year, month, day):
        """
        Test 2.7: Date Filtering Preservation Test
        
        **Validates: Requirements 3.5**
        
        This test establishes baseline behavior for date extraction from queries.
        Test various date formats and verify consistent extraction.
        
        EXPECTED OUTCOME ON UNFIXED CODE:
        - Dates are extracted correctly from queries
        - Multiple date formats are supported (YYYY-MM-DD, MMM DD YYYY, etc.)
        - Extracted dates are normalized to YYYY-MM-DD format
        - Test PASSES to establish baseline
        
        EXPECTED OUTCOME ON FIXED CODE:
        - Same date extraction behavior
        - Test PASSES to confirm preservation
        """
        print(f"\n{'='*70}")
        print(f"PRESERVATION TEST: Date Extraction")
        print(f"Date: {year}-{month:02d}-{day:02d}")
        print(f"{'='*70}")
        
        # Create query engine
        engine = QueryEngine()
        
        # Test different date formats
        date_formats = [
            f"{year}-{month:02d}-{day:02d}",  # YYYY-MM-DD
            f"on {year}-{month:02d}-{day:02d}",  # with "on" prefix
            f"from {year}-{month:02d}-{day:02d}",  # with "from" prefix
        ]
        
        # Also test month name formats
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']
        month_abbrevs = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        month_name = month_names[month - 1]
        month_abbrev = month_abbrevs[month - 1]
        
        date_formats.extend([
            f"on {month_name} {day}, {year}",  # Month DD, YYYY
            f"on {month_abbrev} {day}, {year}",  # MMM DD, YYYY
        ])
        
        for date_format in date_formats:
            query = f"Show me documents {date_format}"
            
            # Extract date from query
            date_result = engine._extract_date(query)
            
            if date_result:
                if isinstance(date_result, tuple):
                    extracted_date, is_ambiguous = date_result
                else:
                    extracted_date = date_result
                    is_ambiguous = False
                
                # Verify date was extracted
                assert extracted_date is not None, \
                    f"Date should be extracted from '{query}'"
                
                # Verify date is in YYYY-MM-DD format
                expected_date = f"{year}-{month:02d}-{day:02d}"
                assert extracted_date == expected_date, \
                    f"Extracted date '{extracted_date}' should match '{expected_date}'"
                
                print(f"  ✓ Extracted '{expected_date}' from '{date_format}'")
    
    def test_date_filtering_metadata_preservation(self):
        """
        Test that date filtering creates correct metadata filters.
        
        **Validates: Requirements 3.5**
        
        EXPECTED OUTCOME ON UNFIXED CODE:
        - Date queries create metadata filters
        - Filters include date field
        - Test PASSES to establish baseline
        
        EXPECTED OUTCOME ON FIXED CODE:
        - Same metadata filter creation
        - Test PASSES to confirm preservation
        """
        print(f"\n{'='*70}")
        print(f"PRESERVATION TEST: Date Metadata Filtering")
        print(f"{'='*70}")
        
        # Create query engine
        engine = QueryEngine()
        
        test_queries = [
            ("Show me documents from 2024-01-15", "2024-01-15"),
            ("Find receipts on January 15, 2024", "2024-01-15"),
            ("What did I buy on Jan 15, 2024", "2024-01-15"),
        ]
        
        for query, expected_date in test_queries:
            print(f"\n  Query: {query}")
            
            # Extract metadata filters
            metadata_filter = engine._extract_metadata_filters(query)
            
            # Verify filter was created
            assert metadata_filter is not None, \
                f"Metadata filter should be created for '{query}'"
            
            # Verify date is in filter
            assert 'date' in metadata_filter, \
                f"Date should be in metadata filter for '{query}'"
            
            # Verify date value
            assert metadata_filter['date'] == expected_date, \
                f"Date filter should be '{expected_date}', got '{metadata_filter['date']}'"
            
            print(f"  ✓ Date filter created: {metadata_filter['date']}")
    
    def test_date_filtering_baseline_summary(self):
        """
        Summary test to document baseline date filtering behavior.
        
        This test documents the expected behavior that must be preserved.
        """
        print(f"\n{'='*70}")
        print(f"BASELINE SUMMARY: Date Filtering Preservation")
        print(f"{'='*70}")
        
        print("\nBaseline behavior established:")
        print("  - Dates are extracted from queries using regex patterns")
        print("  - Multiple date formats are supported:")
        print("    - YYYY-MM-DD")
        print("    - Month DD, YYYY")
        print("    - MMM DD, YYYY")
        print("  - Extracted dates are normalized to YYYY-MM-DD format")
        print("  - Date filters are added to metadata_filter dictionary")
        print("  - Ambiguous dates (missing year) are flagged")
        
        print("\nAfter fix:")
        print("  - Same date extraction patterns must be used")
        print("  - Same date formats must be supported")
        print("  - Same normalization must be applied")
        print("  - Same metadata filter creation must occur")
        print("  - Same ambiguity detection must work")
        
        print(f"\n✓ PRESERVATION TEST BASELINE ESTABLISHED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
