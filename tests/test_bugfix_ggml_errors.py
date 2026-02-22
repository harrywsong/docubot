"""
Bug Condition Exploration Tests for GGML Errors

These tests are EXPECTED TO FAIL on unfixed code.
Failures confirm the bugs exist and document the specific error conditions.

DO NOT attempt to fix the tests or the code when they fail.
These tests encode the expected behavior and will validate the fix when they pass.

NOTE: GGML errors appear to be intermittent or dependent on the Ollama service state.
The logs show GGML errors occurring during actual document processing, triggering
the slow orientation retry logic (60-134 seconds per image).
"""

import pytest
from PIL import Image
import tempfile
import os
from pathlib import Path

from backend.image_processor import ImageProcessor
from backend.ollama_client import OllamaClient


class TestGGMLErrorBugConditions:
    """
    Bug Condition Exploration Tests for Bug 1: GGML Assertion Errors
    
    **Validates: Requirements 2.4**
    
    These tests demonstrate that the vision model throws GGML assertion errors
    when processing certain images, triggering the slow orientation retry fallback.
    
    Based on actual logs showing:
    - GGML errors on KakaoTalk images during document processing
    - Orientation retry taking 44-134 seconds per image
    - Errors occurring on preprocessed temporary files (tmpy6r8etm6.jpg)
    
    EXPECTED OUTCOME ON UNFIXED CODE: Tests FAIL with GGML assertion errors or timeouts
    EXPECTED OUTCOME ON FIXED CODE: Tests PASS without GGML errors, complete in < 15s
    """
    
    def test_real_image_triggers_ggml_error(self):
        """
        Test 1.1: GGML Error Test - Real Images from Testing Directory
        
        **Validates: Requirements 2.4**
        
        Process actual images that caused GGML errors in production logs.
        
        From logs (2026-02-21):
        - KakaoTalk_20260219_155002406_01.jpg: GGML error, 134s to process with retry
        - Temporary preprocessed files also triggered GGML errors
        
        EXPECTED OUTCOME ON UNFIXED CODE:
        - GGML assertion error may occur (intermittent)
        - If GGML error occurs, orientation retry is triggered
        - Processing takes 60+ seconds due to orientation retry
        
        EXPECTED OUTCOME ON FIXED CODE:
        - Image is converted to clean format during preprocessing
        - Processing completes successfully without GGML errors
        - Processing completes in under 15 seconds
        - Returns valid ImageExtraction result
        """
        # Use actual images from testing directory that caused GGML errors
        test_images = [
            "testing/KakaoTalk_20260219_155002406_01.jpg",  # Caused 134s retry in logs
            "testing/KakaoTalk_20260219_155002406.jpg",
            "testing/KakaoTalk_20260219_155002406_02.jpg",
            "testing/KakaoTalk_20260219_155140673.jpg",
            "testing/KakaoTalk_20260219_155151473.jpg",
        ]
        
        # Test with the first available image
        test_image_path = None
        for img_path in test_images:
            if os.path.exists(img_path):
                test_image_path = img_path
                break
        
        if test_image_path is None:
            pytest.skip("No test images found in testing directory")
        
        print(f"\nTesting with: {test_image_path}")
        print(f"NOTE: GGML errors may be intermittent - depends on Ollama service state")
        
        import time
        start_time = time.time()
        
        try:
            # Initialize processor with real Ollama client
            # This will use the actual vision model which may throw GGML errors
            processor = ImageProcessor()
            
            # Process the image
            # ON UNFIXED CODE: May trigger GGML error and slow orientation retry
            # ON FIXED CODE: Should complete successfully in < 15 seconds
            result = processor.process_image(test_image_path)
            
            elapsed_time = time.time() - start_time
            
            # If we reach here, processing succeeded
            assert result is not None
            assert hasattr(result, 'raw_text')
            assert hasattr(result, 'flexible_metadata')
            
            print(f"\n✓ Test PASSED: Image processed successfully without GGML errors")
            print(f"  Processing time: {elapsed_time:.2f} seconds")
            print(f"  Extracted data: {result.flexible_metadata}")
            
            # On FIXED code, verify processing is fast
            if elapsed_time > 15.0:
                print(f"  ⚠ WARNING: Processing took {elapsed_time:.2f}s (expected < 15s)")
                print(f"  This suggests orientation retry may have been triggered")
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            
            # ON UNFIXED CODE: Document the GGML error
            error_msg = str(e)
            error_type = type(e).__name__
            
            print(f"\n✗ Test FAILED (Expected on unfixed code): Error occurred")
            print(f"  Error Type: {error_type}")
            print(f"  Error Message: {error_msg[:500]}")  # Truncate long messages
            print(f"  Processing time before failure: {elapsed_time:.2f} seconds")
            
            # Check if this is a GGML-related error
            is_ggml_error = (
                'GGML' in error_msg.upper() or
                'assertion' in error_msg.lower() or
                'ggml' in error_type.lower() or
                'timeout' in error_msg.lower() or  # May timeout during orientation retry
                'orientation' in error_msg.lower()  # May mention orientation retry
            )
            
            if is_ggml_error:
                print(f"  ✓ Confirmed: This is a GGML-related error (Bug 1 confirmed)")
            
            if elapsed_time > 60:
                print(f"  ✓ Confirmed: Slow processing detected (Bug 2 confirmed)")
            
            # Re-raise to mark test as failed on unfixed code
            raise
    
    def test_real_image_processing_time(self):
        """
        Test 1.1 (Performance): Measure processing time for real images
        
        **Validates: Requirements 2.4, 2.5**
        
        This test measures how long it takes to process real images that caused GGML errors.
        
        EXPECTED OUTCOME ON UNFIXED CODE:
        - If GGML error triggers orientation retry: 60+ seconds
        - If GGML error fails fast: < 5 seconds (but still fails)
        
        EXPECTED OUTCOME ON FIXED CODE:
        - Processing completes in under 15 seconds
        - No GGML errors occur
        """
        import time
        
        # Use actual images from testing directory
        test_images = [
            "testing/KakaoTalk_20260219_155002406.jpg",
            "testing/KakaoTalk_20260219_155002406_01.jpg",
        ]
        
        test_image_path = None
        for img_path in test_images:
            if os.path.exists(img_path):
                test_image_path = img_path
                break
        
        if test_image_path is None:
            pytest.skip("No test images found in testing directory")
        
        print(f"\nTesting processing time with: {test_image_path}")
        
        processor = ImageProcessor()
        
        # Measure processing time
        start_time = time.time()
        
        try:
            result = processor.process_image(test_image_path)
            elapsed_time = time.time() - start_time
            
            print(f"\n✓ Processing completed in {elapsed_time:.2f} seconds")
            
            # On FIXED code, verify processing is fast
            assert elapsed_time < 15.0, f"Processing took {elapsed_time:.2f}s, expected < 15s"
            print(f"  ✓ Performance requirement met (< 15 seconds)")
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            
            print(f"\n✗ Processing failed after {elapsed_time:.2f} seconds")
            print(f"  Error: {str(e)[:200]}")
            
            if elapsed_time > 60:
                print(f"  ✓ Confirmed: Slow orientation retry detected (Bug 2 confirmed)")
            elif elapsed_time < 5:
                print(f"  ✓ Confirmed: Fast failure with GGML error (Bug 1 confirmed)")
            
            raise


    def test_cmyk_image_triggers_ggml_error(self):
        """
        Test 1.2: GGML Error Test - CMYK Image
        
        **Validates: Requirements 2.4**
        
        Process CMYK JPEG image to verify CMYK-to-RGB conversion works correctly.
        
        CMYK (Cyan, Magenta, Yellow, Key/Black) is a color mode used in printing.
        Many vision models expect RGB images and may fail on CMYK images.
        
        EXPECTED OUTCOME ON UNFIXED CODE:
        - Current preprocessing already converts CMYK to RGB (line 210 in image_processor.py)
        - Test may PASS if CMYK conversion is working
        - Test may FAIL if GGML error occurs (intermittent, depends on Ollama service state)
        
        EXPECTED OUTCOME ON FIXED CODE:
        - Image is converted to RGB during preprocessing with enhanced metadata stripping
        - Processing completes successfully without GGML errors
        - Processing completes in under 15 seconds
        - Returns valid ImageExtraction result
        
        NOTE: GGML errors in production occur even on preprocessed RGB JPEG images,
        suggesting the issue is related to metadata, encoding, or Ollama service state
        rather than just color mode conversion.
        """
        # Create a CMYK test image
        # CMYK mode is commonly used in print documents and may cause GGML errors
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            cmyk_image_path = tmp.name
        
        try:
            # Create a simple CMYK image with some content
            # CMYK: Cyan=100%, Magenta=50%, Yellow=0%, Black=0% creates a blue-ish color
            cmyk_img = Image.new('CMYK', (800, 600), color=(255, 128, 0, 0))
            
            # Add some variation to make it more realistic
            from PIL import ImageDraw
            draw = ImageDraw.Draw(cmyk_img)
            draw.rectangle([100, 100, 700, 500], fill=(0, 255, 255, 0))  # Yellow rectangle
            draw.text((200, 250), "CMYK Test Image", fill=(0, 0, 0, 255))  # Black text
            
            # Save as JPEG in CMYK mode
            cmyk_img.save(cmyk_image_path, 'JPEG', quality=95)
            
            # Verify the saved image is actually CMYK
            verify_img = Image.open(cmyk_image_path)
            actual_mode = verify_img.mode
            verify_img.close()
            
            print(f"\nCreated CMYK test image: {cmyk_image_path}")
            print(f"Image mode: {actual_mode}, Size: 800x600")
            print(f"NOTE: GGML errors may be intermittent - depends on Ollama service state")
            
            import time
            start_time = time.time()
            
            try:
                # Initialize processor with real Ollama client
                # This will use the actual vision model which may throw GGML errors on CMYK
                processor = ImageProcessor()
                
                # Process the CMYK image
                # ON UNFIXED CODE: Current preprocessing converts CMYK to RGB (may still pass)
                # ON FIXED CODE: Enhanced preprocessing with metadata stripping (should pass reliably)
                result = processor.process_image(cmyk_image_path)
                
                elapsed_time = time.time() - start_time
                
                # If we reach here, processing succeeded
                assert result is not None
                assert hasattr(result, 'raw_text')
                assert hasattr(result, 'flexible_metadata')
                
                print(f"\n✓ Test PASSED: CMYK image processed successfully without GGML errors")
                print(f"  Processing time: {elapsed_time:.2f} seconds")
                print(f"  Extracted data: {result.flexible_metadata}")
                print(f"  NOTE: Current preprocessing already converts CMYK to RGB")
                print(f"  This test confirms CMYK conversion works, but GGML errors in production")
                print(f"  occur even on preprocessed RGB images, suggesting metadata/encoding issues")
                
                # On FIXED code, verify processing is fast
                if elapsed_time > 15.0:
                    print(f"  ⚠ WARNING: Processing took {elapsed_time:.2f}s (expected < 15s)")
                    print(f"  This suggests orientation retry may have been triggered")
                
            except Exception as e:
                elapsed_time = time.time() - start_time
                
                # ON UNFIXED CODE: Document the GGML error
                error_msg = str(e)
                error_type = type(e).__name__
                
                print(f"\n✗ Test FAILED (Expected on unfixed code if GGML error occurs): Error occurred")
                print(f"  Error Type: {error_type}")
                print(f"  Error Message: {error_msg[:500]}")  # Truncate long messages
                print(f"  Processing time before failure: {elapsed_time:.2f} seconds")
                
                # Check if this is a GGML-related error
                is_ggml_error = (
                    'GGML' in error_msg.upper() or
                    'assertion' in error_msg.lower() or
                    'ggml' in error_type.lower() or
                    'timeout' in error_msg.lower() or  # May timeout during orientation retry
                    'orientation' in error_msg.lower() or  # May mention orientation retry
                    'cmyk' in error_msg.lower() or  # May mention CMYK mode issue
                    'color mode' in error_msg.lower()  # May mention color mode issue
                )
                
                if is_ggml_error:
                    print(f"  ✓ Confirmed: This is a GGML/format-related error (Bug 1 confirmed)")
                
                if elapsed_time > 60:
                    print(f"  ✓ Confirmed: Slow processing detected (Bug 2 confirmed)")
                
                # Re-raise to mark test as failed on unfixed code
                raise
        
        finally:
            # Clean up temporary file
            if os.path.exists(cmyk_image_path):
                os.unlink(cmyk_image_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
