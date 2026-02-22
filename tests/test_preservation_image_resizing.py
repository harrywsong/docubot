"""
Preservation Property Test for Image Resizing

This test MUST PASS on unfixed code to establish baseline behavior.
After the fix, image resizing logic should continue to work identically.

This test uses property-based testing to generate many test cases for stronger guarantees.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from PIL import Image
import tempfile
import os

from backend.image_processor import ImageProcessor


class TestImageResizingPreservation:
    """
    Preservation Property Test for Image Resizing
    
    **Validates: Requirements 3.3**
    
    This test establishes baseline behavior for image resizing that must be preserved.
    
    From bugfix.md:
    - Preservation requirement (3.3): Image resizing with max_dimension=1536 must continue
      to apply the same resizing logic
    
    EXPECTED OUTCOME ON UNFIXED CODE: Test PASSES - resizing logic works correctly
    EXPECTED OUTCOME ON FIXED CODE: Test PASSES - same resizing logic applied
    """
    
    @settings(
        max_examples=15,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        width=st.integers(min_value=1600, max_value=4000),
        height=st.integers(min_value=1600, max_value=4000)
    )
    def test_large_image_resizing_preservation(self, width, height):
        """
        Test 2.3: Image Resizing Preservation Test
        
        **Validates: Requirements 3.3**
        
        This test establishes baseline behavior for image resizing.
        Process large images (>1536px) and verify the same resizing logic
        is applied after the fix.
        
        EXPECTED OUTCOME ON UNFIXED CODE:
        - Large images are resized to max_dimension=1536
        - Aspect ratio is preserved
        - Larger dimension is scaled to 1536, smaller dimension scaled proportionally
        - Test PASSES to establish baseline
        
        EXPECTED OUTCOME ON FIXED CODE:
        - Same resizing logic is applied
        - Test PASSES to confirm preservation
        """
        print(f"\n{'='*70}")
        print(f"PRESERVATION TEST: Image Resizing - Size {width}x{height}")
        print(f"{'='*70}")
        
        # Create a large test image
        image = Image.new('RGB', (width, height), color='blue')
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            image.save(tmp_path, 'JPEG')
        
        try:
            # Process the image through the image processor
            processor = ImageProcessor()
            
            # Call the internal method to get the corrected (resized) image path
            corrected_path = processor._correct_image_orientation(tmp_path)
            
            # Verify the corrected image exists
            assert os.path.exists(corrected_path), "Corrected image should exist"
            
            # Load the corrected image
            corrected_image = Image.open(corrected_path)
            
            # Verify the image was resized
            corrected_width, corrected_height = corrected_image.size
            
            print(f"  Original size: {width}x{height}")
            print(f"  Resized size: {corrected_width}x{corrected_height}")
            
            # Verify max dimension is 1536 or less
            max_dimension = max(corrected_width, corrected_height)
            assert max_dimension <= 1536, f"Max dimension should be <= 1536, got {max_dimension}"
            
            # Verify aspect ratio is preserved (within 1% tolerance for rounding)
            original_aspect = width / height
            corrected_aspect = corrected_width / corrected_height
            aspect_diff = abs(original_aspect - corrected_aspect) / original_aspect
            
            assert aspect_diff < 0.01, f"Aspect ratio should be preserved, diff: {aspect_diff:.4f}"
            
            # Verify the larger dimension was scaled to 1536
            if width > height:
                # Width should be scaled to 1536
                expected_width = 1536
                expected_height = int(height * (1536 / width))
                print(f"  Expected size: {expected_width}x{expected_height}")
                
                # Allow small rounding differences
                assert abs(corrected_width - expected_width) <= 1, \
                    f"Width should be ~{expected_width}, got {corrected_width}"
                assert abs(corrected_height - expected_height) <= 1, \
                    f"Height should be ~{expected_height}, got {corrected_height}"
            else:
                # Height should be scaled to 1536
                expected_height = 1536
                expected_width = int(width * (1536 / height))
                print(f"  Expected size: {expected_width}x{expected_height}")
                
                # Allow small rounding differences
                assert abs(corrected_height - expected_height) <= 1, \
                    f"Height should be ~{expected_height}, got {corrected_height}"
                assert abs(corrected_width - expected_width) <= 1, \
                    f"Width should be ~{expected_width}, got {corrected_width}"
            
            print(f"  ✓ Image resized correctly with preserved aspect ratio")
            
            # Clean up corrected image if it's a temp file
            if corrected_path != tmp_path:
                try:
                    os.unlink(corrected_path)
                except:
                    pass
            
        finally:
            # Clean up original temp file
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        width=st.integers(min_value=100, max_value=1536),
        height=st.integers(min_value=100, max_value=1536)
    )
    def test_small_image_no_resizing_preservation(self, width, height):
        """
        Test that images <= 1536px are not resized.
        
        **Validates: Requirements 3.3**
        
        EXPECTED OUTCOME ON UNFIXED CODE:
        - Small images (<=1536px) are not resized
        - Original dimensions are preserved
        - Test PASSES to establish baseline
        
        EXPECTED OUTCOME ON FIXED CODE:
        - Same behavior (no resizing for small images)
        - Test PASSES to confirm preservation
        """
        print(f"\n{'='*70}")
        print(f"PRESERVATION TEST: Small Image (No Resize) - Size {width}x{height}")
        print(f"{'='*70}")
        
        # Create a small test image
        image = Image.new('RGB', (width, height), color='green')
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            image.save(tmp_path, 'JPEG')
        
        try:
            # Process the image through the image processor
            processor = ImageProcessor()
            
            # Call the internal method to get the corrected image path
            corrected_path = processor._correct_image_orientation(tmp_path)
            
            # Verify the corrected image exists
            assert os.path.exists(corrected_path), "Corrected image should exist"
            
            # Load the corrected image
            corrected_image = Image.open(corrected_path)
            
            # Verify the image dimensions are unchanged (or very close due to JPEG compression)
            corrected_width, corrected_height = corrected_image.size
            
            print(f"  Original size: {width}x{height}")
            print(f"  Processed size: {corrected_width}x{corrected_height}")
            
            # Dimensions should be the same (allowing for small JPEG compression differences)
            assert abs(corrected_width - width) <= 2, \
                f"Width should be ~{width}, got {corrected_width}"
            assert abs(corrected_height - height) <= 2, \
                f"Height should be ~{height}, got {corrected_height}"
            
            print(f"  ✓ Small image not resized (dimensions preserved)")
            
            # Clean up corrected image if it's a temp file
            if corrected_path != tmp_path:
                try:
                    os.unlink(corrected_path)
                except:
                    pass
            
        finally:
            # Clean up original temp file
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    def test_image_resizing_baseline_summary(self):
        """
        Summary test to document baseline image resizing behavior.
        
        This test documents the expected behavior that must be preserved.
        """
        print(f"\n{'='*70}")
        print(f"BASELINE SUMMARY: Image Resizing Preservation")
        print(f"{'='*70}")
        
        print("\nBaseline behavior established:")
        print("  - Images with max dimension > 1536px are resized")
        print("  - Max dimension is scaled to 1536px")
        print("  - Aspect ratio is preserved during resizing")
        print("  - Smaller dimension is scaled proportionally")
        print("  - Images with max dimension <= 1536px are not resized")
        print("  - Resizing uses LANCZOS resampling for quality")
        
        print("\nAfter fix:")
        print("  - Same resizing logic must be applied")
        print("  - Same max_dimension=1536 threshold must be used")
        print("  - Same aspect ratio preservation must occur")
        print("  - Same resampling method must be used")
        
        print(f"\n✓ PRESERVATION TEST BASELINE ESTABLISHED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
