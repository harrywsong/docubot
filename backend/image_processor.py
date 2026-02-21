"""
Image processor for extracting content from receipts and invoices.

Uses Ollama vision model (Qwen2.5-VL 7B) to extract structured data
from images.
"""

import re
from typing import Optional
from pathlib import Path

from backend.ollama_client import OllamaClient, OllamaError, encode_image_to_base64
from backend.models import ImageExtraction


# Receipt extraction prompt optimized for Qwen2.5-VL
RECEIPT_EXTRACTION_PROMPT = """Extract the following from this receipt: merchant name, date, total amount, payment method, and all line items with prices. Format as structured text."""


class ImageProcessor:
    """Processor for extracting content from images using vision model."""
    
    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        """
        Initialize image processor.
        
        Args:
            ollama_client: OllamaClient instance (creates new one if None)
        """
        self.client = ollama_client or OllamaClient()
    
    def process_image(self, image_path: str) -> ImageExtraction:
        """
        Process image and extract structured data.
        
        Args:
            image_path: Path to image file
            
        Returns:
            ImageExtraction with extracted data
            
        Raises:
            OllamaError: If processing fails after retry
            FileNotFoundError: If image file doesn't exist
            IOError: If image cannot be read
        """
        # Encode image to base64
        base64_image = encode_image_to_base64(image_path)
        
        # Send to vision model with retry (handled by OllamaClient)
        try:
            response = self.client.generate(
                prompt=RECEIPT_EXTRACTION_PROMPT,
                images=[base64_image],
                stream=False
            )
            
            # Extract response text
            raw_text = response.get("response", "")
            
            # Parse response into ImageExtraction
            extraction = self._parse_response(raw_text)
            
            return extraction
            
        except OllamaError as e:
            # OllamaClient already handles retry logic
            raise OllamaError(f"Failed to process image {image_path}: {str(e)}")
    
    def _parse_response(self, raw_text: str) -> ImageExtraction:
        """
        Parse vision model response into ImageExtraction data class.
        
        Args:
            raw_text: Raw text response from vision model
            
        Returns:
            ImageExtraction with parsed data
        """
        # Initialize with defaults
        merchant = None
        date = None
        total_amount = None
        currency = None
        line_items = []
        
        # Parse merchant
        merchant_match = re.search(
            r'merchant(?:\s+name)?[:\s]+(.+?)(?:\n|$)',
            raw_text,
            re.IGNORECASE
        )
        if merchant_match:
            merchant = merchant_match.group(1).strip()
            # Remove any trailing colons or extra text
            merchant = re.sub(r'\s*:.*$', '', merchant)
        
        # Parse date
        date_match = re.search(
            r'date[:\s]+(.+?)(?:\n|$)',
            raw_text,
            re.IGNORECASE
        )
        if date_match:
            date = date_match.group(1).strip()
        
        # Parse total amount and currency
        # Look for patterns like: "Total: $222.18", "Total: USD 222.18", "Total Amount: 222.18"
        total_match = re.search(
            r'total[^:]*[:\s]+(?:([A-Z]{3})\s*)?\$?(\d+\.?\d*)',
            raw_text,
            re.IGNORECASE
        )
        if total_match:
            if total_match.group(1):
                currency = total_match.group(1)
            else:
                # Check if $ symbol was present
                if '$' in total_match.group(0):
                    currency = "USD"
            
            try:
                total_amount = float(total_match.group(2))
            except ValueError:
                pass
        
        # Parse line items
        # Look for patterns like: "- Item Name: 12.99", "Item Name $12.99", "Item Name: $12.99"
        line_items_section = re.search(
            r'line\s+items[:\s]+(.*?)(?:\n\n|\Z)',
            raw_text,
            re.IGNORECASE | re.DOTALL
        )
        
        if line_items_section:
            items_text = line_items_section.group(1)
            # Match individual line items - strip leading bullets/markers
            item_pattern = r'[-•*]?\s*(.+?)[:|\s]+\$?(\d+\.?\d*)'
            for match in re.finditer(item_pattern, items_text):
                item_name = match.group(1).strip()
                # Remove any leading bullets that might have been captured
                item_name = re.sub(r'^[-•*]\s*', '', item_name)
                try:
                    item_price = float(match.group(2))
                    line_items.append({
                        'name': item_name,
                        'price': item_price
                    })
                except ValueError:
                    continue
        
        return ImageExtraction(
            merchant=merchant,
            date=date,
            total_amount=total_amount,
            currency=currency,
            line_items=line_items,
            raw_text=raw_text
        )


def process_image(image_path: str, ollama_client: Optional[OllamaClient] = None) -> ImageExtraction:
    """
    Convenience function to process an image.
    
    Args:
        image_path: Path to image file
        ollama_client: Optional OllamaClient instance
        
    Returns:
        ImageExtraction with extracted data
        
    Raises:
        OllamaError: If processing fails after retry
        FileNotFoundError: If image file doesn't exist
        IOError: If image cannot be read
    """
    processor = ImageProcessor(ollama_client)
    return processor.process_image(image_path)
