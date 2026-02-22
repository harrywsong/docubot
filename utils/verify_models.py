"""
Utility to verify Ollama model integrity and automatically recover corrupted models.

Run this before starting the backend to ensure models are working correctly.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.ollama_client import OllamaClient
from backend.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def verify_and_recover_models():
    """
    Verify all required Ollama models and recover if corrupted.
    
    Returns:
        True if all models are working, False otherwise
    """
    models_to_check = [
        ("qwen2.5vl:7b", "Vision model for document processing"),
        ("qwen2.5:7b", "Text model for response generation")
    ]
    
    all_ok = True
    
    for model_name, description in models_to_check:
        logger.info(f"Checking {description} ({model_name})...")
        
        client = OllamaClient(model=model_name)
        
        # Check if model exists
        if not client.is_model_available():
            logger.error(f"Model {model_name} is not installed!")
            logger.info(f"Please run: ollama pull {model_name}")
            all_ok = False
            continue
        
        # Verify integrity
        logger.info(f"Verifying integrity of {model_name}...")
        if not client.verify_model_integrity():
            logger.warning(f"Model {model_name} failed integrity check. Attempting recovery...")
            
            if client._recover_corrupted_model():
                logger.info(f"✓ Model {model_name} recovered successfully")
            else:
                logger.error(f"✗ Failed to recover {model_name}")
                logger.error(f"Please manually run: ollama rm {model_name} && ollama pull {model_name}")
                all_ok = False
        else:
            logger.info(f"✓ Model {model_name} is working correctly")
    
    return all_ok


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Ollama Model Integrity Verification")
    logger.info("=" * 60)
    
    if verify_and_recover_models():
        logger.info("\n✓ All models verified successfully!")
        sys.exit(0)
    else:
        logger.error("\n✗ Some models failed verification. Please fix the issues above.")
        sys.exit(1)
