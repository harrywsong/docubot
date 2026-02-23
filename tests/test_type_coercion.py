"""
Unit tests for type coercion in ImageProcessor.

Tests the _coerce_numeric_types method to ensure numeric string values
are correctly converted to float/int types.
"""

import pytest
from backend.image_processor import ImageProcessor


class TestTypeCoercion:
    """Test suite for numeric type coercion."""

    def test_coerce_numeric_string_to_float(self):
        """Test that numeric string values are converted to float."""
        processor = ImageProcessor()
        fields = {
            'total': '411.89',
            'subtotal': '380.00',
            'tax': '31.89'
        }
        
        result = processor._coerce_numeric_types(fields)
        
        assert isinstance(result['total'], float)
        assert result['total'] == 411.89
        # 380.00 is a whole number, so it's converted to int
        assert isinstance(result['subtotal'], int)
        assert result['subtotal'] == 380
        assert isinstance(result['tax'], float)
        assert result['tax'] == 31.89

    def test_coerce_numeric_string_to_int(self):
        """Test that whole number strings are converted to int."""
        processor = ImageProcessor()
        fields = {
            'quantity': '5.0',
            'total': '100.0'
        }
        
        result = processor._coerce_numeric_types(fields)
        
        assert isinstance(result['quantity'], int)
        assert result['quantity'] == 5
        assert isinstance(result['total'], int)
        assert result['total'] == 100

    def test_coerce_with_currency_symbols(self):
        """Test that currency symbols are stripped before conversion."""
        processor = ImageProcessor()
        fields = {
            'total': '$411.89',
            'price': '$ 25.50'
        }
        
        result = processor._coerce_numeric_types(fields)
        
        assert isinstance(result['total'], float)
        assert result['total'] == 411.89
        assert isinstance(result['price'], float)
        assert result['price'] == 25.50

    def test_coerce_with_commas(self):
        """Test that comma separators are handled correctly."""
        processor = ImageProcessor()
        fields = {
            'total': '1,234.56',
            'amount': '10,000'
        }
        
        result = processor._coerce_numeric_types(fields)
        
        assert isinstance(result['total'], float)
        assert result['total'] == 1234.56
        assert isinstance(result['amount'], int)
        assert result['amount'] == 10000

    def test_non_numeric_fields_unchanged(self):
        """Test that non-numeric fields are kept as strings."""
        processor = ImageProcessor()
        fields = {
            'store': 'Costco',
            'date': '2024-02-08',
            'total': '411.89'
        }
        
        result = processor._coerce_numeric_types(fields)
        
        assert isinstance(result['store'], str)
        assert result['store'] == 'Costco'
        assert isinstance(result['date'], str)
        assert result['date'] == '2024-02-08'
        assert isinstance(result['total'], float)
        assert result['total'] == 411.89

    def test_invalid_numeric_value_kept_as_string(self):
        """Test that invalid numeric values are kept as strings."""
        processor = ImageProcessor()
        fields = {
            'total': 'invalid',
            'price': 'N/A'
        }
        
        result = processor._coerce_numeric_types(fields)
        
        assert isinstance(result['total'], str)
        assert result['total'] == 'invalid'
        assert isinstance(result['price'], str)
        assert result['price'] == 'N/A'

    def test_mixed_fields(self):
        """Test coercion with a mix of numeric and non-numeric fields."""
        processor = ImageProcessor()
        fields = {
            'store': 'Walmart',
            'date': '2024-03-15',
            'total': '156.78',
            'subtotal': '145.00',
            'tax': '11.78',
            'payment_method': 'Credit Card',
            'quantity': '3'
        }
        
        result = processor._coerce_numeric_types(fields)
        
        # Non-numeric fields should remain strings
        assert isinstance(result['store'], str)
        assert isinstance(result['date'], str)
        assert isinstance(result['payment_method'], str)
        
        # Numeric fields should be converted
        assert isinstance(result['total'], float)
        assert result['total'] == 156.78
        # 145.00 is a whole number, so it's converted to int
        assert isinstance(result['subtotal'], int)
        assert result['subtotal'] == 145
        assert isinstance(result['tax'], float)
        assert result['tax'] == 11.78
        assert isinstance(result['quantity'], int)
        assert result['quantity'] == 3

    def test_empty_fields(self):
        """Test that empty dictionary is handled correctly."""
        processor = ImageProcessor()
        fields = {}
        
        result = processor._coerce_numeric_types(fields)
        
        assert result == {}

    def test_all_numeric_field_types(self):
        """Test all supported numeric field types."""
        processor = ImageProcessor()
        fields = {
            'total': '100.00',
            'subtotal': '90.00',
            'tax': '10.00',
            'amount': '100.00',
            'price': '25.50',
            'quantity': '4',
            'discount': '5.00',
            'tip': '15.00',
            'grand_total': '115.00',
            'balance': '50.00',
            'payment_amount': '100.00'
        }
        
        result = processor._coerce_numeric_types(fields)
        
        # All should be converted to numeric types
        for key, value in result.items():
            assert isinstance(value, (int, float)), f"{key} should be numeric"
