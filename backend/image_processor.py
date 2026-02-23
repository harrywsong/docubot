"""
Image processor for extracting content from various document types.

Uses Ollama vision model (Qwen2.5-VL 7B) to extract structured data
from images including receipts, legal documents, passports, and general documents.
"""

import re
from typing import Optional, Dict
from pathlib import Path

from backend.ollama_client import OllamaClient, OllamaError, encode_image_to_base64
from backend.models import ImageExtraction


# Optimized document extraction prompt for qwen3-vl
# Structured prompt for consistent, concise JSON output with only relevant information
DOCUMENT_EXTRACTION_PROMPT = """Extract key information from this document. Output a JSON object with field names that match the document type.

REQUIRED CANONICAL FIELD NAMES:
You MUST use these exact field names - do NOT use synonyms or variations:
- For store/merchant/vendor/shop: ALWAYS use "store"
- For transaction date/purchase date: ALWAYS use "date"
- For total amount/grand total/amount: ALWAYS use "total"
- For subtotal: ALWAYS use "subtotal"
- For tax amount: ALWAYS use "tax"
- For payment type/card type: ALWAYS use "payment_method"

RULES:
1. Use field names appropriate for the document type
2. Extract each field ONLY ONCE - no duplicates, no translations
3. Maximum 15 fields
4. Choose ONE language per field (English preferred)
5. MUST use canonical field names listed above - no variations allowed

For receipts: store, date, total, subtotal, tax, payment_method
For ID/passport: document_type, name, birth_date, nationality, document_number, issue_date, expiry_date
For other documents: document_type, date, issuer, recipient, reference_number

WRONG (DO NOT DO THIS):
{"merchant": "Costco", "store_korean": "코스트코", "vendor": "Costco"}
{"amount": "411.89", "grand_total": "411.89"}

RIGHT (DO THIS):
{"store": "Costco", "date": "2024-02-08", "total": "411.89", "subtotal": "380.00", "tax": "31.89"}

Output ONLY valid JSON."""


class ImageProcessor:
    """Processor for extracting content from images using vision model."""
    
    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        """
        Initialize image processor.
        
        Args:
            ollama_client: OllamaClient instance (creates new one if None)
        """
        from backend.config import Config
        self.client = ollama_client or OllamaClient(model=Config.OLLAMA_VISION_MODEL)
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"ImageProcessor initialized with vision model: {self.client.model}")
    
    def process_image(self, image_path: str) -> ImageExtraction:
        """
        Process image and extract structured data.

        Automatically corrects image orientation (rotation, flip) and format before processing.
        Enhanced preprocessing prevents GGML errors by ensuring clean RGB JPEG format.

        The vision model dynamically determines what fields to extract based on document type.
        All extracted fields are stored in flexible_metadata for maximum flexibility.

        Args:
            image_path: Path to image file

        Returns:
            ImageExtraction with extracted data in flexible_metadata

        Raises:
            OllamaError: If processing fails
            FileNotFoundError: If image file doesn't exist
            IOError: If image cannot be read or is corrupted
        """
        import os
        import logging
        logger = logging.getLogger(__name__)

        # Preprocess image: correct orientation and format
        corrected_image_path = self._correct_image_orientation(image_path)

        # Try processing with corrected image
        try:
            # Encode image to base64
            base64_image = encode_image_to_base64(corrected_image_path)

            # Send to vision model with JSON format for structured extraction
            # Use reduced num_predict with strong repeat penalty to prevent loops
            response = self.client.generate(
                prompt=DOCUMENT_EXTRACTION_PROMPT,
                images=[base64_image],
                stream=False,
                format="json",  # Request JSON output for structured data extraction
                options={
                    "num_ctx": 4096,  # Context for document understanding
                    "num_predict": 1024,  # Reduced limit - prevents long responses and repetition
                    "temperature": 0.1,  # Low temperature for consistency
                    "repeat_penalty": 2.0,  # Very strong penalty to prevent repetition loops
                    "stop": ["}}", "}\n}", "} }", '"}"}', '"\n}', '",\n}', '" }', '"\n\n}']  # Extended stop sequences to end JSON properly
                }
            )

            # Extract response text
            raw_text = response.get("response", "")
            
            # Debug logging for qwen3-vl
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Vision model response length: {len(raw_text)} chars")
            if raw_text:
                logger.info(f"Response preview (first 200 chars): {raw_text[:200]}")
            else:
                logger.warning(f"Empty response from vision model for {image_path}")
                logger.warning(f"Full response object: {response}")

            # Parse response into ImageExtraction
            extraction = self._parse_response(raw_text)

            # Clean up temporary file if we created one
            if corrected_image_path != image_path:
                try:
                    os.unlink(corrected_image_path)
                except:
                    pass

            return extraction

        except OllamaError as e:
            # Clean up temp file
            if corrected_image_path != image_path:
                try:
                    os.unlink(corrected_image_path)
                except:
                    pass

            # Check if this is a GGML assertion error
            if "GGML_ASSERT" in str(e):
                logger.error(f"GGML error detected for {image_path} after enhanced preprocessing")
                logger.error(f"This indicates the image may be corrupted or in an unsupported format")
                logger.error(f"Image characteristics: Please manually inspect the file")
                raise IOError(f"Image format incompatible with vision model after preprocessing: {image_path}. "
                            f"The image may be corrupted. Original error: {str(e)}")
            else:
                # Not a GGML error, just re-raise
                raise OllamaError(f"Failed to process image {image_path}: {str(e)}")

    
    def _correct_image_orientation(self, image_path: str) -> str:
        """
        Aggressively correct image orientation and format to prevent GGML errors.
        
        This function:
        1. Opens the image and validates it with enhanced format checks
        2. Applies EXIF orientation correction
        3. Converts to RGB mode (removes alpha channels, CMYK, LAB, etc.)
        4. Strips all metadata (EXIF, ICC profiles) that might cause GGML issues
        5. Resizes to optimal dimensions (max 1536px to reduce processing time)
        6. Saves as clean baseline JPEG with standard format
        
        This prevents GGML assertion errors by ensuring consistent image format.
        
        Args:
            image_path: Path to original image
            
        Returns:
            Path to corrected image (temporary file if corrections were made)
        """
        try:
            from PIL import Image, ImageOps
            import tempfile
            import logging
            logger = logging.getLogger(__name__)
            
            # Open and validate image
            try:
                image = Image.open(image_path)
                image.verify()  # Verify image integrity
                image = Image.open(image_path)  # Reopen after verify
            except Exception as e:
                logger.error(f"Image validation failed for {image_path}: {e}")
                raise IOError(f"Invalid or corrupted image file: {image_path}")
            
            # Enhanced format validation - check for problematic characteristics
            if hasattr(image, 'mode'):
                # Check for alpha channels
                if image.mode in ('RGBA', 'LA', 'PA'):
                    logger.debug(f"Image {image_path} has alpha channel (mode: {image.mode})")
                
                # Check for unusual color modes
                if image.mode in ('CMYK', 'LAB', 'HSV', 'I', 'F'):
                    logger.debug(f"Image {image_path} has unusual color mode: {image.mode}")
            
            # Validate image dimensions are within reasonable bounds
            if hasattr(image, 'size'):
                width, height = image.size
                if width <= 0 or height <= 0:
                    raise IOError(f"Invalid image dimensions: {width}x{height}")
                if width > 10000 or height > 10000:
                    logger.warning(f"Image {image_path} has very large dimensions: {width}x{height}")
            
            # Step 1: Apply EXIF orientation correction
            try:
                corrected_image = ImageOps.exif_transpose(image)
                if corrected_image is None:
                    corrected_image = image
            except Exception:
                corrected_image = image
            
            # Step 2: Aggressive metadata stripping - clear EXIF data after orientation correction
            try:
                exif_data = corrected_image.getexif()
                if exif_data:
                    exif_data.clear()
            except Exception:
                pass  # Some images don't have EXIF data
            
            # Remove ICC color profiles
            if hasattr(corrected_image, 'info') and 'icc_profile' in corrected_image.info:
                corrected_image.info.pop('icc_profile', None)
                logger.debug(f"Removed ICC profile from {image_path}")
            
            # Step 3: Convert to RGB mode (CRITICAL for GGML compatibility)
            # This handles RGBA, CMYK, LAB, and other unusual modes
            if corrected_image.mode != 'RGB':
                logger.debug(f"Converting {image_path} from {corrected_image.mode} to RGB")
                corrected_image = corrected_image.convert('RGB')
            
            # Step 4: Resize to optimal dimensions (smaller = faster processing)
            # Vision models work well with 1024-1536px images
            corrected_image = self._resize_if_needed(corrected_image, max_dimension=1536)
            
            # Step 5: Format normalization - always save as clean baseline JPEG
            # This prevents GGML errors from unusual image formats
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                tmp_path = tmp_file.name
                # Use consistent quality settings, baseline JPEG (not progressive)
                # Strip all metadata with exif=b''
                corrected_image.save(
                    tmp_path, 
                    'JPEG', 
                    quality=92, 
                    optimize=True, 
                    progressive=False,
                    exif=b''  # Ensure no EXIF data in output
                )
                
                logger.debug(f"Preprocessed image saved to {tmp_path}")
                
                return tmp_path
                
        except Exception as e:
            # If preprocessing fails, log warning and use original
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Image preprocessing failed for {image_path}: {e}")
            logger.warning("Using original image (may cause GGML errors)")
            return image_path
    
    def _resize_if_needed(self, image: 'Image.Image', max_dimension: int = 1536) -> 'Image.Image':
        """
        Resize image if it exceeds maximum dimensions.
        
        Smaller images = faster processing without significant quality loss.
        Vision models work well with 1024-1536px images.
        
        Args:
            image: PIL Image object
            max_dimension: Maximum width or height (default: 1536)
            
        Returns:
            Resized image or original if no resize needed
        """
        width, height = image.size
        
        if width > max_dimension or height > max_dimension:
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))
            
            from PIL import Image
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Resizing image from {width}x{height} to {new_width}x{new_height}")
            return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    
    
    def _fix_repetition_loop(self, raw_text: str) -> str:
        """
        Detect and fix repetition loops in vision model output.
        
        The vision model sometimes gets stuck repeating the same fields with
        variations (_korean, _english, etc.). This method detects the repetition
        and truncates the JSON at the first complete iteration.
        
        Enhanced to catch more patterns:
        - Repeating field sequences (original behavior)
        - Duplicate field names (same field appearing multiple times)
        - Excessive length (> 5000 chars indicates likely repetition)
        - Character-level repetition patterns
        
        Args:
            raw_text: Raw JSON text from vision model
            
        Returns:
            Fixed JSON text with repetition removed
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Only process if it looks like JSON
        if not raw_text.strip().startswith('{'):
            return raw_text
        
        # Check for excessive length (likely indicates repetition)
        if len(raw_text) > 5000:
            logger.warning(f"Response exceeds 5000 characters ({len(raw_text)} chars), likely repetition")
            # Try to find a reasonable truncation point
            # Look for the first complete JSON object (ending with })
            first_close = raw_text.find('}')
            if first_close > 100:  # Ensure we have some content
                # Count braces to find balanced closing
                open_count = raw_text[:first_close+1].count('{')
                close_count = raw_text[:first_close+1].count('}')
                if open_count == close_count:
                    truncated = raw_text[:first_close+1]
                    logger.warning(f"Truncated excessive response from {len(raw_text)} to {len(truncated)} chars")
                    return truncated
        
        # Look for repeating patterns of field names
        # Extract all field names from the JSON
        field_pattern = r'"([^"]+)":\s*"[^"]*"'
        matches = list(re.finditer(field_pattern, raw_text))
        
        if len(matches) < 20:
            # Too short to have repetition issues
            return raw_text
        
        # Get field names in order
        field_names = [m.group(1) for m in matches]
        
        # Check for duplicate field names (same field appearing multiple times)
        seen_fields = {}
        for idx, field_name in enumerate(field_names):
            if field_name in seen_fields:
                # Found duplicate field - this is likely the start of repetition
                first_occurrence = seen_fields[field_name]
                # Only truncate if we have at least 5 fields before the duplicate
                if first_occurrence >= 5:
                    truncate_pos = matches[first_occurrence + 1].start() if first_occurrence + 1 < len(matches) else matches[first_occurrence].end()
                    fixed_text = raw_text[:truncate_pos].rstrip(', \n\t') + '}'
                    
                    logger.warning(f"Detected duplicate field '{field_name}' at position {idx}")
                    logger.warning(f"Original length: {len(raw_text)}, Fixed length: {len(fixed_text)}")
                    
                    return fixed_text
            seen_fields[field_name] = idx
        
        # Detect repeating sequences: look for a sequence that repeats
        # Check if the last 10 fields appear earlier in the sequence
        window_size = 10
        if len(field_names) > window_size * 2:
            last_fields = field_names[-window_size:]
            
            # Search for this pattern earlier in the sequence
            for i in range(len(field_names) - window_size * 2):
                window = field_names[i:i+window_size]
                if window == last_fields:
                    # Found repetition! Truncate at this point
                    truncate_pos = matches[i].start()
                    fixed_text = raw_text[:truncate_pos].rstrip(', \n\t') + '}'
                    
                    logger.warning(f"Detected repetition loop at position {truncate_pos}")
                    logger.warning(f"Original length: {len(raw_text)}, Fixed length: {len(fixed_text)}")
                    logger.warning(f"Repeating fields: {last_fields[:3]}...")
                    
                    return fixed_text
        
        # Check for character-level repetition (e.g., same substring repeated)
        # Look for patterns like "abc abc abc"
        if len(raw_text) > 1000:
            # Check if the last 200 chars appear earlier
            tail = raw_text[-200:]
            # Search for this tail in the earlier part of the text
            earlier_occurrence = raw_text[:-200].find(tail)
            if earlier_occurrence > 100:
                # Found character-level repetition
                fixed_text = raw_text[:earlier_occurrence + 200].rstrip(', \n\t')
                if not fixed_text.endswith('}'):
                    fixed_text += '}'
                
                logger.warning(f"Detected character-level repetition at position {earlier_occurrence}")
                logger.warning(f"Original length: {len(raw_text)}, Fixed length: {len(fixed_text)}")
                
                return fixed_text
        
        # No repetition detected, return as-is
        return raw_text
    
    def _parse_response(self, raw_text: str) -> ImageExtraction:
        """
        Parse vision model response into ImageExtraction data class.
        
        Extracts all fields dynamically from the JSON response without forcing
        documents into predefined categories. The model creates its own field names
        based on what it actually sees in the document.
        
        Handles multiple formats:
        - Raw JSON (when format:json is used)
        - JSON between ===JSON_START=== and ===JSON_END=== markers
        - JSON in markdown code blocks
        - <think>...</think> tags (strips thinking content)
        
        Args:
            raw_text: Raw text response from vision model
            
        Returns:
            ImageExtraction with parsed data and flexible metadata
        """
        import json
        import logging
        logger = logging.getLogger(__name__)
        
        # Initialize with empty flexible metadata
        flexible_metadata = {}
        data = None
        
        # Handle qwen3-vl thinking tags - strip everything inside <think>...</think>
        if '<think>' in raw_text and '</think>' in raw_text:
            # Remove all thinking content
            raw_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()
            logger.debug(f"Stripped <think> tags, remaining content: {len(raw_text)} chars")
        
        # CRITICAL: Detect and fix repetition loops before parsing
        # Vision model sometimes gets stuck repeating the same fields
        raw_text = self._fix_repetition_loop(raw_text)
        
        # Try parsing as raw JSON first (most common with format:json)
        try:
            data = json.loads(raw_text.strip(), strict=False)
            logger.debug("Successfully parsed raw JSON")
        except json.JSONDecodeError:
            # Not raw JSON, try other formats
            pass
        
        # Check for JSON markers (===JSON_START=== and ===JSON_END===)
        if data is None and '===JSON_START===' in raw_text and '===JSON_END===' in raw_text:
            # Extract JSON between markers
            json_match = re.search(r'===JSON_START===\s*(\{.*?\})\s*===JSON_END===', raw_text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1), strict=False)
                    logger.debug("Successfully parsed JSON from markers")
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON from markers: {e}")
                    pass
        
        # Try markdown code block format
        if data is None:
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', raw_text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1), strict=False)
                    logger.debug("Successfully parsed JSON from markdown code block")
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON from markdown: {e}")
                    pass
        
        # If we successfully parsed JSON, flatten and filter to keep only useful fields
        if data is not None:
            def flatten_dict(d, parent_key='', sep='_', max_list_items=5):
                """
                Recursively flatten nested dictionaries.
                
                Args:
                    d: Dictionary to flatten
                    parent_key: Parent key for nested items
                    sep: Separator for nested keys
                    max_list_items: Maximum number of list items to include (prevents duplicate spam)
                """
                items = []
                for k, v in d.items():
                    new_key = f"{parent_key}{sep}{k}" if parent_key else k
                    if isinstance(v, dict):
                        # Recursively flatten nested dicts
                        items.extend(flatten_dict(v, new_key, sep=sep, max_list_items=max_list_items).items())
                    elif isinstance(v, list):
                        # For lists, limit to first N items to prevent spam
                        if v and all(isinstance(item, (str, int, float)) for item in v):
                            # Simple list - join first N items
                            limited_items = v[:max_list_items]
                            items.append((new_key, ', '.join(str(item) for item in limited_items)))
                            if len(v) > max_list_items:
                                items.append((new_key + '_total_count', str(len(v))))
                        else:
                            # Complex list (list of dicts) - just store count
                            items.append((new_key + '_count', str(len(v))))
                    elif v not in ['N/A', 'n/a', None, '']:
                        items.append((new_key, str(v)))
                return dict(items)
            
            flattened = flatten_dict(data)
            
            # Filter to keep only the most useful fields
            filtered_metadata = self._filter_useful_fields(flattened)
            
            # Normalize field names to canonical forms (merchant/vendor → store, etc.)
            normalized_metadata = self._normalize_field_names(filtered_metadata)
            
            # Coerce numeric string values to numeric types (total, subtotal, tax, etc.)
            flexible_metadata = self._coerce_numeric_types(normalized_metadata)
            
            # Debug logging
            logger.debug(f"Parsed JSON with {len(flattened)} flattened fields, filtered to {len(filtered_metadata)} useful fields, normalized to {len(flexible_metadata)} fields")
            if flexible_metadata:
                logger.debug(f"Kept fields: {list(flexible_metadata.keys())[:10]}")
        
        # Return ImageExtraction with flexible_metadata
        # The model decides what fields to extract based on document type
        return ImageExtraction(
            raw_text=raw_text,
            flexible_metadata=flexible_metadata
        )
    
    def _filter_useful_fields(self, fields: Dict[str, str]) -> Dict[str, str]:
        """
        Filter metadata fields to keep only the most useful information.
        
        Priority fields (always keep):
        - store, issuer, recipient
        - date, time, transaction_date
        - total, subtotal, tax, amount
        - payment_type, payment_method, card_type
        - document_type, document_number
        - items_count, quantity
        
        Skip fields (always remove):
        - Promotional text, survey codes, social media
        - Barcodes, QR codes (unless it's the only identifier)
        - Duplicate fields with variations (_korean, _full, _english, etc.)
        - Fine print, legal disclaimers, terms
        - Website URLs, phone numbers (unless critical)
        
        Args:
            fields: Flattened metadata dictionary
            
        Returns:
            Filtered metadata dictionary with only useful fields
        """
        # Priority keywords (keep if field name contains these)
        priority_keywords = [
            'store', 'issuer', 'recipient', 'name',
            'date', 'time', 'transaction',
            'total', 'subtotal', 'tax', 'amount', 'price',
            'payment', 'card', 'account',
            'document_type', 'document_number', 'document_id',
            'items_count', 'quantity', 'count',
            'invoice', 'receipt', 'reference', 'auth',
            'location', 'address',
            'birth', 'gender', 'nationality', 'status'
        ]
        
        # Skip keywords (remove if field name contains these)
        skip_keywords = [
            'survey', 'promo', 'facebook', 'social', 'website', 'url',
            'barcode', 'qr_code', 'qr',
            'legal', 'disclaimer', 'terms', 'conditions',
            'fine_print', 'note', 'message',
            '_korean_full', '_english_full', '_abbreviated',
            '_korean_english', '_full_english',
            'digital_coupon', 'optimum', 'reward_program'
        ]
        
        # Duplicate detection - track base field names
        seen_base_fields = {}
        
        filtered = {}
        
        for key, value in fields.items():
            key_lower = key.lower()
            
            # Skip if contains skip keywords
            if any(skip in key_lower for skip in skip_keywords):
                continue
            
            # Check for duplicate variations (e.g., "date", "date_korean", "date_english")
            # Keep only the first/simplest version
            base_key = key_lower.split('_')[0]  # Get base field name
            if base_key in seen_base_fields:
                # This is a duplicate variation, skip it
                continue
            
            # Keep if contains priority keywords
            if any(priority in key_lower for priority in priority_keywords):
                filtered[key] = value
                seen_base_fields[base_key] = key
                continue
            
            # For other fields, only keep if we have less than 20 fields total
            # This prevents bloat while allowing some flexibility
            if len(filtered) < 20:
                filtered[key] = value
                seen_base_fields[base_key] = key
        
        return filtered
    def _normalize_field_names(self, fields: Dict[str, str]) -> Dict[str, str]:
        """
        Normalize field name variants to canonical names.

        Maps common field name variants to standardized canonical names:
        - merchant/vendor/shop → store
        - transaction_date/purchase_date → date
        - amount/grand_total → total

        This ensures consistent field names across all documents, enabling
        reliable metadata filtering and aggregation.

        Args:
            fields: Dictionary of extracted fields with potentially variant names

        Returns:
            Dictionary with normalized field names
        """
        # Define mapping from variants to canonical names
        field_mappings = {
            # Store variants
            'merchant': 'store',
            'vendor': 'store',
            'shop': 'store',
            'retailer': 'store',
            'seller': 'store',

            # Date variants
            'transaction_date': 'date',
            'purchase_date': 'date',
            'receipt_date': 'date',
            'sale_date': 'date',

            # Total variants
            'amount': 'total',
            'grand_total': 'total',
            'total_amount': 'total',
            'final_amount': 'total',
        }

        normalized = {}
        for key, value in fields.items():
            # Convert key to lowercase for case-insensitive matching
            key_lower = key.lower()

            # Check if this field name has a canonical mapping
            if key_lower in field_mappings:
                canonical_name = field_mappings[key_lower]
                # Only map if canonical name doesn't already exist
                # (prefer existing canonical names over variants)
                if canonical_name not in normalized:
                    normalized[canonical_name] = value
            else:
                # Keep original field name if no mapping exists
                normalized[key] = value

        return normalized
    def _coerce_numeric_types(self, fields: Dict[str, str]) -> Dict[str, any]:
        """
        Coerce string values to numeric types for numeric fields.

        Converts string representations of numbers to float or int types
        for fields that should be numeric: total, subtotal, tax, amount,
        price, quantity.

        This enables proper range queries and mathematical operations on
        numeric metadata fields in ChromaDB.

        Args:
            fields: Dictionary of extracted fields with string values

        Returns:
            Dictionary with numeric types for numeric fields
        """
        # Define fields that should be numeric
        numeric_fields = {
            'total', 'subtotal', 'tax', 'amount', 'price', 'quantity',
            'discount', 'tip', 'grand_total', 'balance', 'payment_amount'
        }

        coerced = {}
        for key, value in fields.items():
            # Check if this field should be numeric
            if key.lower() in numeric_fields and isinstance(value, str):
                try:
                    # Remove common currency symbols and whitespace
                    cleaned_value = value.strip().replace('$', '').replace(',', '').replace(' ', '')

                    # Try to convert to float first
                    numeric_value = float(cleaned_value)

                    # If it's a whole number, convert to int
                    if numeric_value.is_integer():
                        coerced[key] = int(numeric_value)
                    else:
                        coerced[key] = numeric_value
                except (ValueError, AttributeError):
                    # If conversion fails, keep as string
                    coerced[key] = value
            else:
                # Keep non-numeric fields as-is
                coerced[key] = value

        return coerced


    
    def _normalize_date(self, date_str: str) -> str:
        """
        Normalize date string to YYYY-MM-DD format.
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            Normalized date string in YYYY-MM-DD format
        """
        if not date_str:
            return date_str
        
        # Try to parse common formats
        # Format: 2026/02/11 or 2026-02-11
        if re.match(r'\d{4}[/-]\d{2}[/-]\d{2}', date_str):
            return date_str.replace('/', '-')
        
        # Format: 2024.02.08
        if re.match(r'\d{4}\.\d{2}\.\d{2}', date_str):
            return date_str.replace('.', '-')
        
        # Format: 02/11/2026 or 02-11-2026
        match = re.match(r'(\d{2})[/-](\d{2})[/-](\d{4})', date_str)
        if match:
            month, day, year = match.groups()
            return f"{year}-{month}-{day}"
        
        # Return as-is if we can't parse it
        return date_str


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
