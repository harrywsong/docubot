"""
Unit tests for Ollama client module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from backend.ollama_client import OllamaClient, OllamaError, encode_image_to_base64
import tempfile
import os


class TestOllamaClient:
    """Test Ollama client functionality."""
    
    def test_init_default_config(self):
        """Test client initialization with default config."""
        client = OllamaClient()
        assert client.endpoint == "http://localhost:11434"
        assert client.model == "qwen2.5-vl:7b"
        assert client.timeout in [5, 10]  # Depends on platform
    
    def test_init_custom_config(self):
        """Test client initialization with custom config."""
        client = OllamaClient(
            endpoint="http://custom:8080",
            model="custom-model",
            timeout=15
        )
        assert client.endpoint == "http://custom:8080"
        assert client.model == "custom-model"
        assert client.timeout == 15
    
    @patch('platform.system')
    @patch('platform.machine')
    def test_detect_timeout_apple_silicon(self, mock_machine, mock_system):
        """Test timeout detection for Apple Silicon."""
        mock_system.return_value = "Darwin"
        mock_machine.return_value = "arm64"
        
        client = OllamaClient()
        assert client.timeout == 10
    
    @patch('platform.system')
    @patch('platform.machine')
    def test_detect_timeout_cuda(self, mock_machine, mock_system):
        """Test timeout detection for CUDA systems."""
        mock_system.return_value = "Windows"
        mock_machine.return_value = "x86_64"
        
        client = OllamaClient()
        assert client.timeout == 5
    
    @patch('requests.get')
    def test_health_check_success(self, mock_get):
        """Test successful health check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        client = OllamaClient()
        assert client.health_check() is True
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_health_check_failure(self, mock_get):
        """Test failed health check."""
        mock_get.side_effect = requests.exceptions.ConnectionError()
        
        client = OllamaClient()
        assert client.health_check() is False
    
    @patch('requests.get')
    def test_is_model_available_success(self, mock_get):
        """Test model availability check when model exists."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "qwen2.5-vl:7b"},
                {"name": "other-model"}
            ]
        }
        mock_get.return_value = mock_response
        
        client = OllamaClient()
        assert client.is_model_available() is True
    
    @patch('requests.get')
    def test_is_model_available_not_found(self, mock_get):
        """Test model availability check when model doesn't exist."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "other-model"}
            ]
        }
        mock_get.return_value = mock_response
        
        client = OllamaClient()
        assert client.is_model_available() is False
    
    @patch('requests.get')
    def test_is_model_available_connection_error(self, mock_get):
        """Test model availability check with connection error."""
        mock_get.side_effect = requests.exceptions.ConnectionError()
        
        client = OllamaClient()
        assert client.is_model_available() is False
    
    @patch('requests.post')
    def test_generate_success(self, mock_post):
        """Test successful generation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Generated text",
            "done": True
        }
        mock_post.return_value = mock_response
        
        client = OllamaClient()
        result = client.generate("Test prompt")
        
        assert result["response"] == "Generated text"
        assert result["done"] is True
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_generate_with_images(self, mock_post):
        """Test generation with images."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Image description",
            "done": True
        }
        mock_post.return_value = mock_response
        
        client = OllamaClient()
        result = client.generate(
            "Describe this image",
            images=["base64_image_data"]
        )
        
        assert result["response"] == "Image description"
        # Verify images were included in request
        call_args = mock_post.call_args
        assert "images" in call_args[1]["json"]
    
    @patch('requests.post')
    @patch('time.sleep')
    def test_generate_retry_on_timeout(self, mock_sleep, mock_post):
        """Test retry logic on timeout."""
        # First two attempts timeout, third succeeds
        mock_post.side_effect = [
            requests.exceptions.Timeout(),
            requests.exceptions.Timeout(),
            Mock(status_code=200, json=lambda: {"response": "Success", "done": True})
        ]
        
        client = OllamaClient()
        result = client.generate("Test prompt")
        
        assert result["response"] == "Success"
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep between retries
    
    @patch('requests.post')
    @patch('time.sleep')
    def test_generate_max_retries_exceeded(self, mock_sleep, mock_post):
        """Test that max retries are respected."""
        mock_post.side_effect = requests.exceptions.Timeout()
        
        client = OllamaClient()
        with pytest.raises(OllamaError) as exc_info:
            client.generate("Test prompt")
        
        assert "timed out" in str(exc_info.value).lower()
        assert mock_post.call_count == 3  # Max retries
    
    @patch('requests.post')
    def test_generate_api_error(self, mock_post):
        """Test handling of API errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_post.return_value = mock_response
        
        client = OllamaClient()
        with pytest.raises(OllamaError) as exc_info:
            client.generate("Test prompt")
        
        assert "500" in str(exc_info.value)


class TestImageEncoding:
    """Test image encoding functionality."""
    
    def test_encode_image_to_base64_success(self):
        """Test successful image encoding."""
        # Create a temporary image file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.jpg') as f:
            f.write(b'\xff\xd8\xff\xe0')  # JPEG header
            temp_path = f.name
        
        try:
            encoded = encode_image_to_base64(temp_path)
            assert isinstance(encoded, str)
            assert len(encoded) > 0
            # Base64 encoded data should be valid
            import base64
            decoded = base64.b64decode(encoded)
            assert decoded == b'\xff\xd8\xff\xe0'
        finally:
            os.unlink(temp_path)
    
    def test_encode_image_file_not_found(self):
        """Test encoding with non-existent file."""
        with pytest.raises(FileNotFoundError):
            encode_image_to_base64("/nonexistent/path/image.jpg")
    
    def test_encode_image_not_a_file(self):
        """Test encoding with directory path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(IOError):
                encode_image_to_base64(temp_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
