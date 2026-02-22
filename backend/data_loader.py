"""
Data Loader for Pi Server

Loads pre-computed data (vector store and database) on Pi startup.
Operates in read-only mode and validates manifest for model compatibility.

Enhanced with error handling:
- Retry logic for model loading (3 retries with exponential backoff)
- Safe mode for corrupted vector store
- Error logging with timestamps and context
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional
from datetime import datetime

from backend.config import Config
from backend.vector_store import VectorStore
from backend.database import DatabaseManager
from backend.models import ManifestValidation
from backend.embedding_engine import EmbeddingEngine

logger = logging.getLogger(__name__)


class DataLoadError(Exception):
    """Exception raised when data loading fails."""
    pass


class ManifestError(Exception):
    """Exception raised when manifest validation fails."""
    pass


class DataLoader:
    """
    Loads pre-computed data on Pi startup.
    
    Responsibilities:
    - Load vector store in read-only mode with retry logic
    - Load database in read-only mode
    - Validate manifest file
    - Check embedding dimension compatibility
    - Verify data integrity
    - Handle missing data gracefully
    - Safe mode for corrupted vector store
    - Error logging with timestamps and context
    
    Requirements: 14.1, 14.2, 14.4
    """
    
    def __init__(self, config: Config):
        """
        Initialize data loader with Pi configuration.
        
        Args:
            config: Configuration object with paths and settings
        """
        self.config = config
        self.safe_mode = False  # Safe mode flag for corrupted vector store
        self._log_with_context("DataLoader initialized")
    
    def _log_with_context(self, message: str, level: str = "info", error: Optional[Exception] = None):
        """
        Log message with timestamp and context.
        
        Args:
            message: Log message
            level: Log level (info, warning, error, critical)
            error: Optional exception for error context
        
        Requirements: 14.4
        """
        timestamp = datetime.now().isoformat()
        context = f"[{timestamp}] [DataLoader]"
        
        log_func = getattr(logger, level.lower(), logger.info)
        
        if error:
            log_func(f"{context} {message}: {str(error)}", exc_info=True)
        else:
            log_func(f"{context} {message}")
    
    def load_vector_store(self) -> VectorStore:
        """
        Load vector store in read-only mode with retry logic and safe mode.
        
        Implements retry logic (3 attempts with exponential backoff) for transient failures.
        Enters safe mode if vector store is corrupted.
        
        Returns:
            VectorStore instance configured for read-only access
            
        Raises:
            DataLoadError: If vector store is missing or corrupted after retries
        
        Requirements: 14.1, 14.2
        """
        self._log_with_context(f"Loading vector store from {self.config.CHROMADB_PATH}")
        
        # Check if vector store directory exists
        vector_store_path = Path(self.config.CHROMADB_PATH)
        if not vector_store_path.exists():
            error_msg = (
                f"Vector store not found at {self.config.CHROMADB_PATH}. "
                "Please ensure the export package has been transferred and extracted."
            )
            self._log_with_context(error_msg, level="error")
            raise DataLoadError(error_msg)
        
        # Check if directory is empty
        if not any(vector_store_path.iterdir()):
            error_msg = (
                f"Vector store directory is empty at {self.config.CHROMADB_PATH}. "
                "Please ensure the export package was extracted correctly."
            )
            self._log_with_context(error_msg, level="error")
            raise DataLoadError(error_msg)
        
        # Retry logic: 3 attempts with exponential backoff (1s, 2s, 4s)
        max_retries = 3
        backoff_delays = [1, 2, 4]
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    self._log_with_context(
                        f"Retry attempt {attempt + 1}/{max_retries} for vector store loading",
                        level="warning"
                    )
                
                # Initialize vector store in read-only mode
                vector_store = VectorStore(
                    persist_directory=self.config.CHROMADB_PATH,
                    read_only=True
                )
                vector_store.initialize()
                
                # Verify vector store has data
                stats = vector_store.get_stats()
                total_chunks = stats.get('total_chunks', 0)
                
                if total_chunks == 0:
                    error_msg = (
                        "Vector store is empty. "
                        "Please ensure documents were processed on the desktop before export."
                    )
                    self._log_with_context(error_msg, level="error")
                    raise DataLoadError(error_msg)
                
                self._log_with_context(f"Vector store loaded successfully with {total_chunks} chunks")
                return vector_store
                
            except DataLoadError:
                # Don't retry for empty vector store
                raise
                
            except Exception as e:
                last_error = e
                self._log_with_context(
                    f"Vector store loading attempt {attempt + 1} failed",
                    level="error",
                    error=e
                )
                
                # Check if this is a corruption error
                if "corrupt" in str(e).lower() or "integrity" in str(e).lower():
                    self._log_with_context(
                        "Vector store appears to be corrupted, entering safe mode",
                        level="critical"
                    )
                    self.safe_mode = True
                    error_msg = (
                        f"Vector store is corrupted: {str(e)}. "
                        "System entering safe mode. Please re-export and transfer data from desktop."
                    )
                    raise DataLoadError(error_msg) from e
                
                # Wait before retry (except on last attempt)
                if attempt < max_retries - 1:
                    delay = backoff_delays[attempt]
                    self._log_with_context(f"Waiting {delay}s before retry", level="warning")
                    time.sleep(delay)
        
        # All retries failed
        error_msg = f"Failed to load vector store after {max_retries} attempts: {str(last_error)}"
        self._log_with_context(error_msg, level="error", error=last_error)
        raise DataLoadError(error_msg) from last_error
    
    def load_database(self) -> DatabaseManager:
        """
        Load SQLite database in read-only mode with retry logic.
        
        Returns:
            DatabaseManager instance configured for read-only access
            
        Raises:
            DataLoadError: If database is missing or corrupted
        
        Requirements: 14.1
        """
        self._log_with_context(f"Loading database from {self.config.SQLITE_PATH}")
        
        # Check if database file exists
        db_path = Path(self.config.SQLITE_PATH)
        if not db_path.exists():
            error_msg = (
                f"Database not found at {self.config.SQLITE_PATH}. "
                "Please ensure the export package has been transferred and extracted."
            )
            self._log_with_context(error_msg, level="error")
            raise DataLoadError(error_msg)
        
        # Check if file is not empty
        if db_path.stat().st_size == 0:
            error_msg = (
                f"Database file is empty at {self.config.SQLITE_PATH}. "
                "Please ensure the export package was created correctly."
            )
            self._log_with_context(error_msg, level="error")
            raise DataLoadError(error_msg)
        
        # Retry logic: 3 attempts with exponential backoff
        max_retries = 3
        backoff_delays = [1, 2, 4]
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    self._log_with_context(
                        f"Retry attempt {attempt + 1}/{max_retries} for database loading",
                        level="warning"
                    )
                
                # Initialize database manager
                db_manager = DatabaseManager(db_path=self.config.SQLITE_PATH)
                
                self._log_with_context("Database loaded successfully")
                return db_manager
                
            except Exception as e:
                last_error = e
                self._log_with_context(
                    f"Database loading attempt {attempt + 1} failed",
                    level="error",
                    error=e
                )
                
                # Wait before retry (except on last attempt)
                if attempt < max_retries - 1:
                    delay = backoff_delays[attempt]
                    self._log_with_context(f"Waiting {delay}s before retry", level="warning")
                    time.sleep(delay)
        
        # All retries failed
        error_msg = f"Failed to load database after {max_retries} attempts: {str(last_error)}"
        self._log_with_context(error_msg, level="error", error=last_error)
        raise DataLoadError(error_msg) from last_error
    
    def validate_manifest(self, manifest_path: Optional[str] = None) -> ManifestValidation:
        """
        Validate manifest file and check model compatibility.
        
        Args:
            manifest_path: Path to manifest.json file (uses config default if not provided)
            
        Returns:
            ManifestValidation with compatibility status
            
        Raises:
            ManifestError: If manifest is invalid or models incompatible
        
        Requirements: 14.4
        """
        if manifest_path is None:
            manifest_path = self.config.MANIFEST_PATH
        
        self._log_with_context(f"Validating manifest at {manifest_path}")
        
        manifest_file = Path(manifest_path)
        errors = []
        warnings = []
        
        # Check if manifest exists
        if not manifest_file.exists():
            warning_msg = (
                f"Manifest file not found at {manifest_path}. "
                "Proceeding with default settings, but compatibility cannot be verified."
            )
            self._log_with_context(warning_msg, level="warning")
            warnings.append(warning_msg)
            
            return ManifestValidation(
                valid=True,  # Allow operation without manifest
                embedding_dimension_match=False,
                model_compatible=False,
                errors=[],
                warnings=warnings
            )
        
        try:
            # Load manifest
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
            
            # Validate manifest structure
            required_fields = ['version', 'created_at', 'desktop_config', 'pi_requirements']
            missing_fields = [field for field in required_fields if field not in manifest]
            
            if missing_fields:
                error_msg = f"Manifest is missing required fields: {', '.join(missing_fields)}"
                self._log_with_context(error_msg, level="error")
                errors.append(error_msg)
                
                return ManifestValidation(
                    valid=False,
                    embedding_dimension_match=False,
                    model_compatible=False,
                    errors=errors,
                    warnings=warnings
                )
            
            # Extract configuration
            desktop_config = manifest.get('desktop_config', {})
            pi_requirements = manifest.get('pi_requirements', {})
            
            # Check embedding dimension compatibility
            manifest_embedding_dim = desktop_config.get('embedding_dimension')
            
            if manifest_embedding_dim is None:
                warning_msg = "Manifest does not specify embedding dimension"
                self._log_with_context(warning_msg, level="warning")
                warnings.append(warning_msg)
                embedding_dimension_match = False
            else:
                # Get expected embedding dimension from embedding engine
                try:
                    embedding_engine = EmbeddingEngine(model_name=self.config.EMBEDDING_MODEL)
                    expected_dim = embedding_engine.get_embedding_dimension()
                    
                    if manifest_embedding_dim != expected_dim:
                        error_msg = (
                            f"Embedding dimension mismatch: "
                            f"manifest specifies {manifest_embedding_dim}, "
                            f"but model {self.config.EMBEDDING_MODEL} produces {expected_dim} dimensions"
                        )
                        self._log_with_context(error_msg, level="error")
                        errors.append(error_msg)
                        embedding_dimension_match = False
                    else:
                        self._log_with_context(f"Embedding dimensions match: {expected_dim}")
                        embedding_dimension_match = True
                        
                except Exception as e:
                    warning_msg = f"Could not verify embedding dimensions: {str(e)}"
                    self._log_with_context(warning_msg, level="warning", error=e)
                    warnings.append(warning_msg)
                    embedding_dimension_match = False
            
            # Check model compatibility
            required_model = pi_requirements.get('conversational_model')
            current_model = self.config.CONVERSATIONAL_MODEL
            
            if required_model and required_model != current_model:
                warning_msg = (
                    f"Model mismatch: manifest recommends {required_model}, "
                    f"but current configuration uses {current_model}. "
                    "This may affect response quality."
                )
                self._log_with_context(warning_msg, level="warning")
                warnings.append(warning_msg)
                model_compatible = False
            else:
                self._log_with_context(f"Model configuration compatible: {current_model}")
                model_compatible = True
            
            # Check memory requirements
            min_memory_gb = pi_requirements.get('min_memory_gb')
            if min_memory_gb:
                try:
                    import psutil
                    available_memory_gb = psutil.virtual_memory().total / (1024 ** 3)
                    
                    if available_memory_gb < min_memory_gb:
                        warning_msg = (
                            f"System memory ({available_memory_gb:.1f}GB) is below "
                            f"recommended minimum ({min_memory_gb}GB). "
                            "Performance may be degraded."
                        )
                        self._log_with_context(warning_msg, level="warning")
                        warnings.append(warning_msg)
                    else:
                        self._log_with_context(f"Memory requirements met: {available_memory_gb:.1f}GB available")
                        
                except ImportError:
                    self._log_with_context("psutil not available, cannot check memory requirements", level="warning")
            
            # Determine overall validity
            valid = len(errors) == 0
            
            if valid:
                self._log_with_context("Manifest validation passed")
            else:
                self._log_with_context(f"Manifest validation failed with {len(errors)} errors", level="error")
            
            return ManifestValidation(
                valid=valid,
                embedding_dimension_match=embedding_dimension_match,
                model_compatible=model_compatible,
                errors=errors,
                warnings=warnings
            )
            
        except json.JSONDecodeError as e:
            error_msg = f"Manifest file is not valid JSON: {str(e)}"
            self._log_with_context(error_msg, level="error", error=e)
            errors.append(error_msg)
            
            return ManifestValidation(
                valid=False,
                embedding_dimension_match=False,
                model_compatible=False,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            error_msg = f"Failed to validate manifest: {str(e)}"
            self._log_with_context(error_msg, level="error", error=e)
            errors.append(error_msg)
            
            return ManifestValidation(
                valid=False,
                embedding_dimension_match=False,
                model_compatible=False,
                errors=errors,
                warnings=warnings
            )
