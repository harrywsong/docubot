# GGML Error Bug Documentation

## Bug Confirmation from Production Logs

Date: 2026-02-21 20:30-20:40

### Evidence of Bug 1: GGML Assertion Errors

**Instance 1: PDF Page Processing**
```
2026-02-21 20:33:35,705 - backend.image_processor - WARNING - GGML error detected for C:\Users\harry\AppData\Local\Temp\tmpy6r8etm6.jpg
2026-02-21 20:33:35,706 - backend.image_processor - WARNING - This image may have format issues. Trying alternative orientations...
2026-02-21 20:33:35,775 - backend.image_processor - INFO - Trying orientation 0° for C:\Users\harry\AppData\Local\Temp\tmpy6r8etm6.jpg
2026-02-21 20:34:20,125 - backend.image_processor - INFO - Successfully processed with 0° rotation
```
**Processing time: 44 seconds** (from 20:33:35 to 20:34:20)

**Instance 2: KakaoTalk Image**
```
2026-02-21 20:37:20,656 - backend.image_processor - WARNING - GGML error detected for C:\Users\harry\OneDrive\Desktop\testing\KakaoTalk_20260219_155002406_01.jpg
2026-02-21 20:37:20,656 - backend.image_processor - WARNING - This image may have format issues. Trying alternative orientations...
2026-02-21 20:37:20,739 - backend.image_processor - INFO - Trying orientation 0° for C:\Users\harry\OneDrive\Desktop\testing\KakaoTalk_20260219_155002406_01.jpg
2026-02-21 20:38:56,779 - backend.image_processor - INFO - Trying orientation 90° for C:\Users\harry\OneDrive\Desktop\testing\KakaoTalk_20260219_155002406_01.jpg
2026-02-21 20:39:34,442 - backend.image_processor - INFO - Successfully processed with 90° rotation
```
**Processing time: 134 seconds** (from 20:37:20 to 20:39:34)
- Orientation 0°: ~96 seconds (failed)
- Orientation 90°: ~38 seconds (succeeded)

### Evidence of Bug 2: Slow Orientation Retry

The orientation retry logic causes severe performance issues:
- **Instance 1**: 44 seconds for a single image (orientation 0° succeeded)
- **Instance 2**: 134 seconds for a single image (orientation 0° failed, 90° succeeded)
- **Expected performance**: < 15 seconds per image

### Image Characteristics

Images that triggered GGML errors:
- **Format**: JPEG (RGB mode)
- **Source**: KakaoTalk messenger, PDF pages
- **Properties**:
  - KakaoTalk_20260219_155002406_01.jpg: 1170x1634, RGB, EXIF data
  - Temporary preprocessed files (tmpy6r8etm6.jpg): Already preprocessed by `_correct_image_orientation`

### Root Cause Analysis

1. **GGML errors occur AFTER preprocessing**: The temporary file `tmpy6r8etm6.jpg` shows that GGML errors happen even after the image has been preprocessed (converted to RGB, resized, saved as JPEG).

2. **Current preprocessing is insufficient**: The `_correct_image_orientation` method converts to RGB and saves as JPEG, but this doesn't prevent GGML errors.

3. **Possible causes**:
   - Metadata (EXIF, ICC profiles) surviving preprocessing and causing GGML issues
   - Image dimensions or aspect ratios that GGML doesn't handle well
   - Specific JPEG encoding characteristics (progressive vs baseline, subsampling)
   - Ollama service state or memory issues

4. **Orientation retry is ineffective**: The retry logic tries different rotations, but:
   - Rotation doesn't fix format issues
   - Each attempt takes 15+ seconds (timeout)
   - Total time: 60-134 seconds per image
   - Eventually succeeds, suggesting the issue is transient or timing-related

### Test Behavior

**Test 1.1 - Real Images**: When running `test_real_image_triggers_ggml_error` in isolation:
- Images process successfully without GGML errors
- Processing time: 4-6 seconds
- No orientation retry triggered

**Test 1.2 - CMYK Images**: When running `test_cmyk_image_triggers_ggml_error`:
- CMYK images process successfully without GGML errors
- Processing time: 5-6 seconds
- Current preprocessing already converts CMYK to RGB (line 210 in image_processor.py)
- Test confirms CMYK conversion works correctly
- **Key Finding**: GGML errors in production occur even on preprocessed RGB JPEG images, suggesting the issue is related to metadata, JPEG encoding characteristics, or Ollama service state rather than just color mode conversion

**Production Behavior**: When processing multiple documents in sequence:
- GGML errors occur intermittently
- Orientation retry is triggered
- Processing time: 44-134 seconds per affected image

**Conclusion**: GGML errors appear to be:
- Intermittent or dependent on Ollama service state
- More likely to occur during batch processing
- Possibly related to memory pressure or service load
- Not consistently reproducible in isolated tests
- Not caused by CMYK color mode (already handled by preprocessing)
- Likely caused by metadata (EXIF, ICC profiles) or JPEG encoding characteristics

### Bug Confirmation

✓ **Bug 1 (GGML Errors) CONFIRMED**: Production logs show GGML assertion errors occurring during image processing

✓ **Bug 2 (Slow Orientation Retry) CONFIRMED**: Production logs show orientation retry taking 44-134 seconds per image

✓ **Bug 3 (Receipt Logic) PENDING**: Requires separate testing of field extraction and query filtering

### Recommended Fix Strategy

Based on the evidence:

1. **Enhanced Metadata Stripping**: Strip ALL metadata (EXIF, ICC profiles, XMP) after preprocessing
2. **Format Normalization**: Ensure consistent JPEG encoding (baseline, standard subsampling)
3. **Dimension Validation**: Validate and normalize image dimensions to GGML-friendly sizes
4. **Remove Orientation Retry**: Since rotation doesn't fix format issues, remove this ineffective fallback
5. **Fast Failure**: If GGML error occurs after enhanced preprocessing, fail fast with clear error message

### Test Strategy

Since GGML errors are intermittent:

1. **Document the bug**: ✓ Done (this file + test file)
2. **Write test encoding expected behavior**: ✓ Done (test_real_image_triggers_ggml_error)
3. **Implement fix**: Apply enhanced preprocessing and remove orientation retry
4. **Verify fix**: Run tests and monitor production logs for GGML errors
5. **Performance verification**: Ensure all images process in < 15 seconds
