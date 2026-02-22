"""
Groq API client for fast cloud-based LLM responses.

Provides a free, fast alternative to local Ollama models for conversational responses.
"""

import requests
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class GroqClient:
    """Client for interacting with Groq API."""
    
    def __init__(self, api_key: str, model: str = "llama-3.1-70b-versatile"):
        """
        Initialize Groq client.
        
        Args:
            api_key: Groq API key from https://console.groq.com/
            model: Model name (default: llama-3.1-70b-versatile)
        """
        self.api_key = api_key
        self.model = model
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"
        
        if not api_key:
            raise ValueError("Groq API key is required. Get one from https://console.groq.com/")
        
        logger.info(f"GroqClient initialized with model: {model}")
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """
        Generate response from Groq API.
        
        Args:
            prompt: Text prompt for the model
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Response dictionary with 'response' and 'done' keys (compatible with Ollama format)
            
        Raises:
            GroqError: If generation fails
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Convert Groq format to Ollama-compatible format
                content = result["choices"][0]["message"]["content"]
                
                return {
                    "response": content,
                    "done": True,
                    "model": self.model,
                    "usage": result.get("usage", {})
                }
            else:
                error_msg = f"Groq API returned status {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise GroqError(error_msg)
                
        except requests.exceptions.Timeout:
            raise GroqError("Request timed out after 30 seconds")
        except requests.exceptions.RequestException as e:
            raise GroqError(f"Request failed: {str(e)}")


class GroqError(Exception):
    """Exception raised for Groq API errors."""
    pass
