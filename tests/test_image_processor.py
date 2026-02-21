"""
Unit tests for image processor module.
"""

import pytest
from unittest.mock import Mock, patch
import tempfile
import os

from backend.image_processor import ImageProcessor, process_image, RECEIPT_EXTRACTION_PROMPT
from backend.ollama_client import OllamaClient, OllamaError
from backend.models import ImageExtraction


class TestImageProcessor:
    """Test image processor functionality."""
    
    def test_init_default_client(self):
        """Test processor initialization with default client."""
        processor = ImageProcessor()
        assert processor.client is not None
        assert isinstance(processor.client, OllamaClient)
    
    def test_init_custom_client(self):
        """Test processor initialization with custom client."""
        custom_client = OllamaClient(endpoint="http://custom:8080")
        processor = ImageProcessor(custom_client)
        assert processor.client == custom_client
    
    @patch('backend.image_processor.encode_image_to_base64')
    def test_process_image_success(self, mock_encode):
        """Test successful image processing."""
        mock_encode.return_value = "base64_image_data"
        
        # Mock Ollama client
        mock_client = Mock()
        mock_client.generate.return_value = {
            "response": "Merchant: Costco\nDate: February 11, 2026\nTotal: $222.18",
            "done": True
        }
        
        processor = ImageProcessor(mock_client)
        result = processor.process_image("/path/to/image.jpg")
        
        # Verify result
        assert isinstance(result, ImageExtraction)
        assert result.merchant == "Costco"
        assert result.date == "February 11, 2026"
        assert result.total_amount == 222.18
        assert result.currency == "USD"
        
        # Verify client was called correctly
        mock_client.generate.assert_called_once()
        call_args = mock_client.generate.call_args
        assert call_args[1]["prompt"] == RECEIPT_EXTRACTION_PROMPT
        assert call_args[1]["images"] == ["base64_image_data"]
        assert call_args[1]["stream"] is False
    
    @patch('backend.image_processor.encode_image_to_base64')
    def test_process_image_ollama_error(self, mock_encode):
        """Test image processing with Ollama error."""
        mock_encode.return_value = "base64_image_data"
        
        # Mock Ollama client that raises error
        mock_client = Mock()
        mock_client.generate.side_effect = OllamaError("Connection failed")
        
        processor = ImageProcessor(mock_client)
        with pytest.raises(OllamaError) as exc_info:
            processor.process_image("/path/to/image.jpg")
        
        assert "Connection failed" in str(exc_info.value)
    
    @patch('backend.image_processor.encode_image_to_base64')
    def test_process_image_file_not_found(self, mock_encode):
        """Test image processing with non-existent file."""
        mock_encode.side_effect = FileNotFoundError("File not found")
        
        processor = ImageProcessor()
        with pytest.raises(FileNotFoundError):
            processor.process_image("/nonexistent/image.jpg")


class TestResponseParsing:
    """Test vision model response parsing."""
    
    def test_parse_response_complete(self):
        """Test parsing complete receipt response."""
        raw_text = """Merchant: Costco
Date: February 11, 2026
Total: $222.18
Line Items:
- Milk: 4.99
- Bread: 3.50
- Eggs: 5.99"""
        
        processor = ImageProcessor()
        result = processor._parse_response(raw_text)
        
        assert result.merchant == "Costco"
        assert result.date == "February 11, 2026"
        assert result.total_amount == 222.18
        assert result.currency == "USD"
        assert len(result.line_items) == 3
        assert result.line_items[0] == {"name": "Milk", "price": 4.99}
        assert result.line_items[1] == {"name": "Bread", "price": 3.50}
        assert result.line_items[2] == {"name": "Eggs", "price": 5.99}
        assert result.raw_text == raw_text
    
    def test_parse_response_with_currency_code(self):
        """Test parsing response with explicit currency code."""
        raw_text = "Merchant: Target\nDate: Jan 1, 2026\nTotal: USD 150.00"
        
        processor = ImageProcessor()
        result = processor._parse_response(raw_text)
        
        assert result.merchant == "Target"
        assert result.total_amount == 150.00
        assert result.currency == "USD"
    
    def test_parse_response_minimal(self):
        """Test parsing response with minimal information."""
        raw_text = "Some receipt text without clear structure"
        
        processor = ImageProcessor()
        result = processor._parse_response(raw_text)
        
        assert result.merchant is None
        assert result.date is None
        assert result.total_amount is None
        assert result.currency is None
        assert len(result.line_items) == 0
        assert result.raw_text == raw_text
    
    def test_parse_response_merchant_variations(self):
        """Test parsing merchant with different formats."""
        test_cases = [
            ("Merchant: Walmart", "Walmart"),
            ("MERCHANT: Target", "Target"),
            ("Merchant Name: Costco", "Costco"),
            ("merchant: Amazon", "Amazon"),
        ]
        
        processor = ImageProcessor()
        for raw_text, expected_merchant in test_cases:
            result = processor._parse_response(raw_text)
            assert result.merchant == expected_merchant
    
    def test_parse_response_date_variations(self):
        """Test parsing date with different formats."""
        test_cases = [
            ("Date: February 11, 2026", "February 11, 2026"),
            ("DATE: 2026-02-11", "2026-02-11"),
            ("Date: Feb 11, 2026", "Feb 11, 2026"),
            ("date: 02/11/2026", "02/11/2026"),
        ]
        
        processor = ImageProcessor()
        for raw_text, expected_date in test_cases:
            result = processor._parse_response(raw_text)
            assert result.date == expected_date
    
    def test_parse_response_total_variations(self):
        """Test parsing total amount with different formats."""
        test_cases = [
            ("Total: $222.18", 222.18, "USD"),
            ("Total: 222.18", 222.18, None),
            ("Total Amount: $50.00", 50.00, "USD"),
            ("TOTAL: $1234.56", 1234.56, "USD"),
            ("Total: USD 100.00", 100.00, "USD"),
        ]
        
        processor = ImageProcessor()
        for raw_text, expected_amount, expected_currency in test_cases:
            result = processor._parse_response(raw_text)
            assert result.total_amount == expected_amount
            assert result.currency == expected_currency
    
    def test_parse_response_line_items_variations(self):
        """Test parsing line items with different formats."""
        raw_text = """Line Items:
- Item A: 10.00
- Item B $20.50
* Item C: $5.99
• Item D 15.00"""
        
        processor = ImageProcessor()
        result = processor._parse_response(raw_text)
        
        assert len(result.line_items) == 4
        assert result.line_items[0]["name"] == "Item A"
        assert result.line_items[0]["price"] == 10.00
        assert result.line_items[1]["name"] == "Item B"
        assert result.line_items[1]["price"] == 20.50
    
    def test_parse_response_empty(self):
        """Test parsing empty response."""
        processor = ImageProcessor()
        result = processor._parse_response("")
        
        assert result.merchant is None
        assert result.date is None
        assert result.total_amount is None
        assert result.currency is None
        assert len(result.line_items) == 0
        assert result.raw_text == ""


class TestConvenienceFunction:
    """Test convenience function."""
    
    @patch('backend.image_processor.encode_image_to_base64')
    def test_process_image_function(self, mock_encode):
        """Test process_image convenience function."""
        mock_encode.return_value = "base64_data"
        
        # Mock client
        mock_client = Mock()
        mock_client.generate.return_value = {
            "response": "Merchant: Test Store\nTotal: $50.00",
            "done": True
        }
        
        result = process_image("/path/to/image.jpg", mock_client)
        
        assert isinstance(result, ImageExtraction)
        assert result.merchant == "Test Store"
        assert result.total_amount == 50.00


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
