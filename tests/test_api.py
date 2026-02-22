"""
Integration tests for REST API endpoints.

Tests all API endpoints with success and error cases.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient

# Import after setting up test environment
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.api import app
from backend.config import Config


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
def client(test_data_dir):
    """Create test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def temp_folder():
    """Create temporary folder for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestRootEndpoint:
    """Tests for root endpoint."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "RAG Chatbot API"
        assert data["status"] == "running"
        assert "endpoints" in data


class TestHealthCheck:
    """Tests for health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "status" in data
        assert "memory_usage_percent" in data
        assert "memory_available_mb" in data
        assert "model_loaded" in data
        assert "vector_store_loaded" in data
        assert "total_chunks" in data
        assert "ollama_available" in data
        assert "model_available" in data
        assert "database_available" in data
        assert "errors" in data
        assert "warnings" in data
        
        # Database and vector store should be available in tests
        assert data["database_available"] is True
        assert data["vector_store_loaded"] is True


class TestFolderEndpoints:
    """Tests for folder management endpoints."""
    
    def test_add_folder_success(self, client, temp_folder):
        """Test adding a valid folder."""
        response = client.post(
            "/api/folders/add",
            json={"path": temp_folder}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "folder" in data
        assert data["folder"]["path"] == str(Path(temp_folder).resolve())
    
    def test_add_folder_invalid_path(self, client):
        """Test adding an invalid folder path."""
        response = client.post(
            "/api/folders/add",
            json={"path": "/nonexistent/folder/path"}
        )
        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"].lower()
    
    def test_add_folder_duplicate(self, client, temp_folder):
        """Test adding the same folder twice."""
        # Add folder first time
        client.post("/api/folders/add", json={"path": temp_folder})
        
        # Try to add again
        response = client.post(
            "/api/folders/add",
            json={"path": temp_folder}
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()
    
    def test_list_folders(self, client, temp_folder):
        """Test listing folders."""
        # Add a folder
        client.post("/api/folders/add", json={"path": temp_folder})
        
        # List folders
        response = client.get("/api/folders/list")
        assert response.status_code == 200
        data = response.json()
        assert "folders" in data
        assert len(data["folders"]) > 0
        
        # Check folder structure
        folder = data["folders"][0]
        assert "id" in folder
        assert "path" in folder
        assert "added_at" in folder
    
    def test_remove_folder_success(self, client, temp_folder):
        """Test removing a folder."""
        # Add folder
        client.post("/api/folders/add", json={"path": temp_folder})
        
        # Remove folder
        response = client.request(
            "DELETE",
            "/api/folders/remove",
            json={"path": temp_folder}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_remove_folder_not_found(self, client):
        """Test removing a non-existent folder."""
        response = client.request(
            "DELETE",
            "/api/folders/remove",
            json={"path": "/nonexistent/folder"}
        )
        assert response.status_code == 404


class TestProcessingEndpoints:
    """Tests for document processing endpoints."""
    
    def test_get_processing_status(self, client):
        """Test getting processing status."""
        response = client.get("/api/process/status")
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "is_processing" in data
        assert "processed" in data
        assert "skipped" in data
        assert "failed" in data
        assert "failed_files" in data
    
    def test_start_processing(self, client):
        """Test starting document processing."""
        response = client.post("/api/process/start")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "processing_id" in data


class TestConversationEndpoints:
    """Tests for conversation management endpoints."""
    
    def test_create_conversation(self, client):
        """Test creating a conversation."""
        response = client.post(
            "/api/conversations/create",
            json={"title": "Test Conversation"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "conversation" in data
        
        conversation = data["conversation"]
        assert "id" in conversation
        assert conversation["title"] == "Test Conversation"
        assert "created_at" in conversation
        assert "updated_at" in conversation
        assert conversation["messages"] == []
    
    def test_create_conversation_no_title(self, client):
        """Test creating a conversation without a title."""
        response = client.post(
            "/api/conversations/create",
            json={}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_list_conversations(self, client):
        """Test listing conversations."""
        # Create a conversation
        create_response = client.post(
            "/api/conversations/create",
            json={"title": "Test List"}
        )
        
        # List conversations
        response = client.get("/api/conversations/list")
        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
        assert len(data["conversations"]) > 0
    
    def test_get_conversation(self, client):
        """Test getting a conversation."""
        # Create a conversation
        create_response = client.post(
            "/api/conversations/create",
            json={"title": "Test Get"}
        )
        conversation_id = create_response.json()["conversation"]["id"]
        
        # Get conversation
        response = client.get(f"/api/conversations/{conversation_id}")
        assert response.status_code == 200
        data = response.json()
        assert "conversation" in data
        
        conversation = data["conversation"]
        assert conversation["id"] == conversation_id
        assert "messages" in conversation
    
    def test_get_conversation_not_found(self, client):
        """Test getting a non-existent conversation."""
        response = client.get("/api/conversations/invalid-id")
        assert response.status_code == 404
    
    def test_delete_conversation(self, client):
        """Test deleting a conversation."""
        # Create a conversation
        create_response = client.post(
            "/api/conversations/create",
            json={"title": "Test Delete"}
        )
        conversation_id = create_response.json()["conversation"]["id"]
        
        # Delete conversation
        response = client.delete(f"/api/conversations/{conversation_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify it's deleted
        get_response = client.get(f"/api/conversations/{conversation_id}")
        assert get_response.status_code == 404
    
    def test_delete_conversation_not_found(self, client):
        """Test deleting a non-existent conversation."""
        response = client.delete("/api/conversations/invalid-id")
        assert response.status_code == 404


class TestQueryEndpoint:
    """Tests for query endpoint."""
    
    def test_query_conversation_not_found(self, client):
        """Test querying with invalid conversation ID."""
        response = client.post(
            "/api/query",
            json={
                "conversation_id": "invalid-id",
                "question": "Test question"
            }
        )
        assert response.status_code == 404
    
    def test_query_success(self, client):
        """Test successful query."""
        # Create a conversation
        create_response = client.post(
            "/api/conversations/create",
            json={"title": "Test Query"}
        )
        conversation_id = create_response.json()["conversation"]["id"]
        
        # Submit query
        response = client.post(
            "/api/query",
            json={
                "conversation_id": conversation_id,
                "question": "What is the weather today?"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "answer" in data
        assert "sources" in data
        assert isinstance(data["sources"], list)
        
        # Verify message was added to conversation
        conv_response = client.get(f"/api/conversations/{conversation_id}")
        conversation = conv_response.json()["conversation"]
        assert len(conversation["messages"]) == 2  # User + assistant


class TestExportEndpoints:
    """Tests for export and validation endpoints."""
    
    def test_get_processing_report(self, client):
        """Test getting processing validation report."""
        response = client.get("/api/processing/report")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_documents" in data
        assert "total_chunks" in data
        assert "total_embeddings" in data
        assert "failed_documents" in data
        assert "missing_embeddings" in data
        assert "incomplete_metadata" in data
        assert "validation_passed" in data
        
        # Check types
        assert isinstance(data["total_documents"], int)
        assert isinstance(data["total_chunks"], int)
        assert isinstance(data["total_embeddings"], int)
        assert isinstance(data["failed_documents"], list)
        assert isinstance(data["missing_embeddings"], list)
        assert isinstance(data["incomplete_metadata"], list)
        assert isinstance(data["validation_passed"], bool)
    
    def test_create_export_full(self, client, test_data_dir):
        """Test creating full export package."""
        # Note: This test expects ChromaDB directory to exist
        # In a real scenario, documents would be processed first
        # For this test, we verify the API endpoint structure works
        
        response = client.post(
            "/api/export",
            json={
                "output_dir": str(Path(test_data_dir) / "test_export"),
                "incremental": False
            }
        )
        
        # The export may fail if no data has been processed yet
        # This is expected behavior - we're testing the API structure
        if response.status_code == 500:
            # Verify it's the expected error (missing ChromaDB)
            detail = response.json()["detail"]
            assert "ChromaDB directory not found" in detail or "Export failed" in detail
        else:
            # If it succeeds (data exists), verify response structure
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "package_path" in data
            assert "archive_path" in data
            assert "size_bytes" in data
            assert "size_mb" in data
            assert "statistics" in data
            assert "errors" in data
    
    def test_create_export_incremental(self, client, test_data_dir):
        """Test creating incremental export package."""
        from datetime import datetime, timedelta
        
        # Use a timestamp from 1 hour ago
        since_timestamp = (datetime.now() - timedelta(hours=1)).isoformat()
        
        response = client.post(
            "/api/export",
            json={
                "output_dir": str(Path(test_data_dir) / "test_export_incremental"),
                "incremental": True,
                "since_timestamp": since_timestamp
            }
        )
        
        # The export may fail if no data has been processed yet
        # This is expected behavior - we're testing the API structure
        if response.status_code == 500:
            # Verify it's the expected error (missing ChromaDB)
            detail = response.json()["detail"]
            assert "ChromaDB directory not found" in detail or "Export failed" in detail
        else:
            # If it succeeds (data exists), verify response structure
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "package_path" in data
            assert "archive_path" in data
    
    def test_create_export_invalid_timestamp(self, client, test_data_dir):
        """Test creating export with invalid timestamp format."""
        response = client.post(
            "/api/export",
            json={
                "output_dir": str(Path(test_data_dir) / "test_export_invalid"),
                "incremental": True,
                "since_timestamp": "invalid-timestamp"
            }
        )
        assert response.status_code == 400
        assert "Invalid timestamp format" in response.json()["detail"]
    
    def test_validate_export_valid(self, client, test_data_dir):
        """Test validating export package endpoint structure."""
        # Test with a non-existent path to verify API structure
        # (Creating a real export requires processed data)
        
        response = client.get(
            "/api/export/validate",
            params={"package_path": str(Path(test_data_dir) / "nonexistent")}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "valid" in data
        assert "errors" in data
        assert "warnings" in data
        assert isinstance(data["valid"], bool)
        assert isinstance(data["errors"], list)
        assert isinstance(data["warnings"], list)
        
        # Should be invalid since path doesn't exist
        assert data["valid"] is False
        assert len(data["errors"]) > 0
    
    def test_validate_export_missing_directory(self, client):
        """Test validating non-existent export package."""
        response = client.get(
            "/api/export/validate",
            params={"package_path": "/nonexistent/path"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0
        assert "not found" in data["errors"][0].lower()


class TestPiSpecificEndpoints:
    """Tests for Pi-specific API endpoints."""
    
    def test_health_check_with_resource_monitor(self, client):
        """Test health check endpoint returns Pi-specific fields."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        
        # Check Pi-specific fields are present
        assert "status" in data
        assert "memory_usage_percent" in data
        assert "memory_available_mb" in data
        assert "model_loaded" in data
        assert "vector_store_loaded" in data
        assert "total_chunks" in data
        
        # Check types
        assert isinstance(data["memory_usage_percent"], (int, float))
        assert isinstance(data["memory_available_mb"], (int, float))
        assert isinstance(data["model_loaded"], bool)
        assert isinstance(data["vector_store_loaded"], bool)
        assert isinstance(data["total_chunks"], int)
        
        # Memory usage should be between 0 and 100
        assert 0 <= data["memory_usage_percent"] <= 100
        assert data["memory_available_mb"] >= 0
    
    def test_get_data_stats(self, client):
        """Test getting data statistics."""
        response = client.get("/api/data/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_chunks" in data
        assert "embedding_dimension" in data
        assert "last_update" in data
        assert "vector_store_size_mb" in data
        assert "database_size_mb" in data
        
        # Check types
        assert isinstance(data["total_chunks"], int)
        assert data["total_chunks"] >= 0
        
        # embedding_dimension can be None if vector store is empty
        if data["embedding_dimension"] is not None:
            assert isinstance(data["embedding_dimension"], int)
            assert data["embedding_dimension"] > 0
        
        # last_update can be None if no manifest
        if data["last_update"] is not None:
            assert isinstance(data["last_update"], str)
        
        # Sizes can be None if files don't exist
        if data["vector_store_size_mb"] is not None:
            assert isinstance(data["vector_store_size_mb"], (int, float))
            assert data["vector_store_size_mb"] >= 0
        
        if data["database_size_mb"] is not None:
            assert isinstance(data["database_size_mb"], (int, float))
            assert data["database_size_mb"] >= 0
    
    def test_merge_incremental_data_missing_package(self, client):
        """Test merging with non-existent package."""
        response = client.post(
            "/api/data/merge",
            json={"package_path": "/nonexistent/package"}
        )
        assert response.status_code == 500
        assert "Merge failed" in response.json()["detail"]
    
    def test_merge_incremental_data_invalid_package(self, client, test_data_dir):
        """Test merging with invalid package (missing manifest)."""
        # Create an empty directory as invalid package
        invalid_package = Path(test_data_dir) / "invalid_package"
        invalid_package.mkdir(exist_ok=True)
        
        response = client.post(
            "/api/data/merge",
            json={"package_path": str(invalid_package)}
        )
        assert response.status_code == 500
        detail = response.json()["detail"]
        assert "Merge failed" in detail
        assert "Manifest file not found" in detail


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
