"""
Unit tests for DataLoader class.

Tests data loading, manifest validation, and error handling.
"""

import json
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from backend.data_loader import DataLoader, DataLoadError, ManifestError
from backend.config import Config
from backend.models import ManifestValidation


class TestDataLoader:
    """Test suite for DataLoader class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test data."""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)
    
    @pytest.fixture
    def mock_config(self, temp_dir):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.CHROMADB_PATH = str(Path(temp_dir) / "chromadb")
        config.SQLITE_PATH = str(Path(temp_dir) / "app.db")
        config.MANIFEST_PATH = str(Path(temp_dir) / "manifest.json")
        config.EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
        config.CONVERSATIONAL_MODEL = "qwen2.5:3b"
        return config
    
    @pytest.fixture
    def data_loader(self, mock_config):
        """Create DataLoader instance."""
        return DataLoader(mock_config)
    
    def test_init(self, data_loader, mock_config):
        """Test DataLoader initialization."""
        assert data_loader.config == mock_config
    
    def test_load_vector_store_missing_directory(self, data_loader):
        """Test loading vector store when directory doesn't exist."""
        with pytest.raises(DataLoadError) as exc_info:
            data_loader.load_vector_store()
        
        assert "Vector store not found" in str(exc_info.value)
        assert "export package has been transferred" in str(exc_info.value)
    
    def test_load_vector_store_empty_directory(self, data_loader, temp_dir):
        """Test loading vector store when directory is empty."""
        # Create empty directory
        chromadb_path = Path(temp_dir) / "chromadb"
        chromadb_path.mkdir(parents=True)
        
        with pytest.raises(DataLoadError) as exc_info:
            data_loader.load_vector_store()
        
        assert "Vector store directory is empty" in str(exc_info.value)
    
    @patch('backend.data_loader.VectorStore')
    def test_load_vector_store_success(self, mock_vector_store_class, data_loader, temp_dir):
        """Test successful vector store loading."""
        # Create non-empty directory
        chromadb_path = Path(temp_dir) / "chromadb"
        chromadb_path.mkdir(parents=True)
        (chromadb_path / "chroma.sqlite3").touch()
        
        # Mock VectorStore
        mock_vs = Mock()
        mock_vs.get_stats.return_value = {'total_chunks': 100}
        mock_vector_store_class.return_value = mock_vs
        
        result = data_loader.load_vector_store()
        
        assert result == mock_vs
        mock_vector_store_class.assert_called_once_with(
            persist_directory=data_loader.config.CHROMADB_PATH,
            read_only=True
        )
        mock_vs.initialize.assert_called_once()
    
    @patch('backend.data_loader.VectorStore')
    def test_load_vector_store_empty_data(self, mock_vector_store_class, data_loader, temp_dir):
        """Test loading vector store with no chunks."""
        # Create non-empty directory
        chromadb_path = Path(temp_dir) / "chromadb"
        chromadb_path.mkdir(parents=True)
        (chromadb_path / "chroma.sqlite3").touch()
        
        # Mock VectorStore with no chunks
        mock_vs = Mock()
        mock_vs.get_stats.return_value = {'total_chunks': 0}
        mock_vector_store_class.return_value = mock_vs
        
        with pytest.raises(DataLoadError) as exc_info:
            data_loader.load_vector_store()
        
        assert "Vector store is empty" in str(exc_info.value)
    
    def test_load_database_missing_file(self, data_loader):
        """Test loading database when file doesn't exist."""
        with pytest.raises(DataLoadError) as exc_info:
            data_loader.load_database()
        
        assert "Database not found" in str(exc_info.value)
    
    def test_load_database_empty_file(self, data_loader, temp_dir):
        """Test loading database when file is empty."""
        # Create empty database file
        db_path = Path(temp_dir) / "app.db"
        db_path.touch()
        
        with pytest.raises(DataLoadError) as exc_info:
            data_loader.load_database()
        
        assert "Database file is empty" in str(exc_info.value)
    
    @patch('backend.data_loader.DatabaseManager')
    def test_load_database_success(self, mock_db_manager_class, data_loader, temp_dir):
        """Test successful database loading."""
        # Create non-empty database file
        db_path = Path(temp_dir) / "app.db"
        db_path.write_text("dummy database content")
        
        # Mock DatabaseManager
        mock_db = Mock()
        mock_db_manager_class.return_value = mock_db
        
        result = data_loader.load_database()
        
        assert result == mock_db
        mock_db_manager_class.assert_called_once_with(db_path=data_loader.config.SQLITE_PATH)
    
    def test_validate_manifest_missing_file(self, data_loader):
        """Test manifest validation when file doesn't exist."""
        result = data_loader.validate_manifest()
        
        assert result.valid is True  # Allow operation without manifest
        assert result.embedding_dimension_match is False
        assert result.model_compatible is False
        assert len(result.errors) == 0
        assert len(result.warnings) == 1
        assert "Manifest file not found" in result.warnings[0]
    
    def test_validate_manifest_invalid_json(self, data_loader, temp_dir):
        """Test manifest validation with invalid JSON."""
        # Create invalid JSON file
        manifest_path = Path(temp_dir) / "manifest.json"
        manifest_path.write_text("{ invalid json }")
        
        result = data_loader.validate_manifest()
        
        assert result.valid is False
        assert len(result.errors) == 1
        assert "not valid JSON" in result.errors[0]
    
    def test_validate_manifest_missing_fields(self, data_loader, temp_dir):
        """Test manifest validation with missing required fields."""
        # Create manifest with missing fields
        manifest_path = Path(temp_dir) / "manifest.json"
        manifest_data = {
            "version": "1.0"
            # Missing: created_at, desktop_config, pi_requirements
        }
        manifest_path.write_text(json.dumps(manifest_data))
        
        result = data_loader.validate_manifest()
        
        assert result.valid is False
        assert len(result.errors) == 1
        assert "missing required fields" in result.errors[0]
    
    @patch('backend.data_loader.EmbeddingEngine')
    def test_validate_manifest_dimension_mismatch(self, mock_embedding_engine_class, data_loader, temp_dir):
        """Test manifest validation with embedding dimension mismatch."""
        # Create valid manifest
        manifest_path = Path(temp_dir) / "manifest.json"
        manifest_data = {
            "version": "1.0",
            "created_at": "2024-01-15T10:30:00Z",
            "desktop_config": {
                "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
                "embedding_dimension": 512  # Wrong dimension
            },
            "pi_requirements": {
                "conversational_model": "qwen2.5:3b",
                "min_memory_gb": 4,
                "embedding_dimension": 512
            }
        }
        manifest_path.write_text(json.dumps(manifest_data))
        
        # Mock EmbeddingEngine to return different dimension
        mock_engine = Mock()
        mock_engine.get_embedding_dimension.return_value = 384
        mock_embedding_engine_class.return_value = mock_engine
        
        result = data_loader.validate_manifest()
        
        assert result.valid is False
        assert result.embedding_dimension_match is False
        assert len(result.errors) == 1
        assert "Embedding dimension mismatch" in result.errors[0]
        assert "512" in result.errors[0]
        assert "384" in result.errors[0]
    
    @patch('backend.data_loader.EmbeddingEngine')
    def test_validate_manifest_success(self, mock_embedding_engine_class, data_loader, temp_dir):
        """Test successful manifest validation."""
        # Create valid manifest
        manifest_path = Path(temp_dir) / "manifest.json"
        manifest_data = {
            "version": "1.0",
            "created_at": "2024-01-15T10:30:00Z",
            "desktop_config": {
                "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
                "embedding_dimension": 384
            },
            "pi_requirements": {
                "conversational_model": "qwen2.5:3b",
                "min_memory_gb": 4,
                "embedding_dimension": 384
            }
        }
        manifest_path.write_text(json.dumps(manifest_data))
        
        # Mock EmbeddingEngine
        mock_engine = Mock()
        mock_engine.get_embedding_dimension.return_value = 384
        mock_embedding_engine_class.return_value = mock_engine
        
        result = data_loader.validate_manifest()
        
        assert result.valid is True
        assert result.embedding_dimension_match is True
        assert result.model_compatible is True
        assert len(result.errors) == 0
    
    @patch('backend.data_loader.EmbeddingEngine')
    def test_validate_manifest_model_mismatch_warning(self, mock_embedding_engine_class, data_loader, temp_dir):
        """Test manifest validation with model mismatch (warning only)."""
        # Create valid manifest with different model
        manifest_path = Path(temp_dir) / "manifest.json"
        manifest_data = {
            "version": "1.0",
            "created_at": "2024-01-15T10:30:00Z",
            "desktop_config": {
                "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
                "embedding_dimension": 384
            },
            "pi_requirements": {
                "conversational_model": "qwen2.5:7b",  # Different from config
                "min_memory_gb": 4,
                "embedding_dimension": 384
            }
        }
        manifest_path.write_text(json.dumps(manifest_data))
        
        # Mock EmbeddingEngine
        mock_engine = Mock()
        mock_engine.get_embedding_dimension.return_value = 384
        mock_embedding_engine_class.return_value = mock_engine
        
        result = data_loader.validate_manifest()
        
        assert result.valid is True  # Still valid, just a warning
        assert result.embedding_dimension_match is True
        assert result.model_compatible is False
        assert len(result.errors) == 0
        assert len(result.warnings) == 1
        assert "Model mismatch" in result.warnings[0]
    
    @patch('backend.data_loader.EmbeddingEngine')
    @patch('psutil.virtual_memory')
    def test_validate_manifest_low_memory_warning(self, mock_virtual_memory, mock_embedding_engine_class, data_loader, temp_dir):
        """Test manifest validation with low memory warning."""
        # Create valid manifest
        manifest_path = Path(temp_dir) / "manifest.json"
        manifest_data = {
            "version": "1.0",
            "created_at": "2024-01-15T10:30:00Z",
            "desktop_config": {
                "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
                "embedding_dimension": 384
            },
            "pi_requirements": {
                "conversational_model": "qwen2.5:3b",
                "min_memory_gb": 8,  # Require 8GB
                "embedding_dimension": 384
            }
        }
        manifest_path.write_text(json.dumps(manifest_data))
        
        # Mock EmbeddingEngine
        mock_engine = Mock()
        mock_engine.get_embedding_dimension.return_value = 384
        mock_embedding_engine_class.return_value = mock_engine
        
        # Mock psutil to report low memory
        mock_memory = Mock()
        mock_memory.total = 4 * 1024 ** 3  # 4GB
        mock_virtual_memory.return_value = mock_memory
        
        result = data_loader.validate_manifest()
        
        assert result.valid is True  # Still valid, just a warning
        assert len(result.warnings) >= 1
        memory_warnings = [w for w in result.warnings if "memory" in w.lower()]
        assert len(memory_warnings) == 1
        assert "below recommended minimum" in memory_warnings[0]
    
    @patch('backend.data_loader.EmbeddingEngine')
    def test_validate_manifest_custom_path(self, mock_embedding_engine_class, data_loader, temp_dir):
        """Test manifest validation with custom path."""
        # Create manifest at custom location
        custom_path = Path(temp_dir) / "custom_manifest.json"
        manifest_data = {
            "version": "1.0",
            "created_at": "2024-01-15T10:30:00Z",
            "desktop_config": {
                "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
                "embedding_dimension": 384
            },
            "pi_requirements": {
                "conversational_model": "qwen2.5:3b",
                "embedding_dimension": 384
            }
        }
        custom_path.write_text(json.dumps(manifest_data))
        
        # Mock EmbeddingEngine
        mock_engine = Mock()
        mock_engine.get_embedding_dimension.return_value = 384
        mock_embedding_engine_class.return_value = mock_engine
        
        # Should use custom path instead of config default
        result = data_loader.validate_manifest(manifest_path=str(custom_path))
        
        # Should successfully validate the custom manifest
        assert result.valid is True
        assert result.embedding_dimension_match is True


class TestDataLoaderErrorHandling:
    """Test error handling in DataLoader."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.CHROMADB_PATH = "/nonexistent/chromadb"
        config.SQLITE_PATH = "/nonexistent/app.db"
        config.MANIFEST_PATH = "/nonexistent/manifest.json"
        config.EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
        config.CONVERSATIONAL_MODEL = "qwen2.5:3b"
        return config
    
    def test_load_vector_store_exception_handling(self, mock_config):
        """Test that exceptions during vector store loading are handled gracefully."""
        data_loader = DataLoader(mock_config)
        
        with pytest.raises(DataLoadError) as exc_info:
            data_loader.load_vector_store()
        
        # Should provide clear error message
        assert "Vector store not found" in str(exc_info.value)
    
    def test_load_database_exception_handling(self, mock_config):
        """Test that exceptions during database loading are handled gracefully."""
        data_loader = DataLoader(mock_config)
        
        with pytest.raises(DataLoadError) as exc_info:
            data_loader.load_database()
        
        # Should provide clear error message
        assert "Database not found" in str(exc_info.value)
