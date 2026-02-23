"""
Ollama client wrapper for vision model integration.

Provides health checks, model availability checks, and image generation
with retry logic and timeout handling.
"""

import time
import base64
import platform
import requests
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from backend.config import Config

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(
        self,
        endpoint: str = None,
        model: str = None,
        timeout: Optional[int] = None
    ):
        """
        Initialize Ollama client.
        
        Args:
            endpoint: Ollama API endpoint (defaults to Config.OLLAMA_ENDPOINT)
            model: Model name (defaults to Config.OLLAMA_MODEL)
            timeout: Request timeout in seconds (auto-detected if None)
        """
        self.endpoint = endpoint or Config.OLLAMA_ENDPOINT
        self.model = model or Config.OLLAMA_MODEL
        self.timeout = timeout or self._detect_timeout()
        
    def _detect_timeout(self) -> int:
        """
        Detect appropriate timeout based on hardware and model type.
        
        Vision models need longer timeouts than text models due to:
        - Image preprocessing (resizing, format conversion)
        - Larger model size (7B vision vs 3B text)
        - More complex inference (image + text understanding)
        
        Returns:
            Timeout in seconds (120s for vision models, 60s for text models)
        """
        # Check if this is a vision model
        is_vision_model = 'vl' in self.model.lower() or 'vision' in self.model.lower()
        
        if is_vision_model:
            # Vision models need more time
            return 120
        else:
            # Text/embedding models are faster
            return 60
    
    def health_check(self) -> bool:
        """
        Check if Ollama is running and accessible.
        
        Returns:
            True if Ollama is running, False otherwise
        """
        try:
            response = requests.get(
                f"{self.endpoint}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def is_model_available(self) -> bool:
        """
        Check if the specified model is available.
        
        Returns:
            True if model is available, False otherwise
        """
        try:
            response = requests.get(
                f"{self.endpoint}/api/tags",
                timeout=5
            )
            if response.status_code != 200:
                return False
            
            data = response.json()
            models = data.get("models", [])
            
            # Check if our model is in the list
            for model in models:
                if model.get("name") == self.model:
                    return True
            
            return False
        except requests.exceptions.RequestException:
            return False
    
    def verify_model_integrity(self) -> bool:
        """
        Verify model integrity by running a simple test generation.
        
        Returns:
            True if model works correctly, False if corrupted
        """
        try:
            # Simple test prompt (no images for faster check)
            test_payload = {
                "model": self.model,
                "prompt": "test",
                "stream": False
            }
            
            response = requests.post(
                f"{self.endpoint}/api/generate",
                json=test_payload,
                timeout=30
            )
            
            # Check for GGML assertion errors
            if response.status_code == 500 and "GGML_ASSERT" in response.text:
                logger.warning(f"Model {self.model} failed integrity check: GGML assertion error")
                return False
            
            # Model is working
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Model integrity check failed: {str(e)}")
            return False
    
    def generate(
        self,
        prompt: str,
        images: list[str] = None,
        stream: bool = False,
        keep_alive: str = None,
        format: str = None,
        options: dict = None  # Allow custom options override
    ) -> Dict[str, Any]:
        """
        Generate response from Ollama model with retry logic.
        
        Args:
            prompt: Text prompt for the model
            images: List of base64-encoded images
            stream: Whether to stream the response
            keep_alive: How long to keep model in memory (e.g., "30m", "1h")
            format: Output format ("json" for structured data, None for natural language)
            
        Returns:
            Response dictionary with 'response' and 'done' keys.
            Note: Some models (like qwen3-vl) return content in 'thinking' field
            instead of 'response' field. This method normalizes the response
            by copying 'thinking' to 'response' if 'response' is empty.
            
        Raises:
            OllamaError: If generation fails after retries
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "keep_alive": keep_alive or Config.OLLAMA_KEEP_ALIVE,
            "options": options or {
                "num_ctx": 1536,  # Balanced: not too large (2048) but enough context for accuracy
                "num_predict": 256,  # Keep short responses for speed
                "temperature": 0.1 if format == "json" else 0.7,  # Low temp for JSON, higher for natural language
            }
        }
        
        # Only add format parameter if explicitly requested (for vision model JSON extraction)
        if format:
            payload["format"] = format
        
        if images:
            payload["images"] = images
        
        # Retry logic with exponential backoff
        max_retries = 3
        backoff_delays = [1, 2, 4]  # seconds
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.endpoint}/api/generate",
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Handle models that return content in 'thinking' field (e.g., qwen3-vl)
                    # If 'response' is empty but 'thinking' has content, use 'thinking'
                    if not result.get('response') and result.get('thinking'):
                        logger.debug(f"Model {self.model} returned content in 'thinking' field, normalizing to 'response'")
                        result['response'] = result['thinking']
                    
                    return result
                else:
                    last_error = OllamaError(
                        f"Ollama API returned status {response.status_code}: {response.text}"
                    )
                    
            except requests.exceptions.Timeout:
                last_error = OllamaError(
                    f"Request timed out after {self.timeout} seconds"
                )
            except requests.exceptions.RequestException as e:
                last_error = OllamaError(f"Request failed: {str(e)}")
            
            # Wait before retry (except on last attempt)
            if attempt < max_retries - 1:
                time.sleep(backoff_delays[attempt])
        
        # All retries failed
        raise last_error


class OllamaError(Exception):
    """Exception raised for Ollama API errors."""
    pass


def encode_image_to_base64(image_path: str) -> str:
    """
    Encode image file to base64 string.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Base64-encoded image string
        
    Raises:
        FileNotFoundError: If image file doesn't exist
        IOError: If image cannot be read
    """
    path = Path(image_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    if not path.is_file():
        raise IOError(f"Path is not a file: {image_path}")
    
    try:
        with open(path, "rb") as image_file:
            image_data = image_file.read()
            return base64.b64encode(image_data).decode("utf-8")
    except Exception as e:
        raise IOError(f"Failed to read image file: {str(e)}")
