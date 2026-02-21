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
        assert "ollama_available" in data
        assert "model_available" in data
        assert "database_available" in data
        assert "vector_store_available" in data
        assert "errors" in data
        assert "warnings" in data
        
        # Database and vector store should be available in tests
        assert data["database_available"] is True
        assert data["vector_store_available"] is True


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
