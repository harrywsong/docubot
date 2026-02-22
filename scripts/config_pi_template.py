"""
Raspberry Pi Configuration Template for Desktop-Pi RAG Pipeline

This configuration file is designed for deployment on Raspberry Pi hardware.
It disables document processing and uses a lightweight conversational model
optimized for resource-constrained environments.

DEPLOYMENT INSTRUCTIONS:
1. Copy this file to your Pi as 'config_pi.py' or rename to 'config.py'
2. Update the paths and settings below to match your Pi environment
3. Ensure the Ollama service is running with the qwen2.5:3b model installed
4. Load the exported data package into the data/ directory
5. Start the server with: python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000

IMPORTANT: This configuration assumes you have already:
- Transferred the export package from your desktop
- Extracted the ChromaDB and SQLite database to the data/ directory
- Installed Ollama and pulled the qwen2.5:3b model
"""

import os
from pathlib import Path


class Config:
    """Raspberry Pi application configuration."""
    
    # ============================================================================
    # DEPLOYMENT MODE - CRITICAL SETTING
    # ============================================================================
    # Set to False on Raspberry Pi to disable document processing
    # Document processing (embedding generation, vision processing) happens on desktop only
    ENABLE_DOCUMENT_PROCESSING = False
    
    # ============================================================================
    # OLLAMA CONFIGURATION
    # ============================================================================
    # Ollama endpoint - typically localhost on Pi
    OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
    
    # Ollama model for conversational responses
    # qwen2.5:3b is recommended for Raspberry Pi (low memory footprint)
    # Alternative: qwen2.5:1.5b for even lower memory usage (4GB Pi models)
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    
    # ============================================================================
    # MODEL CONFIGURATION
    # ============================================================================
    # Embedding model name (for reference only - embeddings are pre-computed on desktop)
    # This should match the model used on desktop for compatibility validation
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
    
    # Conversational model for response generation on Pi
    # Must match OLLAMA_MODEL above
    CONVERSATIONAL_MODEL = os.getenv("CONVERSATIONAL_MODEL", "qwen2.5:3b")
    
    # ============================================================================
    # DATA PATHS
    # ============================================================================
    # ChromaDB vector store path (read-only on Pi)
    # This directory should contain the exported ChromaDB data from desktop
    CHROMADB_PATH = os.getenv("CHROMADB_PATH", str(Path("data/chromadb").absolute()))
    
    # SQLite database path (read-only on Pi)
    # This file should be the exported app.db from desktop
    SQLITE_PATH = os.getenv("SQLITE_PATH", str(Path("data/app.db").absolute()))
    
    # Data directory root
    DATA_DIR = Path("data")
    
    # Manifest file path (contains model compatibility information)
    MANIFEST_PATH = os.getenv("MANIFEST_PATH", "data/manifest.json")
    
    # ============================================================================
    # EXPORT/IMPORT CONFIGURATION
    # ============================================================================
    # Export directory (not used on Pi, but kept for compatibility)
    EXPORT_DIR = os.getenv("EXPORT_DIR", "pi_export")
    
    # ============================================================================
    # PERFORMANCE TUNING FOR RASPBERRY PI
    # ============================================================================
    # Query retrieval settings
    TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "5"))  # Number of chunks to retrieve
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.5"))  # Minimum similarity score
    
    # Timeout settings (in seconds)
    QUERY_TIMEOUT = int(os.getenv("QUERY_TIMEOUT", "2"))  # Retrieval timeout
    RESPONSE_TIMEOUT = int(os.getenv("RESPONSE_TIMEOUT", "10"))  # Response generation timeout
    
    # Memory monitoring settings
    MEMORY_CHECK_INTERVAL = int(os.getenv("MEMORY_CHECK_INTERVAL", "60"))  # Check every 60 seconds
    MEMORY_WARNING_THRESHOLD = float(os.getenv("MEMORY_WARNING_THRESHOLD", "0.90"))  # Warn at 90%
    
    # ============================================================================
    # WEB SERVER CONFIGURATION
    # ============================================================================
    # Server host and port
    SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")  # Listen on all interfaces
    SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
    
    # CORS settings (adjust for your network)
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # ============================================================================
    # LOGGING CONFIGURATION
    # ============================================================================
    # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Log file path (optional - leave empty to log to console only)
    LOG_FILE = os.getenv("LOG_FILE", "")
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    @classmethod
    def ensure_data_directories(cls):
        """Create data directories if they don't exist."""
        cls.DATA_DIR.mkdir(exist_ok=True)
        Path(cls.CHROMADB_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(cls.SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """
        Validate Pi configuration.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check that document processing is disabled
        if cls.ENABLE_DOCUMENT_PROCESSING:
            errors.append(
                "ENABLE_DOCUMENT_PROCESSING must be False on Raspberry Pi. "
                "Document processing should only run on desktop hardware."
            )
        
        # Check that conversational model is specified
        if not cls.CONVERSATIONAL_MODEL:
            errors.append("CONVERSATIONAL_MODEL must be specified")
        
        # Check that OLLAMA_MODEL matches CONVERSATIONAL_MODEL
        if cls.OLLAMA_MODEL != cls.CONVERSATIONAL_MODEL:
            errors.append(
                f"OLLAMA_MODEL ({cls.OLLAMA_MODEL}) must match CONVERSATIONAL_MODEL "
                f"({cls.CONVERSATIONAL_MODEL}) on Pi"
            )
        
        # Check that data paths exist
        if not Path(cls.CHROMADB_PATH).exists():
            errors.append(
                f"ChromaDB path does not exist: {cls.CHROMADB_PATH}. "
                "Please load the exported data package from desktop."
            )
        
        if not Path(cls.SQLITE_PATH).exists():
            errors.append(
                f"SQLite database does not exist: {cls.SQLITE_PATH}. "
                "Please load the exported data package from desktop."
            )
        
        # Check that manifest exists
        if not Path(cls.MANIFEST_PATH).exists():
            errors.append(
                f"Manifest file does not exist: {cls.MANIFEST_PATH}. "
                "The manifest is required for model compatibility validation."
            )
        
        # Validate timeout settings
        if cls.QUERY_TIMEOUT <= 0:
            errors.append("QUERY_TIMEOUT must be positive")
        
        if cls.RESPONSE_TIMEOUT <= 0:
            errors.append("RESPONSE_TIMEOUT must be positive")
        
        # Validate memory threshold
        if not (0 < cls.MEMORY_WARNING_THRESHOLD <= 1):
            errors.append("MEMORY_WARNING_THRESHOLD must be between 0 and 1")
        
        return (len(errors) == 0, errors)
    
    @classmethod
    def get_pi_info(cls) -> dict:
        """
        Get Pi-specific configuration information.
        
        Returns:
            Dictionary with Pi configuration details
        """
        return {
            "deployment_mode": "Pi Server (Read-Only)",
            "document_processing_enabled": cls.ENABLE_DOCUMENT_PROCESSING,
            "conversational_model": cls.CONVERSATIONAL_MODEL,
            "embedding_model": cls.EMBEDDING_MODEL,
            "data_paths": {
                "chromadb": cls.CHROMADB_PATH,
                "sqlite": cls.SQLITE_PATH,
                "manifest": cls.MANIFEST_PATH,
            },
            "performance_settings": {
                "top_k_results": cls.TOP_K_RESULTS,
                "similarity_threshold": cls.SIMILARITY_THRESHOLD,
                "query_timeout": cls.QUERY_TIMEOUT,
                "response_timeout": cls.RESPONSE_TIMEOUT,
            },
            "monitoring": {
                "memory_check_interval": cls.MEMORY_CHECK_INTERVAL,
                "memory_warning_threshold": cls.MEMORY_WARNING_THRESHOLD,
            },
            "server": {
                "host": cls.SERVER_HOST,
                "port": cls.SERVER_PORT,
            }
        }


# ============================================================================
# CONFIGURATION NOTES AND RECOMMENDATIONS
# ============================================================================
"""
RASPBERRY PI MODEL RECOMMENDATIONS:

1. Raspberry Pi 4 (8GB RAM) - RECOMMENDED
   - Model: qwen2.5:3b
   - Expected performance: 5-10 seconds per response
   - Concurrent users: 3-5
   - Memory usage: ~3-4GB

2. Raspberry Pi 4 (4GB RAM) - MINIMUM
   - Model: qwen2.5:1.5b (change CONVERSATIONAL_MODEL above)
   - Expected performance: 3-7 seconds per response
   - Concurrent users: 2-3
   - Memory usage: ~2-3GB

3. Raspberry Pi 5 (8GB RAM) - BEST PERFORMANCE
   - Model: qwen2.5:3b or qwen2.5:7b
   - Expected performance: 3-7 seconds per response
   - Concurrent users: 5-10
   - Memory usage: ~3-5GB

STORAGE RECOMMENDATIONS:
- Use SSD instead of microSD for better I/O performance
- Minimum 32GB storage
- Keep 10GB free for system operations

NETWORK RECOMMENDATIONS:
- Use wired Ethernet for better stability
- WiFi is acceptable for light usage (1-2 users)
- Consider static IP for easier access

OLLAMA INSTALLATION ON PI:
1. Install Ollama: curl -fsSL https://ollama.ai/install.sh | sh
2. Pull the model: ollama pull qwen2.5:3b
3. Verify: ollama list
4. Test: ollama run qwen2.5:3b "Hello"

TROUBLESHOOTING:
- If memory usage is high, reduce TOP_K_RESULTS to 3
- If responses are slow, consider using qwen2.5:1.5b
- If Ollama fails to start, check: sudo systemctl status ollama
- If queries fail, verify manifest.json exists and is valid
- Check logs for detailed error messages

MONITORING:
- Memory usage is logged every 60 seconds
- Access health check at: http://pi-ip:8000/api/health
- Monitor system resources: htop or top
- Check Ollama logs: journalctl -u ollama -f

SECURITY CONSIDERATIONS:
- Change SERVER_HOST to specific IP if not using firewall
- Consider adding authentication (not included in base template)
- Keep Pi on trusted network or behind firewall
- Regularly update system packages: sudo apt update && sudo apt upgrade
"""
