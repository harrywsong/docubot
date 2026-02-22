"""
Tests for ExportManager incremental export functionality.

Tests the actual filtering logic for incremental exports.
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from backend.export_manager import ExportManager, ExportResult
from backend.config import Config
from backend.vector_store import VectorStore
from backend.database import DatabaseManager
from backend.models import DocumentChunk


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def mock_config(temp_dir):
    """Create mock configuration."""
    config = Mock(spec=Config)
    config.CHROMADB_PATH = str(Path(temp_dir) / "chromadb")
    config.SQLITE_PATH = str(Path(temp_dir) / "app.db")
    config.EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
    config.CONVERSATIONAL_MODEL = "qwen2.5:3b"
    config.OLLAMA_MODEL = "qwen2.5vl:7b"
    config.EXPORT_DIR = str(Path(temp_dir) / "export")
    
    # Create mock data directories
    Path(config.CHROMADB_PATH).mkdir(parents=True, exist_ok=True)
    Path(config.SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    # Create dummy files
    Path(config.SQLITE_PATH).touch()
    (Path(config.CHROMADB_PATH) / "chroma.sqlite3").touch()
    
    return config


def test_incremental_export_filters_chunks_by_timestamp(temp_dir, mock_config):
    """Test that incremental export only includes chunks from files modified after timestamp."""
    
    # Create mock vector store with collection
    mock_collection = MagicMock()
    
    # Mock data: 5 chunks total, 2 from new files, 3 from old files
    base_timestamp = datetime(2024, 1, 1)
    new_timestamp = datetime(2024, 1, 15)
    
    # All chunks in the vector store
    all_chunks_data = {
        'ids': ['chunk1', 'chunk2', 'chunk3', 'chunk4', 'chunk5'],
        'embeddings': [[0.1] * 384] * 5,
        'documents': ['doc1', 'doc2', 'doc3', 'doc4', 'doc5'],
        'metadatas': [
            {'filename': 'old1.txt', 'folder_path': '/data', 'file_type': 'text'},  # Old file
            {'filename': 'old2.txt', 'folder_path': '/data', 'file_type': 'text'},  # Old file
            {'filename': 'new1.txt', 'folder_path': '/data', 'file_type': 'text'},  # New file
            {'filename': 'old3.txt', 'folder_path': '/data', 'file_type': 'text'},  # Old file
            {'filename': 'new2.txt', 'folder_path': '/data', 'file_type': 'text'},  # New file
        ]
    }
    
    mock_collection.get.return_value = all_chunks_data
    mock_collection.name = "documents"
    
    mock_vector_store = Mock(spec=VectorStore)
    mock_vector_store.collection = mock_collection
    mock_vector_store.get_stats.return_value = {
        "total_chunks": 5,
        "collection_name": "documents",
        "persist_directory": mock_config.CHROMADB_PATH
    }
    mock_vector_store.get_embedding_dimension.return_value = 384
    
    # Create mock database manager
    mock_db_manager = Mock(spec=DatabaseManager)
    
    # Mock transaction context manager
    mock_conn = MagicMock()
    
    # Setup different responses for different queries
    def execute_side_effect(query, params=None):
        mock_cursor = MagicMock()
        
        if "WHERE processed_at >" in query:
            # Query for files modified after timestamp
            # Return only the new files
            mock_cursor.fetchall.return_value = [
                {'file_path': '/data/new1.txt'},
                {'file_path': '/data/new2.txt'}
            ]
            mock_cursor.fetchone.return_value = [2]  # 2 new documents
        elif "COUNT(*)" in query and "processed_at" not in query:
            # Query for total documents
            mock_cursor.fetchone.return_value = [5]  # 5 total documents
        else:
            mock_cursor.fetchone.return_value = [0]
            mock_cursor.fetchall.return_value = []
        
        return mock_cursor
    
    mock_conn.execute.side_effect = execute_side_effect
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=False)
    
    mock_db_manager.transaction.return_value = mock_conn
    
    # Create ExportManager
    export_manager = ExportManager(mock_config, mock_vector_store, mock_db_manager)
    
    # Mock the ChromaDB client creation in _create_incremental_chromadb
    with patch('chromadb.PersistentClient') as mock_client_class:
        mock_client = MagicMock()
        mock_new_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_new_collection
        mock_client_class.return_value = mock_client
        
        # Create incremental export
        output_dir = Path(temp_dir) / "incremental_export"
        result = export_manager.create_export_package(
            output_dir=str(output_dir),
            incremental=True,
            since_timestamp=new_timestamp
        )
        
        # Verify the result
        assert result.success is True
        
        # Verify that only 2 chunks were added to the new collection (from new files)
        mock_new_collection.add.assert_called_once()
        call_args = mock_new_collection.add.call_args
        
        # Check that only chunks from new files were included
        added_ids = call_args.kwargs['ids']
        added_metadatas = call_args.kwargs['metadatas']
        
        assert len(added_ids) == 2, f"Expected 2 chunks, got {len(added_ids)}"
        
        # Verify the chunks are from new files
        for metadata in added_metadatas:
            filename = metadata['filename']
            assert filename in ['new1.txt', 'new2.txt'], f"Unexpected file: {filename}"


def test_incremental_export_with_no_new_files(temp_dir, mock_config):
    """Test incremental export when no files have been modified."""
    
    # Create mock vector store
    mock_collection = MagicMock()
    mock_collection.get.return_value = {
        'ids': ['chunk1'],
        'embeddings': [[0.1] * 384],
        'documents': ['doc1'],
        'metadatas': [{'filename': 'old.txt', 'folder_path': '/data', 'file_type': 'text'}]
    }
    mock_collection.name = "documents"
    
    mock_vector_store = Mock(spec=VectorStore)
    mock_vector_store.collection = mock_collection
    mock_vector_store.get_stats.return_value = {
        "total_chunks": 1,
        "collection_name": "documents",
        "persist_directory": mock_config.CHROMADB_PATH
    }
    mock_vector_store.get_embedding_dimension.return_value = 384
    
    # Create mock database manager with no new files
    mock_db_manager = Mock(spec=DatabaseManager)
    mock_conn = MagicMock()
    
    def execute_side_effect(query, params=None):
        mock_cursor = MagicMock()
        
        if "WHERE processed_at >" in query:
            # No new files
            mock_cursor.fetchall.return_value = []
            mock_cursor.fetchone.return_value = [0]
        else:
            mock_cursor.fetchone.return_value = [1]
            mock_cursor.fetchall.return_value = []
        
        return mock_cursor
    
    mock_conn.execute.side_effect = execute_side_effect
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=False)
    
    mock_db_manager.transaction.return_value = mock_conn
    
    # Create ExportManager
    export_manager = ExportManager(mock_config, mock_vector_store, mock_db_manager)
    
    # Create incremental export
    output_dir = Path(temp_dir) / "incremental_export_empty"
    result = export_manager.create_export_package(
        output_dir=str(output_dir),
        incremental=True,
        since_timestamp=datetime(2024, 1, 15)
    )
    
    # Verify the result
    assert result.success is True
    
    # Check statistics show no new chunks
    assert result.statistics.get('new_chunks', 0) == 0
    assert result.statistics.get('new_documents', 0) == 0


def test_incremental_export_statistics_accuracy(temp_dir, mock_config):
    """Test that incremental export statistics are accurate."""
    
    # Create mock vector store
    mock_collection = MagicMock()
    
    all_chunks_data = {
        'ids': ['chunk1', 'chunk2', 'chunk3'],
        'embeddings': [[0.1] * 384] * 3,
        'documents': ['doc1', 'doc2', 'doc3'],
        'metadatas': [
            {'filename': 'new1.txt', 'folder_path': '/data', 'file_type': 'text'},
            {'filename': 'new1.txt', 'folder_path': '/data', 'file_type': 'text'},  # Same file, 2 chunks
            {'filename': 'old1.txt', 'folder_path': '/data', 'file_type': 'text'},
        ]
    }
    
    # Mock collection.get() to return all chunks data
    # This will be called twice: once for statistics, once for filtering
    mock_collection.get.return_value = all_chunks_data
    mock_collection.name = "documents"
    
    mock_vector_store = Mock(spec=VectorStore)
    mock_vector_store.collection = mock_collection
    mock_vector_store.get_stats.return_value = {
        "total_chunks": 3,
        "collection_name": "documents",
        "persist_directory": mock_config.CHROMADB_PATH
    }
    mock_vector_store.get_embedding_dimension.return_value = 384
    
    # Create mock database manager
    mock_db_manager = Mock(spec=DatabaseManager)
    mock_conn = MagicMock()
    
    def execute_side_effect(query, params=None):
        mock_cursor = MagicMock()
        
        if "WHERE processed_at >" in query:
            if "SELECT file_path" in query:
                # Query for file paths modified after timestamp
                mock_cursor.fetchall.return_value = [
                    {'file_path': '/data/new1.txt'}
                ]
            else:
                # Query for count of modified documents
                mock_cursor.fetchone.return_value = [1]
        else:
            mock_cursor.fetchone.return_value = [2]  # 2 total documents
            mock_cursor.fetchall.return_value = []
        
        return mock_cursor
    
    mock_conn.execute.side_effect = execute_side_effect
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=False)
    
    mock_db_manager.transaction.return_value = mock_conn
    
    # Create ExportManager
    export_manager = ExportManager(mock_config, mock_vector_store, mock_db_manager)
    
    # Mock ChromaDB client
    with patch('chromadb.PersistentClient') as mock_client_class:
        mock_client = MagicMock()
        mock_new_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_new_collection
        mock_client_class.return_value = mock_client
        
        # Create incremental export
        output_dir = Path(temp_dir) / "incremental_export_stats"
        result = export_manager.create_export_package(
            output_dir=str(output_dir),
            incremental=True,
            since_timestamp=datetime(2024, 1, 15)
        )
        
        # Verify statistics
        assert result.success is True
        assert result.statistics['new_documents'] == 1
        assert result.statistics['new_chunks'] == 2  # 2 chunks from the new file
        assert result.statistics['total_chunks'] == 2  # For incremental, total = new
        
        # Verify manifest
        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        assert manifest['export_type'] == 'incremental'
        assert manifest['incremental']['is_incremental'] is True
        assert manifest['statistics']['new_chunks'] == 2


def test_incremental_export_manifest_includes_base_version(temp_dir, mock_config):
    """Test that incremental export manifest includes base_version and since_timestamp."""
    
    # Create minimal mocks
    mock_vector_store = Mock(spec=VectorStore)
    mock_vector_store.get_stats.return_value = {"total_chunks": 0}
    mock_vector_store.get_embedding_dimension.return_value = 384
    mock_vector_store.collection = MagicMock()
    mock_vector_store.collection.get.return_value = {
        'ids': [], 'embeddings': [], 'documents': [], 'metadatas': []
    }
    mock_vector_store.collection.name = "documents"
    
    mock_db_manager = Mock(spec=DatabaseManager)
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = [0]
    mock_cursor.fetchall.return_value = []
    mock_conn.execute.return_value = mock_cursor
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=False)
    mock_db_manager.transaction.return_value = mock_conn
    
    # Create ExportManager
    export_manager = ExportManager(mock_config, mock_vector_store, mock_db_manager)
    
    # Create incremental export with specific timestamp
    since_timestamp = datetime(2024, 1, 15, 10, 30, 0)
    output_dir = Path(temp_dir) / "incremental_export_manifest"
    
    result = export_manager.create_export_package(
        output_dir=str(output_dir),
        incremental=True,
        since_timestamp=since_timestamp
    )
    
    assert result.success is True
    
    # Read and verify manifest
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    # Verify incremental metadata
    assert manifest['incremental']['is_incremental'] is True
    assert manifest['incremental']['since_timestamp'] == since_timestamp.isoformat()
    # base_version is None for now (could be enhanced in future)
    assert manifest['incremental']['base_version'] is None
