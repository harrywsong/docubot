"""
Tests for ExportManager class.

Tests export package creation, validation, and deployment instructions generation.
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from backend.export_manager import ExportManager, ExportResult, ValidationResult
from backend.config import Config
from backend.vector_store import VectorStore
from backend.database import DatabaseManager


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


@pytest.fixture
def mock_vector_store():
    """Create mock vector store."""
    vs = Mock(spec=VectorStore)
    vs.get_stats.return_value = {
        "total_chunks": 100,
        "collection_name": "documents",
        "persist_directory": "data/chromadb"
    }
    vs.get_embedding_dimension.return_value = 384
    return vs


@pytest.fixture
def mock_db_manager():
    """Create mock database manager."""
    db = Mock(spec=DatabaseManager)
    
    # Mock transaction context manager
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = [50]  # 50 documents
    mock_conn.execute.return_value = mock_cursor
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=False)
    
    db.transaction.return_value = mock_conn
    
    return db


@pytest.fixture
def export_manager(mock_config, mock_vector_store, mock_db_manager):
    """Create ExportManager instance."""
    return ExportManager(mock_config, mock_vector_store, mock_db_manager)


def test_export_manager_initialization(export_manager, mock_config, mock_vector_store, mock_db_manager):
    """Test ExportManager initializes correctly."""
    assert export_manager.config == mock_config
    assert export_manager.vector_store == mock_vector_store
    assert export_manager.db_manager == mock_db_manager


def test_create_export_package_full(export_manager, temp_dir):
    """Test creating a full export package."""
    output_dir = Path(temp_dir) / "test_export"
    
    result = export_manager.create_export_package(
        output_dir=str(output_dir),
        incremental=False
    )
    
    # Check result
    assert result.success is True
    assert len(result.errors) == 0
    assert result.size_bytes > 0
    assert "total_chunks" in result.statistics
    assert "total_documents" in result.statistics
    
    # Check package contents
    assert output_dir.exists()
    assert (output_dir / "chromadb").exists()
    assert (output_dir / "app.db").exists()
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "config_pi.py").exists()
    assert (output_dir / "DEPLOYMENT.md").exists()
    
    # Check archive was created
    assert result.archive_path
    assert Path(result.archive_path).exists()
    assert result.archive_path.endswith(".tar.gz")


def test_create_export_package_incremental(export_manager, temp_dir):
    """Test creating an incremental export package."""
    output_dir = Path(temp_dir) / "test_export_incremental"
    since_timestamp = datetime(2024, 1, 1)
    
    result = export_manager.create_export_package(
        output_dir=str(output_dir),
        incremental=True,
        since_timestamp=since_timestamp
    )
    
    # Check result
    assert result.success is True
    
    # Check manifest indicates incremental export
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    assert manifest["export_type"] == "incremental"
    assert manifest["incremental"]["is_incremental"] is True
    assert manifest["incremental"]["since_timestamp"] is not None


def test_create_export_package_missing_chromadb(export_manager, temp_dir):
    """Test export fails gracefully when ChromaDB is missing."""
    # Remove ChromaDB directory
    shutil.rmtree(export_manager.config.CHROMADB_PATH)
    
    output_dir = Path(temp_dir) / "test_export_fail"
    result = export_manager.create_export_package(output_dir=str(output_dir))
    
    # Check result indicates failure
    assert result.success is False
    assert len(result.errors) > 0
    assert "Vector store" in result.errors[0] or "ChromaDB" in result.errors[0]


def test_create_export_package_missing_database(export_manager, temp_dir):
    """Test export fails gracefully when database is missing."""
    # Remove database file
    Path(export_manager.config.SQLITE_PATH).unlink()
    
    output_dir = Path(temp_dir) / "test_export_fail"
    result = export_manager.create_export_package(output_dir=str(output_dir))
    
    # Check result indicates failure
    assert result.success is False
    assert len(result.errors) > 0
    assert "SQLite" in result.errors[0] or "database" in result.errors[0].lower()


def test_validate_export_package_valid(export_manager, temp_dir):
    """Test validation of a valid export package."""
    # Create a valid export package first
    output_dir = Path(temp_dir) / "test_export"
    result = export_manager.create_export_package(output_dir=str(output_dir))
    
    assert result.success is True
    
    # Validate the package
    validation = export_manager.validate_export_package(str(output_dir))
    
    assert validation.valid is True
    assert len(validation.errors) == 0


def test_validate_export_package_missing_directory(export_manager, temp_dir):
    """Test validation fails for non-existent package."""
    non_existent = Path(temp_dir) / "does_not_exist"
    
    validation = export_manager.validate_export_package(str(non_existent))
    
    assert validation.valid is False
    assert len(validation.errors) > 0
    assert "not found" in validation.errors[0].lower()


def test_validate_export_package_missing_files(export_manager, temp_dir):
    """Test validation fails when required files are missing."""
    # Create package directory but don't add all files
    package_dir = Path(temp_dir) / "incomplete_package"
    package_dir.mkdir(parents=True)
    
    # Only create some files
    (package_dir / "chromadb").mkdir()
    (package_dir / "app.db").touch()
    # Missing: manifest.json, config_pi.py, DEPLOYMENT.md
    
    validation = export_manager.validate_export_package(str(package_dir))
    
    assert validation.valid is False
    assert len(validation.errors) >= 3  # At least 3 missing files


def test_validate_export_package_invalid_manifest(export_manager, temp_dir):
    """Test validation detects invalid manifest."""
    # Create package with invalid manifest
    package_dir = Path(temp_dir) / "invalid_manifest"
    package_dir.mkdir(parents=True)
    
    # Create required directories/files
    (package_dir / "chromadb").mkdir()
    (package_dir / "app.db").touch()
    (package_dir / "config_pi.py").touch()
    (package_dir / "DEPLOYMENT.md").touch()
    
    # Create invalid manifest (missing required fields)
    manifest_path = package_dir / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump({"version": "1.0"}, f)  # Missing many required fields
    
    validation = export_manager.validate_export_package(str(package_dir))
    
    assert validation.valid is False
    assert len(validation.errors) > 0


def test_generate_deployment_instructions(export_manager, temp_dir):
    """Test deployment instructions generation."""
    package_path = Path(temp_dir) / "test_package"
    package_path.mkdir()
    
    instructions = export_manager.generate_deployment_instructions(str(package_path))
    
    # Check instructions contain key information
    assert "Deployment Instructions" in instructions
    assert "Raspberry Pi" in instructions
    assert export_manager.config.CONVERSATIONAL_MODEL in instructions
    assert "scp" in instructions or "rsync" in instructions
    assert "tar -xzf" in instructions
    assert "uvicorn" in instructions
    assert "ENABLE_DOCUMENT_PROCESSING=false" in instructions


def test_manifest_contains_required_fields(export_manager, temp_dir):
    """Test manifest contains all required fields."""
    output_dir = Path(temp_dir) / "test_export"
    result = export_manager.create_export_package(output_dir=str(output_dir))
    
    assert result.success is True
    
    # Read manifest
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    # Check required top-level fields
    assert "version" in manifest
    assert "created_at" in manifest
    assert "export_type" in manifest
    assert "desktop_config" in manifest
    assert "pi_requirements" in manifest
    assert "statistics" in manifest
    assert "incremental" in manifest
    
    # Check desktop_config fields
    assert "embedding_model" in manifest["desktop_config"]
    assert "embedding_dimension" in manifest["desktop_config"]
    assert "vision_model" in manifest["desktop_config"]
    
    # Check pi_requirements fields
    assert "conversational_model" in manifest["pi_requirements"]
    assert "min_memory_gb" in manifest["pi_requirements"]
    assert "embedding_dimension" in manifest["pi_requirements"]
    
    # Check statistics fields
    assert "total_chunks" in manifest["statistics"]
    assert "total_documents" in manifest["statistics"]
    assert "total_embeddings" in manifest["statistics"]


def test_pi_config_template_generation(export_manager, temp_dir):
    """Test Pi configuration template is generated correctly."""
    output_dir = Path(temp_dir) / "test_export"
    result = export_manager.create_export_package(output_dir=str(output_dir))
    
    assert result.success is True
    
    # Read config template
    config_path = output_dir / "config_pi.py"
    with open(config_path, 'r') as f:
        config_content = f.read()
    
    # Check config contains required settings
    assert "ENABLE_DOCUMENT_PROCESSING = False" in config_content
    assert export_manager.config.CONVERSATIONAL_MODEL in config_content
    assert export_manager.config.EMBEDDING_MODEL in config_content
    assert "class Config:" in config_content


def test_export_statistics_accuracy(export_manager, temp_dir):
    """Test export statistics are accurate."""
    output_dir = Path(temp_dir) / "test_export"
    result = export_manager.create_export_package(output_dir=str(output_dir))
    
    assert result.success is True
    
    stats = result.statistics
    
    # Check statistics match mock data
    assert stats["total_chunks"] == 100  # From mock_vector_store
    assert stats["total_documents"] == 50  # From mock_db_manager
    assert stats["total_embeddings"] == 100  # Should equal total_chunks
    assert "vector_store_size_mb" in stats
    assert "database_size_mb" in stats


def test_archive_creation(export_manager, temp_dir):
    """Test compressed archive is created correctly."""
    output_dir = Path(temp_dir) / "test_export"
    result = export_manager.create_export_package(output_dir=str(output_dir))
    
    assert result.success is True
    assert result.archive_path
    
    archive_path = Path(result.archive_path)
    
    # Check archive exists and has .tar.gz extension
    assert archive_path.exists()
    assert archive_path.suffix == ".gz"
    assert archive_path.stem.endswith(".tar")
    
    # Check archive size is reasonable
    assert archive_path.stat().st_size > 0


def test_create_manifest_full_export(export_manager):
    """Test creating a manifest for a full export."""
    manifest = export_manager.create_manifest(incremental=False)
    
    # Check required top-level fields
    assert "version" in manifest
    assert "created_at" in manifest
    assert "export_type" in manifest
    assert manifest["export_type"] == "full"
    
    # Check desktop_config
    assert "desktop_config" in manifest
    desktop_config = manifest["desktop_config"]
    assert "embedding_model" in desktop_config
    assert "embedding_dimension" in desktop_config
    assert "vision_model" in desktop_config
    assert desktop_config["embedding_dimension"] == 384
    
    # Check pi_requirements
    assert "pi_requirements" in manifest
    pi_req = manifest["pi_requirements"]
    assert "conversational_model" in pi_req
    assert "min_memory_gb" in pi_req
    assert "embedding_dimension" in pi_req
    assert pi_req["embedding_dimension"] == 384
    assert pi_req["min_memory_gb"] == 4
    
    # Check statistics
    assert "statistics" in manifest
    stats = manifest["statistics"]
    assert "total_chunks" in stats
    assert "total_documents" in stats
    assert "total_embeddings" in stats
    
    # Check incremental metadata
    assert "incremental" in manifest
    incremental = manifest["incremental"]
    assert incremental["is_incremental"] is False
    assert incremental["base_version"] is None
    assert incremental["since_timestamp"] is None


def test_create_manifest_incremental_export(export_manager):
    """Test creating a manifest for an incremental export."""
    since_timestamp = datetime(2024, 1, 15, 10, 30, 0)
    manifest = export_manager.create_manifest(
        incremental=True,
        since_timestamp=since_timestamp
    )
    
    # Check export type
    assert manifest["export_type"] == "incremental"
    
    # Check incremental metadata
    incremental = manifest["incremental"]
    assert incremental["is_incremental"] is True
    assert incremental["since_timestamp"] == since_timestamp.isoformat()


def test_create_manifest_with_provided_statistics(export_manager):
    """Test creating a manifest with pre-provided statistics."""
    custom_stats = {
        "total_chunks": 200,
        "total_documents": 100,
        "total_embeddings": 200,
        "custom_field": "custom_value"
    }
    
    manifest = export_manager.create_manifest(statistics=custom_stats)
    
    # Check that provided statistics are used
    assert manifest["statistics"] == custom_stats
    assert manifest["statistics"]["total_chunks"] == 200
    assert manifest["statistics"]["custom_field"] == "custom_value"


def test_validate_manifest_valid(export_manager):
    """Test validating a valid manifest."""
    manifest = export_manager.create_manifest(incremental=False)
    
    validation = export_manager.validate_manifest(manifest)
    
    assert validation.valid is True
    assert len(validation.errors) == 0


def test_validate_manifest_missing_top_level_fields(export_manager):
    """Test validation fails when top-level fields are missing."""
    manifest = {
        "version": "1.0",
        "created_at": datetime.now().isoformat()
        # Missing: export_type, desktop_config, pi_requirements, statistics, incremental
    }
    
    validation = export_manager.validate_manifest(manifest)
    
    assert validation.valid is False
    assert len(validation.errors) >= 5  # At least 5 missing fields


def test_validate_manifest_missing_desktop_config_fields(export_manager):
    """Test validation fails when desktop_config fields are missing."""
    manifest = {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "export_type": "full",
        "desktop_config": {
            "embedding_model": "test-model"
            # Missing: embedding_dimension, vision_model
        },
        "pi_requirements": {
            "conversational_model": "qwen2.5:3b",
            "min_memory_gb": 4,
            "embedding_dimension": 384
        },
        "statistics": {},
        "incremental": {
            "is_incremental": False,
            "base_version": None,
            "since_timestamp": None
        }
    }
    
    validation = export_manager.validate_manifest(manifest)
    
    assert validation.valid is False
    assert any("desktop_config" in error for error in validation.errors)


def test_validate_manifest_missing_pi_requirements_fields(export_manager):
    """Test validation fails when pi_requirements fields are missing."""
    manifest = {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "export_type": "full",
        "desktop_config": {
            "embedding_model": "test-model",
            "embedding_dimension": 384,
            "vision_model": "qwen2.5vl:7b"
        },
        "pi_requirements": {
            "conversational_model": "qwen2.5:3b"
            # Missing: min_memory_gb, embedding_dimension
        },
        "statistics": {},
        "incremental": {
            "is_incremental": False,
            "base_version": None,
            "since_timestamp": None
        }
    }
    
    validation = export_manager.validate_manifest(manifest)
    
    assert validation.valid is False
    assert any("pi_requirements" in error for error in validation.errors)


def test_validate_manifest_invalid_embedding_dimension(export_manager):
    """Test validation fails when embedding_dimension is invalid."""
    manifest = {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "export_type": "full",
        "desktop_config": {
            "embedding_model": "test-model",
            "embedding_dimension": -1,  # Invalid: negative
            "vision_model": "qwen2.5vl:7b"
        },
        "pi_requirements": {
            "conversational_model": "qwen2.5:3b",
            "min_memory_gb": 4,
            "embedding_dimension": 384
        },
        "statistics": {},
        "incremental": {
            "is_incremental": False,
            "base_version": None,
            "since_timestamp": None
        }
    }
    
    validation = export_manager.validate_manifest(manifest)
    
    assert validation.valid is False
    assert any("embedding_dimension" in error and "desktop_config" in error 
               for error in validation.errors)


def test_validate_manifest_dimension_mismatch(export_manager):
    """Test validation fails when embedding dimensions don't match."""
    manifest = {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "export_type": "full",
        "desktop_config": {
            "embedding_model": "test-model",
            "embedding_dimension": 384,
            "vision_model": "qwen2.5vl:7b"
        },
        "pi_requirements": {
            "conversational_model": "qwen2.5:3b",
            "min_memory_gb": 4,
            "embedding_dimension": 768  # Mismatch!
        },
        "statistics": {},
        "incremental": {
            "is_incremental": False,
            "base_version": None,
            "since_timestamp": None
        }
    }
    
    validation = export_manager.validate_manifest(manifest)
    
    assert validation.valid is False
    assert any("mismatch" in error.lower() for error in validation.errors)


def test_validate_manifest_invalid_min_memory(export_manager):
    """Test validation fails when min_memory_gb is invalid."""
    manifest = {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "export_type": "full",
        "desktop_config": {
            "embedding_model": "test-model",
            "embedding_dimension": 384,
            "vision_model": "qwen2.5vl:7b"
        },
        "pi_requirements": {
            "conversational_model": "qwen2.5:3b",
            "min_memory_gb": -2,  # Invalid: negative
            "embedding_dimension": 384
        },
        "statistics": {},
        "incremental": {
            "is_incremental": False,
            "base_version": None,
            "since_timestamp": None
        }
    }
    
    validation = export_manager.validate_manifest(manifest)
    
    assert validation.valid is False
    assert any("min_memory_gb" in error for error in validation.errors)


def test_validate_manifest_missing_statistics_fields(export_manager):
    """Test validation warns when statistics fields are missing."""
    manifest = {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "export_type": "full",
        "desktop_config": {
            "embedding_model": "test-model",
            "embedding_dimension": 384,
            "vision_model": "qwen2.5vl:7b"
        },
        "pi_requirements": {
            "conversational_model": "qwen2.5:3b",
            "min_memory_gb": 4,
            "embedding_dimension": 384
        },
        "statistics": {},  # Empty statistics
        "incremental": {
            "is_incremental": False,
            "base_version": None,
            "since_timestamp": None
        }
    }
    
    validation = export_manager.validate_manifest(manifest)
    
    # Should pass validation but have warnings
    assert validation.valid is True
    assert len(validation.warnings) > 0
    assert any("statistics" in warning for warning in validation.warnings)


def test_validate_manifest_empty_data_warnings(export_manager):
    """Test validation warns when data counts are zero."""
    manifest = {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "export_type": "full",
        "desktop_config": {
            "embedding_model": "test-model",
            "embedding_dimension": 384,
            "vision_model": "qwen2.5vl:7b"
        },
        "pi_requirements": {
            "conversational_model": "qwen2.5:3b",
            "min_memory_gb": 4,
            "embedding_dimension": 384
        },
        "statistics": {
            "total_chunks": 0,
            "total_documents": 0,
            "total_embeddings": 0
        },
        "incremental": {
            "is_incremental": False,
            "base_version": None,
            "since_timestamp": None
        }
    }
    
    validation = export_manager.validate_manifest(manifest)
    
    # Should pass validation but have warnings
    assert validation.valid is True
    assert len(validation.warnings) >= 2  # Warnings for no chunks and no documents


def test_validate_manifest_export_type_mismatch_warning(export_manager):
    """Test validation warns when export_type doesn't match is_incremental."""
    manifest = {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "export_type": "full",  # Says full
        "desktop_config": {
            "embedding_model": "test-model",
            "embedding_dimension": 384,
            "vision_model": "qwen2.5vl:7b"
        },
        "pi_requirements": {
            "conversational_model": "qwen2.5:3b",
            "min_memory_gb": 4,
            "embedding_dimension": 384
        },
        "statistics": {
            "total_chunks": 100,
            "total_documents": 50,
            "total_embeddings": 100
        },
        "incremental": {
            "is_incremental": True,  # But says incremental
            "base_version": None,
            "since_timestamp": None
        }
    }
    
    validation = export_manager.validate_manifest(manifest)
    
    # Should pass validation but have warning
    assert validation.valid is True
    assert len(validation.warnings) > 0
    assert any("export_type" in warning for warning in validation.warnings)


def test_validate_manifest_incremental_without_timestamp_warning(export_manager):
    """Test validation warns when incremental export lacks since_timestamp."""
    manifest = {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "export_type": "incremental",
        "desktop_config": {
            "embedding_model": "test-model",
            "embedding_dimension": 384,
            "vision_model": "qwen2.5vl:7b"
        },
        "pi_requirements": {
            "conversational_model": "qwen2.5:3b",
            "min_memory_gb": 4,
            "embedding_dimension": 384
        },
        "statistics": {
            "total_chunks": 100,
            "total_documents": 50,
            "total_embeddings": 100
        },
        "incremental": {
            "is_incremental": True,
            "base_version": None,
            "since_timestamp": None  # Missing timestamp for incremental
        }
    }
    
    validation = export_manager.validate_manifest(manifest)
    
    # Should pass validation but have warning
    assert validation.valid is True
    assert len(validation.warnings) > 0
    assert any("since_timestamp" in warning for warning in validation.warnings)
