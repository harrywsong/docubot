"""Configuration management for RAG chatbot with vision processing."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration."""
    
    # Ollama configuration
    OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")  # Better reading comprehension for multilingual RAG
    OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "qwen3-vl:8b")  # Vision model for images
    OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")  # Keep models in memory for 30 minutes
    
    # Groq API configuration (optional - disabled by default for privacy)
    USE_GROQ = os.getenv("USE_GROQ", "false").lower() == "true"
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")

    
    # ChromaDB configuration
    CHROMADB_PATH = os.getenv("CHROMADB_PATH", str(Path("data/chromadb").absolute()))
    
    # SQLite configuration
    SQLITE_PATH = os.getenv("SQLITE_PATH", str(Path("data/app.db").absolute()))
    
    # Data directory
    DATA_DIR = Path("data")
    
    # Deployment mode: Set to False on Raspberry Pi to disable document processing
    ENABLE_DOCUMENT_PROCESSING = os.getenv("ENABLE_DOCUMENT_PROCESSING", "true").lower() == "true"
    
    # Model configuration for split-architecture deployment
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "qwen3-embedding:8b")  # Multilingual embeddings (Korean + English)
    CONVERSATIONAL_MODEL = os.getenv("CONVERSATIONAL_MODEL", "qwen2.5:7b")  # Better reading comprehension for Pi deployment
    
    # Export/Import paths for Pi deployment
    EXPORT_DIR = os.getenv("EXPORT_DIR", "pi_export")
    MANIFEST_PATH = os.getenv("MANIFEST_PATH", "data/manifest.json")
    
    @classmethod
    def ensure_data_directories(cls):
        """Create data directories if they don't exist."""
        cls.DATA_DIR.mkdir(exist_ok=True)
        Path(cls.CHROMADB_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(cls.SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """
        Validate model configuration consistency.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check that required models are specified
        if not cls.EMBEDDING_MODEL:
            errors.append("EMBEDDING_MODEL must be specified")
        
        if not cls.CONVERSATIONAL_MODEL:
            errors.append("CONVERSATIONAL_MODEL must be specified")
        
        # Check that paths are valid
        if not cls.CHROMADB_PATH:
            errors.append("CHROMADB_PATH must be specified")
        
        if not cls.SQLITE_PATH:
            errors.append("SQLITE_PATH must be specified")
        
        # Check deployment mode consistency
        if not cls.ENABLE_DOCUMENT_PROCESSING:
            # Pi mode - should use conversational model
            if cls.OLLAMA_MODEL == cls.EMBEDDING_MODEL:
                errors.append(
                    f"Pi mode (ENABLE_DOCUMENT_PROCESSING=False) should use CONVERSATIONAL_MODEL, "
                    f"but OLLAMA_MODEL is set to embedding model: {cls.OLLAMA_MODEL}"
                )
        else:
            # Desktop mode - can use either model depending on operation
            pass
        
        # Check export directory exists if in desktop mode
        if cls.ENABLE_DOCUMENT_PROCESSING:
            export_path = Path(cls.EXPORT_DIR)
            if not export_path.exists():
                # This is just a warning, not an error - directory will be created on export
                pass
        
        return (len(errors) == 0, errors)
