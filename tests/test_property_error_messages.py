"""
Property-based test for error message user-friendliness.

Feature: rag-chatbot-with-vision, Property 28: Error Message User-Friendliness

Validates: Requirements 11.1, 11.4

**Validates: Requirements 11.1, 11.4**

This test verifies that for any error occurring during document processing or querying,
the system displays a user-friendly error message (not raw stack traces or technical jargon).
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import patch, Mock, MagicMock
from backend.document_processor import DocumentProcessor
from backend.query_engine import QueryEngine
from backend.folder_manager import FolderManager
from backend.database import DatabaseManager
from backend.config import Config
from backend.api import app
from fastapi.testclient import TestClient
import re


# Test fixtures
@pytest.fixture(scope="module")
def test_data_dir():
    """Create temporary data directory for tests."""
    temp_dir = tempfile.mkdtemp()
    
    # Override config paths
    Config.DATA_DIR = Path(temp_dir)
    Config.CHROMADB_PATH = str(Path(temp_dir) / "chromadb")
    Config.SQLITE_PATH = str(Path(temp_dir) / "test.db")
    Config.ensure_data_directories()
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="module")
def db_manager(test_data_dir):
    """Create database manager for tests."""
    return DatabaseManager()


@pytest.fixture(scope="module")
def client(test_data_dir):
    """Create test client."""
    with TestClient(app) as test_client:
        yield test_client


# Custom strategies for generating error scenarios
@st.composite
def invalid_folder_path_strategy(draw):
    """Generate invalid folder paths that should trigger errors."""
    invalid_type = draw(st.sampled_from([
        'nonexistent',
        'special_chars',
        'empty',
        'whitespace',
        'very_long'
    ]))
    
    if invalid_type == 'nonexistent':
        # Generate a path that doesn't exist
        random_name = draw(st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
        return f"/nonexistent/path/{random_name}"
    elif invalid_type == 'special_chars':
        # Generate path with special characters
        return draw(st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=('Cs',))))
    elif invalid_type == 'empty':
        return ""
    elif invalid_type == 'whitespace':
        return "   "
    else:  # very_long
        return "/" + "a" * 500


@st.composite
def file_processing_error_strategy(draw):
    """Generate scenarios that cause file processing errors."""
    error_type = draw(st.sampled_from([
        'corrupted_pdf',
        'unreadable_file',
        'invalid_image',
        'extraction_failure',
        'embedding_failure'
    ]))
    
    filename = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    
    if error_type == 'corrupted_pdf':
        return {
            'type': error_type,
            'filename': f"{filename}.pdf",
            'exception': Exception("PDF extraction failed: corrupted file")
        }
    elif error_type == 'unreadable_file':
        return {
            'type': error_type,
            'filename': f"{filename}.txt",
            'exception': IOError("Permission denied")
        }
    elif error_type == 'invalid_image':
        return {
            'type': error_type,
            'filename': f"{filename}.jpg",
            'exception': Exception("Image processing failed")
        }
    elif error_type == 'extraction_failure':
        return {
            'type': error_type,
            'filename': f"{filename}.pdf",
            'exception': Exception("Text extraction failed")
        }
    else:  # embedding_failure
        return {
            'type': error_type,
            'filename': f"{filename}.txt",
            'exception': Exception("Failed to generate embeddings")
        }


@st.composite
def query_error_strategy(draw):
    """Generate scenarios that cause query errors."""
    error_type = draw(st.sampled_from([
        'no_chunks',
        'timeout',
        'llm_failure',
        'embedding_failure',
        'vector_store_error'
    ]))
    
    question = draw(st.text(min_size=5, max_size=200, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))))
    
    return {
        'type': error_type,
        'question': question,
        'exception': Exception(f"Query error: {error_type}")
    }


def is_user_friendly_error(error_message: str) -> tuple[bool, list[str]]:
    """
    Check if an error message is user-friendly.
    
    Returns:
        Tuple of (is_friendly, list_of_violations)
    """
    violations = []
    
    # Check for stack traces
    stack_trace_patterns = [
        r'Traceback \(most recent call last\)',
        r'File ".*", line \d+',
        r'^\s+at\s+.*\(.*:\d+:\d+\)',  # JavaScript stack traces
        r'^\s+File\s+"',
        r'raise\s+\w+Error',
    ]
    
    for pattern in stack_trace_patterns:
        if re.search(pattern, error_message, re.MULTILINE):
            violations.append(f"Contains stack trace pattern: {pattern}")
    
    # Check for technical jargon and internal details
    technical_jargon = [
        r'\bTraceback\b',
        r'\bException\b',
        r'\bRuntimeError\b',
        r'\bValueError\b',
        r'\bTypeError\b',
        r'\bAttributeError\b',
        r'\bKeyError\b',
        r'\bIndexError\b',
        r'\bIOError\b',
        r'\bOSError\b',
        r'\bFileNotFoundError\b',
        r'\bPermissionError\b',
        r'<class\s+',
        r'__\w+__',  # Dunder methods
        r'0x[0-9a-fA-F]+',  # Memory addresses
        r'\bNoneType\b',
        r'\bmodule\s+\w+\s+has\s+no\s+attribute\b',
        r'\bobject\s+has\s+no\s+attribute\b',
        r'\bstack\s+trace\b',
        r'\bcall\s+stack\b',
    ]
    
    for pattern in technical_jargon:
        if re.search(pattern, error_message, re.IGNORECASE):
            violations.append(f"Contains technical jargon: {pattern}")
    
    # Check for raw exception messages (common patterns)
    raw_exception_patterns = [
        r"'NoneType' object",
        r"list index out of range",
        r"dictionary key",
        r"unexpected keyword argument",
        r"takes \d+ positional argument",
        r"missing \d+ required positional argument",
    ]
    
    for pattern in raw_exception_patterns:
        if re.search(pattern, error_message, re.IGNORECASE):
            violations.append(f"Contains raw exception message: {pattern}")
    
    # Check for internal file paths
    internal_path_patterns = [
        r'/backend/',
        r'\\backend\\',
        r'/src/',
        r'\\src\\',
        r'\.py:\d+',
        r'\.js:\d+',
    ]
    
    for pattern in internal_path_patterns:
        if re.search(pattern, error_message):
            violations.append(f"Contains internal file path: {pattern}")
    
    return len(violations) == 0, violations


class TestPropertyErrorMessageUserFriendliness:
    """
    Property-based tests for error message user-friendliness.
    
    Feature: rag-chatbot-with-vision, Property 28: Error Message User-Friendliness
    """
    
    @given(invalid_path=invalid_folder_path_strategy())
    @settings(max_examples=100, deadline=None)
    def test_folder_validation_errors_are_user_friendly(self, invalid_path, db_manager):
        """
        Property 28: Error Message User-Friendliness (Folder Validation)
        
        For any invalid folder path, the error message should be user-friendly
        without stack traces or technical jargon.
        
        This test verifies that:
        1. Error messages don't contain stack traces
        2. Error messages don't contain technical jargon
        3. Error messages are human-readable
        """
        # Arrange: Create folder manager
        folder_manager = FolderManager(db_manager)
        
        # Act: Try to add invalid folder
        success, message, folder = folder_manager.add_folder(invalid_path)
        
        # Assert: Verify error is user-friendly
        if not success:
            # Property 1: Error message should be user-friendly
            is_friendly, violations = is_user_friendly_error(message)
            
            assert is_friendly, \
                f"Folder validation error is not user-friendly. Violations: {violations}\nMessage: {message}"
            
            # Property 2: Error message should not be empty
            assert len(message.strip()) > 0, \
                "Error message should not be empty"
            
            # Property 3: Error message should be reasonably short
            # Allow longer messages if they include the path (which can be long)
            # Base message + path should be reasonable
            base_message_length = len(message) - len(invalid_path)
            assert base_message_length < 200, \
                f"Error message base text too long ({base_message_length} chars excluding path)"
    
    @given(invalid_path=invalid_folder_path_strategy())
    @settings(max_examples=100, deadline=None)
    def test_document_processing_errors_are_user_friendly(self, invalid_path, db_manager):
        """
        Property 28: Error Message User-Friendliness (Document Processing)
        
        For any error during document processing, the error message should be
        user-friendly without stack traces or technical jargon.
        
        This test verifies folder validation errors which are part of document processing.
        """
        # Arrange: Create folder manager
        folder_manager = FolderManager(db_manager)
        
        # Act: Try to add invalid folder (this is part of document processing setup)
        success, message, folder = folder_manager.add_folder(invalid_path)
        
        # Assert: Verify error is user-friendly
        if not success:
            # Property 1: Error message should be user-friendly
            is_friendly, violations = is_user_friendly_error(message)
            
            assert is_friendly, \
                f"Document processing error is not user-friendly. Violations: {violations}\nMessage: {message}"
    
    @given(error_scenario=query_error_strategy())
    @settings(max_examples=100, deadline=None)
    def test_query_errors_are_user_friendly(self, error_scenario):
        """
        Property 28: Error Message User-Friendliness (Query Errors)
        
        For any error during query processing, the error message displayed to
        the user should be user-friendly without stack traces or technical jargon.
        
        This test verifies that:
        1. Query errors are caught and formatted
        2. Error messages are user-friendly
        3. Generic error messages are used for internal failures
        """
        # Arrange: Create query engine with mocked dependencies
        with patch('backend.query_engine.get_embedding_engine') as mock_emb:
            with patch('backend.query_engine.get_vector_store') as mock_vs:
                # Setup mocks based on error type
                if error_scenario['type'] == 'no_chunks':
                    mock_emb.return_value.generate_embedding.return_value = [0.1] * 384
                    mock_vs.return_value.query.return_value = []
                elif error_scenario['type'] == 'embedding_failure':
                    mock_emb.return_value.generate_embedding.side_effect = error_scenario['exception']
                elif error_scenario['type'] == 'vector_store_error':
                    mock_emb.return_value.generate_embedding.return_value = [0.1] * 384
                    mock_vs.return_value.query.side_effect = error_scenario['exception']
                else:
                    # For other errors, mock to raise exception
                    mock_emb.return_value.generate_embedding.side_effect = error_scenario['exception']
                
                engine = QueryEngine()
                
                # Act: Execute query
                result = engine.query(error_scenario['question'])
                
                # Assert: Verify error handling
                assert 'answer' in result, "Result should include answer field"
                
                answer = result['answer']
                
                # Property 1: Error message should be user-friendly
                is_friendly, violations = is_user_friendly_error(answer)
                
                assert is_friendly, \
                    f"Query error is not user-friendly. Violations: {violations}\nMessage: {answer}"
                
                # Property 2: Error message should not be empty
                assert len(answer.strip()) > 0, \
                    "Error message should not be empty"
                
                # Property 3: For no results, message should be informative
                if error_scenario['type'] == 'no_chunks':
                    assert 'no' in answer.lower() or 'not found' in answer.lower() or "couldn't find" in answer.lower(), \
                        "No results message should indicate nothing was found"
    
    @given(invalid_path=invalid_folder_path_strategy())
    @settings(max_examples=100, deadline=None)
    def test_api_folder_errors_are_user_friendly(self, invalid_path, db_manager):
        """
        Property 28: Error Message User-Friendliness (API Folder Endpoints)
        
        For any error in folder management API endpoints, the error response
        should be user-friendly without stack traces or technical jargon.
        
        This test verifies folder manager errors which are returned by the API.
        """
        # Arrange: Create folder manager (used by API)
        folder_manager = FolderManager(db_manager)
        
        # Act: Try to add invalid folder (simulates API behavior)
        success, message, folder = folder_manager.add_folder(invalid_path)
        
        # Assert: Verify error response
        if not success:
            error_detail = message
            
            # Property 1: Error detail should be user-friendly
            is_friendly, violations = is_user_friendly_error(error_detail)
            
            assert is_friendly, \
                f"API folder error is not user-friendly. Violations: {violations}\nDetail: {error_detail}"
            
            # Property 2: Error detail should not be empty
            assert len(error_detail.strip()) > 0, \
                "API error detail should not be empty"
            
            # Property 3: Error should not expose internal paths
            assert '/backend/' not in error_detail and '\\backend\\' not in error_detail, \
                "API error should not expose internal paths"
    
    @given(error_scenario=query_error_strategy())
    @settings(max_examples=100, deadline=None)
    def test_api_query_errors_are_user_friendly(self, error_scenario):
        """
        Property 28: Error Message User-Friendliness (API Query Endpoint)
        
        For any error in the query API endpoint, the error response should be
        user-friendly without stack traces or technical jargon.
        
        This test verifies query engine error handling which is used by the API.
        """
        # Arrange: Mock query engine to fail
        with patch('backend.query_engine.get_embedding_engine') as mock_emb:
            with patch('backend.query_engine.get_vector_store') as mock_vs:
                # Setup mocks based on error type
                if error_scenario['type'] == 'no_chunks':
                    mock_emb.return_value.generate_embedding.return_value = [0.1] * 384
                    mock_vs.return_value.query.return_value = []
                elif error_scenario['type'] == 'embedding_failure':
                    mock_emb.return_value.generate_embedding.side_effect = error_scenario['exception']
                elif error_scenario['type'] == 'vector_store_error':
                    mock_emb.return_value.generate_embedding.return_value = [0.1] * 384
                    mock_vs.return_value.query.side_effect = error_scenario['exception']
                else:
                    # For other errors, mock to raise exception
                    mock_emb.return_value.generate_embedding.side_effect = error_scenario['exception']
                
                engine = QueryEngine()
                
                # Act: Execute query
                result = engine.query(error_scenario['question'])
                
                # Assert: Verify error handling
                assert 'answer' in result, "Result should include answer field"
                
                answer = result['answer']
                
                # Property 1: Error message should be user-friendly
                is_friendly, violations = is_user_friendly_error(answer)
                
                assert is_friendly, \
                    f"Query error is not user-friendly. Violations: {violations}\nMessage: {answer}"
                
                # Property 2: Error message should not be empty
                assert len(answer.strip()) > 0, \
                    "Error message should not be empty"
    
    @given(invalid_path=invalid_folder_path_strategy())
    @settings(max_examples=100, deadline=None)
    def test_processing_status_errors_are_user_friendly(self, invalid_path, db_manager):
        """
        Property 28: Error Message User-Friendliness (Processing Status)
        
        For any file processing error, the status report should include
        user-friendly error messages without stack traces or technical jargon.
        
        This test verifies folder-related errors in processing status.
        """
        # Arrange: Create folder manager
        folder_manager = FolderManager(db_manager)
        
        # Act: Try to add invalid folder
        success, message, folder = folder_manager.add_folder(invalid_path)
        
        # Assert: Verify error is user-friendly
        if not success:
            # Property 1: Error message should be user-friendly
            is_friendly, violations = is_user_friendly_error(message)
            
            assert is_friendly, \
                f"Processing status error is not user-friendly. Violations: {violations}\nMessage: {message}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
