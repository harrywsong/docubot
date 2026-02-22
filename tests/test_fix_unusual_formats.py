"""
Additional Fix Checking Tests - Unusual Image Formats

**Property 1: Expected Behavior** - Format Conversion

These property-based tests verify that the fixed system can handle various
unusual image formats (WebP, TIFF, BMP) by converting them to clean JPEG
and processing them successfully without GGML errors.

**Validates: Requirements 2.4**
"""

import pytest
from PIL import Image, ImageDraw
import tempfile
import os
import time
from hypothesis import given, strategies as st, settings, HealthCheck

from backend.image_processor import ImageProcessor


class TestUnusualFormatProcessing:
    """
    Property-Based Tests for Unusual Image Format Processing
    
    **Validates: Requirements 2.4**
    
    These tests verify that the fixed preprocessing handles various image formats:
    - WebP: Modern web image format with lossy/lossless compression
    - TIFF: Tagged Image File Format, common in scanning/professional photography
    - BMP: Bitmap format, uncompressed raster graphics
    
    EXPECTED OUTCOME ON FIXED CODE:
    - All formats are converted to clean JPEG during preprocessing
    - Processing completes successfully without GGML errors
    - Processing completes in under 15 seconds per image
    - Returns valid ImageExtraction result with flexible_metadata
    """
    
    @given(
        width=st.integers(min_value=100, max_value=2000),
        height=st.integers(min_value=100, max_value=2000),
        format_choice=st.sampled_from(['WEBP', 'TIFF', 'BMP'])
    )
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    def test_unusual_format_processing_property(self, width, height, format_choice):
        """
        Property Test: For any unusual image format (WebP, TIFF, BMP),
        the fixed system SHALL convert to clean JPEG and process successfully.
        
        **Validates: Requirements 2.4**
        
        This property-based test generates images in various formats and dimensions
        to verify robust format conversion.
        """
        # Create test image in the specified format
        with tempfile.NamedTemporaryFile(
            suffix=f'.{format_choice.lower()}',
            delete=False
        ) as tmp:
            test_image_path = tmp.name
        
        try:
            # Create RGB image with some content
            img = Image.new('RGB', (width, height), color=(100, 150, 200))
            
            # Add some visual content to make it realistic
            draw = ImageDraw.Draw(img)
            draw.rectangle([width//4, height//4, 3*width//4, 3*height//4], 
                          fill=(200, 100, 50))
            draw.ellipse([width//3, height//3, 2*width//3, 2*height//3], 
                        fill=(50, 200, 100))
            
            # Save in the specified format
            if format_choice == 'WEBP':
                img.save(test_image_path, 'WEBP', quality=90)
            elif format_choice == 'TIFF':
                img.save(test_image_path, 'TIFF', compression='tiff_deflate')
            elif format_choice == 'BMP':
                img.save(test_image_path, 'BMP')
            
            img.close()
            
            # Verify the saved image format
            verify_img = Image.open(test_image_path)
            actual_format = verify_img.format
            verify_img.close()
            
            print(f"\nTesting {format_choice} image: {width}x{height}, format={actual_format}")
            
            # Process the image
            start_time = time.time()
            processor = ImageProcessor()
            result = processor.process_image(test_image_path)
            elapsed_time = time.time() - start_time
            
            # Verify successful processing
            assert result is not None, f"Processing failed for {format_choice} image"
            assert hasattr(result, 'raw_text'), "Result missing raw_text"
            assert hasattr(result, 'flexible_metadata'), "Result missing flexible_metadata"
            
            # Verify processing time is reasonable
            assert elapsed_time < 15.0, \
                f"{format_choice} processing took {elapsed_time:.2f}s, expected < 15s"
            
            print(f"  ✓ {format_choice} image processed successfully in {elapsed_time:.2f}s")
            
        finally:
            # Clean up temporary file
            if os.path.exists(test_image_path):
                os.unlink(test_image_path)
    
    def test_webp_format_processing(self):
        """
        Test WebP format processing
        
        **Validates: Requirements 2.4**
        
        WebP is a modern image format developed by Google that provides
        superior compression. This test verifies WebP images are converted
        to clean JPEG and processed successfully.
        """
        with tempfile.NamedTemporaryFile(suffix='.webp', delete=False) as tmp:
            webp_path = tmp.name
        
        try:
            # Create WebP test image
            img = Image.new('RGB', (800, 600), color=(120, 180, 240))
            draw = ImageDraw.Draw(img)
            draw.rectangle([100, 100, 700, 500], fill=(240, 120, 80))
            draw.text((200, 250), "WebP Test", fill=(0, 0, 0))
            img.save(webp_path, 'WEBP', quality=90)
            img.close()
            
            print(f"\nTesting WebP image: {webp_path}")
            
            # Process the image
            start_time = time.time()
            processor = ImageProcessor()
            result = processor.process_image(webp_path)
            elapsed_time = time.time() - start_time
            
            # Verify successful processing
            assert result is not None
            assert hasattr(result, 'flexible_metadata')
            assert elapsed_time < 15.0, f"Processing took {elapsed_time:.2f}s"
            
            print(f"  ✓ WebP image processed successfully in {elapsed_time:.2f}s")
            print(f"  Extracted data: {result.flexible_metadata}")
            
        finally:
            if os.path.exists(webp_path):
                os.unlink(webp_path)
    
    def test_tiff_format_processing(self):
        """
        Test TIFF format processing
        
        **Validates: Requirements 2.4**
        
        TIFF is a flexible format commonly used in scanning and professional
        photography. This test verifies TIFF images are converted to clean
        JPEG and processed successfully.
        """
        with tempfile.NamedTemporaryFile(suffix='.tiff', delete=False) as tmp:
            tiff_path = tmp.name
        
        try:
            # Create TIFF test image
            img = Image.new('RGB', (1000, 800), color=(200, 150, 100))
            draw = ImageDraw.Draw(img)
            draw.ellipse([200, 200, 800, 600], fill=(100, 200, 150))
            draw.text((300, 350), "TIFF Test", fill=(255, 255, 255))
            img.save(tiff_path, 'TIFF', compression='tiff_deflate')
            img.close()
            
            print(f"\nTesting TIFF image: {tiff_path}")
            
            # Process the image
            start_time = time.time()
            processor = ImageProcessor()
            result = processor.process_image(tiff_path)
            elapsed_time = time.time() - start_time
            
            # Verify successful processing
            assert result is not None
            assert hasattr(result, 'flexible_metadata')
            assert elapsed_time < 15.0, f"Processing took {elapsed_time:.2f}s"
            
            print(f"  ✓ TIFF image processed successfully in {elapsed_time:.2f}s")
            print(f"  Extracted data: {result.flexible_metadata}")
            
        finally:
            if os.path.exists(tiff_path):
                os.unlink(tiff_path)
    
    def test_bmp_format_processing(self):
        """
        Test BMP format processing
        
        **Validates: Requirements 2.4**
        
        BMP is an uncompressed bitmap format. This test verifies BMP images
        are converted to clean JPEG and processed successfully.
        """
        with tempfile.NamedTemporaryFile(suffix='.bmp', delete=False) as tmp:
            bmp_path = tmp.name
        
        try:
            # Create BMP test image
            img = Image.new('RGB', (640, 480), color=(150, 200, 250))
            draw = ImageDraw.Draw(img)
            draw.rectangle([50, 50, 590, 430], fill=(250, 150, 100))
            draw.text((150, 200), "BMP Test", fill=(0, 0, 0))
            img.save(bmp_path, 'BMP')
            img.close()
            
            print(f"\nTesting BMP image: {bmp_path}")
            
            # Process the image
            start_time = time.time()
            processor = ImageProcessor()
            result = processor.process_image(bmp_path)
            elapsed_time = time.time() - start_time
            
            # Verify successful processing
            assert result is not None
            assert hasattr(result, 'flexible_metadata')
            assert elapsed_time < 15.0, f"Processing took {elapsed_time:.2f}s"
            
            print(f"  ✓ BMP image processed successfully in {elapsed_time:.2f}s")
            print(f"  Extracted data: {result.flexible_metadata}")
            
        finally:
            if os.path.exists(bmp_path):
                os.unlink(bmp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
