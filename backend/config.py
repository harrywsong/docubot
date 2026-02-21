"""Configuration management for RAG chatbot with vision processing."""

import os
from pathlib import Path


class Config:
    """Application configuration."""
    
    # Ollama configuration
    OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-vl:7b")
    
    # ChromaDB configuration
    CHROMADB_PATH = os.getenv("CHROMADB_PATH", str(Path("data/chromadb").absolute()))
    
    # SQLite configuration
    SQLITE_PATH = os.getenv("SQLITE_PATH", str(Path("data/app.db").absolute()))
    
    # Data directory
    DATA_DIR = Path("data")
    
    @classmethod
    def ensure_data_directories(cls):
        """Create data directories if they don't exist."""
        cls.DATA_DIR.mkdir(exist_ok=True)
        Path(cls.CHROMADB_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(cls.SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
