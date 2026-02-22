"""
Tests for ProcessingValidator class.

Tests validation of processed documents, embedding coverage, and metadata completeness.
"""

import pytest
from unittest.mock import Mock, MagicMock

from backend.processing_validator import ProcessingValidator
from backend.vector_store import VectorStore
from backend.database import DatabaseManager
from backend.models import ProcessingReport


@pytest.fixture
def mock_db_manager():
    """Create mock database manager."""
    db = Mock(spec=DatabaseManager)
    
    # Mock transaction context manager
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = [10]  # 10 documents
    mock_conn.execute.return_value = mock_cursor
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=False)
    
    db.transaction.return_value = mock_conn
    
    return db


@pytest.fixture
def mock_vector_store_valid():
    """Create mock vector store with valid data."""
    vs = Mock(spec=VectorStore)
    
    # Mock collection
    mock_collection = MagicMock()
    
    # Mock get_stats
    vs.get_stats.return_value = {
        "total_chunks": 50,
        "collection_name": "documents",
        "persist_directory": "data/chromadb"
    }
    
    # Mock collection.get for valid data (all chunks have embeddings and metadata)
    mock_collection.get.return_value = {
        'ids': ['chunk1', 'chunk2', 'chunk3'],
        'embeddings': [
            [0.1] * 384,  # Valid embedding
            [0.2] * 384,  # Valid embedding
            [0.3] * 384   # Valid embedding
        ],
        'metadatas': [
            {'filename': 'file1.txt', 'folder_path': '/data', 'file_type': 'text'},
            {'filename': 'file2.txt', 'folder_path': '/data', 'file_type': 'text'},
            {'filename': 'file3.txt', 'folder_path': '/data', 'file_type': 'text'}
        ]
    }
    
    vs.collection = mock_collection
    
    return vs


@pytest.fixture
def mock_vector_store_missing_embeddings():
    """Create mock vector store with missing embeddings."""
    vs = Mock(spec=VectorStore)
    
    # Mock collection
    mock_collection = MagicMock()
    
    # Mock get_stats
    vs.get_stats.return_value = {
        "total_chunks": 50,
        "collection_name": "documents",
        "persist_directory": "data/chromadb"
    }
    
    # Mock collection.get with some missing embeddings
    mock_collection.get.return_value = {
        'ids': ['chunk1', 'chunk2', 'chunk3'],
        'embeddings': [
            [0.1] * 384,  # Valid embedding
            None,         # Missing embedding
            []            # Empty embedding
        ],
        'metadatas': [
            {'filename': 'file1.txt', 'folder_path': '/data', 'file_type': 'text'},
            {'filename': 'file2.txt', 'folder_path': '/data', 'file_type': 'text'},
            {'filename': 'file3.txt', 'folder_path': '/data', 'file_type': 'text'}
        ]
    }
    
    vs.collection = mock_collection
    
    return vs


@pytest.fixture
def mock_vector_store_incomplete_metadata():
    """Create mock vector store with incomplete metadata."""
    vs = Mock(spec=VectorStore)
    
    # Mock collection
    mock_collection = MagicMock()
    
    # Mock get_stats
    vs.get_stats.return_value = {
        "total_chunks": 50,
        "collection_name": "documents",
        "persist_directory": "data/chromadb"
    }
    
    # Mock collection.get with incomplete metadata
    mock_collection.get.return_value = {
        'ids': ['chunk1', 'chunk2', 'chunk3', 'chunk4'],
        'embeddings': [
            [0.1] * 384,
            [0.2] * 384,
            [0.3] * 384,
            [0.4] * 384
        ],
        'metadatas': [
            {'filename': 'file1.txt', 'folder_path': '/data', 'file_type': 'text'},  # Valid
            {'filename': 'file2.txt', 'folder_path': '/data'},  # Missing file_type
            {'folder_path': '/data', 'file_type': 'text'},  # Missing filename
            None  # Missing metadata entirely
        ]
    }
    
    vs.collection = mock_collection
    
    return vs


def test_processing_validator_initialization(mock_vector_store_valid, mock_db_manager):
    """Test ProcessingValidator initializes correctly."""
    validator = ProcessingValidator(mock_vector_store_valid, mock_db_manager)
    
    assert validator.vector_store == mock_vector_store_valid
    assert validator.db_manager == mock_db_manager


def test_validate_processing_all_valid(mock_vector_store_valid, mock_db_manager):
    """Test validation passes when all data is valid."""
    validator = ProcessingValidator(mock_vector_store_valid, mock_db_manager)
    
    report = validator.validate_processing()
    
    # Check report structure
    assert isinstance(report, ProcessingReport)
    assert report.total_documents == 10
    assert report.total_chunks == 50
    assert report.total_embeddings == 50
    assert len(report.missing_embeddings) == 0
    assert len(report.incomplete_metadata) == 0
    assert report.validation_passed is True


def test_validate_processing_missing_embeddings(mock_vector_store_missing_embeddings, mock_db_manager):
    """Test validation detects missing embeddings."""
    validator = ProcessingValidator(mock_vector_store_missing_embeddings, mock_db_manager)
    
    report = validator.validate_processing()
    
    # Check report detects missing embeddings
    assert report.total_chunks == 50
    assert len(report.missing_embeddings) == 2  # chunk2 and chunk3
    assert 'chunk2' in report.missing_embeddings
    assert 'chunk3' in report.missing_embeddings
    assert report.validation_passed is False


def test_validate_processing_incomplete_metadata(mock_vector_store_incomplete_metadata, mock_db_manager):
    """Test validation detects incomplete metadata."""
    validator = ProcessingValidator(mock_vector_store_incomplete_metadata, mock_db_manager)
    
    report = validator.validate_processing()
    
    # Check report detects incomplete metadata
    assert report.total_chunks == 50
    assert len(report.incomplete_metadata) == 3  # chunk2, chunk3, chunk4
    assert 'chunk2' in report.incomplete_metadata
    assert 'chunk3' in report.incomplete_metadata
    assert 'chunk4' in report.incomplete_metadata
    assert report.validation_passed is False


def test_check_embedding_coverage_all_valid(mock_vector_store_valid, mock_db_manager):
    """Test embedding coverage check with all valid embeddings."""
    validator = ProcessingValidator(mock_vector_store_valid, mock_db_manager)
    
    missing = validator.check_embedding_coverage()
    
    assert len(missing) == 0


def test_check_embedding_coverage_missing(mock_vector_store_missing_embeddings, mock_db_manager):
    """Test embedding coverage check detects missing embeddings."""
    validator = ProcessingValidator(mock_vector_store_missing_embeddings, mock_db_manager)
    
    missing = validator.check_embedding_coverage()
    
    assert len(missing) == 2
    assert 'chunk2' in missing
    assert 'chunk3' in missing


def test_check_metadata_completeness_all_valid(mock_vector_store_valid, mock_db_manager):
    """Test metadata completeness check with all valid metadata."""
    validator = ProcessingValidator(mock_vector_store_valid, mock_db_manager)
    
    incomplete = validator.check_metadata_completeness()
    
    assert len(incomplete) == 0


def test_check_metadata_completeness_incomplete(mock_vector_store_incomplete_metadata, mock_db_manager):
    """Test metadata completeness check detects incomplete metadata."""
    validator = ProcessingValidator(mock_vector_store_incomplete_metadata, mock_db_manager)
    
    incomplete = validator.check_metadata_completeness()
    
    assert len(incomplete) == 3
    assert 'chunk2' in incomplete  # Missing file_type
    assert 'chunk3' in incomplete  # Missing filename
    assert 'chunk4' in incomplete  # Missing metadata entirely


def test_validate_processing_empty_vector_store(mock_db_manager):
    """Test validation handles empty vector store."""
    vs = Mock(spec=VectorStore)
    vs.get_stats.return_value = {"total_chunks": 0}
    
    mock_collection = MagicMock()
    mock_collection.get.return_value = {'ids': [], 'embeddings': [], 'metadatas': []}
    vs.collection = mock_collection
    
    validator = ProcessingValidator(vs, mock_db_manager)
    
    report = validator.validate_processing()
    
    # Empty vector store should fail validation
    assert report.total_chunks == 0
    assert report.total_embeddings == 0
    assert report.validation_passed is False


def test_validate_processing_calculates_embeddings_correctly(mock_vector_store_missing_embeddings, mock_db_manager):
    """Test that total_embeddings is calculated correctly."""
    validator = ProcessingValidator(mock_vector_store_missing_embeddings, mock_db_manager)
    
    report = validator.validate_processing()
    
    # total_embeddings = total_chunks - missing_embeddings
    expected_embeddings = report.total_chunks - len(report.missing_embeddings)
    assert report.total_embeddings == expected_embeddings


def test_check_embedding_coverage_handles_exceptions(mock_db_manager):
    """Test embedding coverage check handles exceptions gracefully."""
    vs = Mock(spec=VectorStore)
    
    # Mock collection that raises exception
    mock_collection = MagicMock()
    mock_collection.get.side_effect = Exception("Database error")
    vs.collection = mock_collection
    
    validator = ProcessingValidator(vs, mock_db_manager)
    
    # Should not raise exception, should return empty list
    missing = validator.check_embedding_coverage()
    
    assert isinstance(missing, list)


def test_check_metadata_completeness_handles_exceptions(mock_db_manager):
    """Test metadata completeness check handles exceptions gracefully."""
    vs = Mock(spec=VectorStore)
    
    # Mock collection that raises exception
    mock_collection = MagicMock()
    mock_collection.get.side_effect = Exception("Database error")
    vs.collection = mock_collection
    
    validator = ProcessingValidator(vs, mock_db_manager)
    
    # Should not raise exception, should return empty list
    incomplete = validator.check_metadata_completeness()
    
    assert isinstance(incomplete, list)
