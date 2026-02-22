"""
Export Manager for Desktop-Pi RAG Pipeline

Orchestrates export of processed data for Pi deployment, including:
- Vector store and database export
- Manifest creation with model requirements
- Pi configuration template generation
- Compressed archive creation
- Deployment instructions generation
- Export package validation
- Disk space checking
- Pre-export data validation
"""

import os
import json
import shutil
import tarfile
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

from backend.config import Config
from backend.vector_store import VectorStore
from backend.database import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class ExportResult:
    """Result of export operation."""
    success: bool
    package_path: str
    archive_path: str
    size_bytes: int
    statistics: Dict[str, Any]
    errors: List[str]


@dataclass
class ValidationResult:
    """Result of export package validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]


class ExportManager:
    """
    Manages export of processed data for Pi deployment.
    
    Creates self-contained export packages with:
    - ChromaDB vector store directory
    - SQLite database
    - Manifest file with model requirements
    - Pi configuration template
    - Deployment instructions
    """
    
    def __init__(
        self,
        config: Config,
        vector_store: VectorStore,
        db_manager: DatabaseManager
    ):
        """
        Initialize export manager.
        
        Args:
            config: Application configuration
            vector_store: Vector store instance
            db_manager: Database manager instance
        """
        self.config = config
        self.vector_store = vector_store
        self.db_manager = db_manager
        
        logger.info("ExportManager initialized")
    
    def create_export_package(
        self,
        output_dir: str = "pi_export",
        incremental: bool = False,
        since_timestamp: Optional[datetime] = None
    ) -> ExportResult:
        """
        Create export package for Pi deployment.
        
        Args:
            output_dir: Directory to create export package
            incremental: If True, export only new/modified data
            since_timestamp: For incremental exports, export data modified after this time
            
        Returns:
            ExportResult with package path, size, and statistics
        """
        logger.info(f"Creating {'incremental' if incremental else 'full'} export package")
        
        errors = []
        package_path = Path(output_dir)
        
        try:
            # Step 0: Pre-export validation
            logger.info("Running pre-export validation...")
            validation_errors = self._validate_before_export(incremental=incremental)
            
            if validation_errors:
                logger.error(f"Pre-export validation failed with {len(validation_errors)} errors")
                for error in validation_errors:
                    logger.error(f"  - {error}")
                
                return ExportResult(
                    success=False,
                    package_path=str(package_path),
                    archive_path="",
                    size_bytes=0,
                    statistics={},
                    errors=validation_errors
                )
            
            logger.info("Pre-export validation passed")
            
            # Step 0.5: Check disk space
            logger.info("Checking available disk space...")
            disk_space_error = self._check_disk_space(output_dir)
            
            if disk_space_error:
                logger.error(f"Disk space check failed: {disk_space_error}")
                return ExportResult(
                    success=False,
                    package_path=str(package_path),
                    archive_path="",
                    size_bytes=0,
                    statistics={},
                    errors=[disk_space_error]
                )
            
            logger.info("Disk space check passed")
            
            # Create output directory
            package_path.mkdir(parents=True, exist_ok=True)
            
            # Step 1: Handle ChromaDB vector store (full or incremental)
            logger.info("Processing ChromaDB vector store...")
            chromadb_source = Path(self.config.CHROMADB_PATH)
            chromadb_dest = package_path / "chromadb"
            
            if not chromadb_source.exists():
                errors.append(f"ChromaDB directory not found: {chromadb_source}")
                return ExportResult(
                    success=False,
                    package_path=str(package_path),
                    archive_path="",
                    size_bytes=0,
                    statistics={},
                    errors=errors
                )
            
            if incremental and since_timestamp:
                # For incremental export, filter chunks by timestamp
                logger.info(f"Creating incremental export for chunks modified after {since_timestamp}")
                self._create_incremental_chromadb(chromadb_dest, since_timestamp)
            else:
                # For full export, copy entire ChromaDB directory
                logger.info("Copying full ChromaDB vector store...")
                if chromadb_dest.exists():
                    shutil.rmtree(chromadb_dest)
                shutil.copytree(chromadb_source, chromadb_dest)
            
            logger.info(f"ChromaDB processed to {chromadb_dest}")
            
            # Step 2: Copy SQLite database
            logger.info("Copying SQLite database...")
            db_source = Path(self.config.SQLITE_PATH)
            db_dest = package_path / "app.db"
            
            if not db_source.exists():
                errors.append(f"SQLite database not found: {db_source}")
                return ExportResult(
                    success=False,
                    package_path=str(package_path),
                    archive_path="",
                    size_bytes=0,
                    statistics={},
                    errors=errors
                )
            
            shutil.copy2(db_source, db_dest)
            logger.info(f"Database copied to {db_dest}")
            
            # Step 3: Get statistics
            logger.info("Gathering statistics...")
            statistics = self._gather_statistics(incremental, since_timestamp)
            
            # Step 4: Create manifest file
            logger.info("Creating manifest file...")
            manifest = self._create_manifest(incremental, since_timestamp, statistics)
            manifest_path = package_path / "manifest.json"
            
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, default=str)
            logger.info(f"Manifest created at {manifest_path}")
            
            # Step 5: Generate Pi configuration template
            logger.info("Generating Pi configuration template...")
            config_content = self._generate_pi_config()
            config_path = package_path / "config_pi.py"
            
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            logger.info(f"Pi config template created at {config_path}")
            
            # Step 6: Generate deployment instructions
            logger.info("Generating deployment instructions...")
            instructions = self.generate_deployment_instructions(str(package_path))
            instructions_path = package_path / "DEPLOYMENT.md"
            
            with open(instructions_path, 'w', encoding='utf-8') as f:
                f.write(instructions)
            logger.info(f"Deployment instructions created at {instructions_path}")
            
            # Step 7: Create compressed archive
            logger.info("Creating compressed archive...")
            archive_path = self._create_archive(package_path)
            logger.info(f"Archive created at {archive_path}")
            
            # Calculate total size
            total_size = Path(archive_path).stat().st_size
            
            logger.info(f"Export package created successfully: {archive_path}")
            logger.info(f"Package size: {total_size / (1024*1024):.2f} MB")
            
            return ExportResult(
                success=True,
                package_path=str(package_path),
                archive_path=archive_path,
                size_bytes=total_size,
                statistics=statistics,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Error creating export package: {e}")
            import traceback
            logger.error(traceback.format_exc())
            errors.append(str(e))
            
            return ExportResult(
                success=False,
                package_path=str(package_path),
                archive_path="",
                size_bytes=0,
                statistics={},
                errors=errors
            )
    
    def create_manifest(
        self,
        incremental: bool = False,
        since_timestamp: Optional[datetime] = None,
        statistics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create manifest file with model requirements and metadata.
        
        Public method for creating manifests independently of export package creation.
        
        Args:
            incremental: Whether this is an incremental export
            since_timestamp: Timestamp for incremental exports
            statistics: Export statistics (if None, will gather statistics)
            
        Returns:
            Manifest dictionary
        """
        # Gather statistics if not provided
        if statistics is None:
            statistics = self._gather_statistics(incremental, since_timestamp)
        
        # Use the private method to create the manifest
        return self._create_manifest(incremental, since_timestamp, statistics)
    
    def validate_manifest(self, manifest: Dict[str, Any]) -> ValidationResult:
        """
        Validate a manifest file for completeness and correctness.
        
        Args:
            manifest: Manifest dictionary to validate
            
        Returns:
            ValidationResult with validation status and any errors
        """
        logger.info("Validating manifest")
        
        errors = []
        warnings = []
        
        # Check required top-level fields
        required_fields = [
            "version",
            "created_at",
            "export_type",
            "desktop_config",
            "pi_requirements",
            "statistics",
            "incremental"
        ]
        
        for field in required_fields:
            if field not in manifest:
                errors.append(f"Manifest missing required field: {field}")
        
        # If critical fields are missing, return early
        if errors:
            return ValidationResult(valid=False, errors=errors, warnings=warnings)
        
        # Validate desktop_config fields
        desktop_config = manifest.get("desktop_config", {})
        required_desktop_fields = ["embedding_model", "embedding_dimension", "vision_model"]
        
        for field in required_desktop_fields:
            if field not in desktop_config:
                errors.append(f"Manifest desktop_config missing required field: {field}")
        
        # Validate embedding_dimension is a positive integer
        if "embedding_dimension" in desktop_config:
            dim = desktop_config["embedding_dimension"]
            if not isinstance(dim, int) or dim <= 0:
                errors.append(f"Invalid embedding_dimension in desktop_config: {dim}")
        
        # Validate pi_requirements fields
        pi_requirements = manifest.get("pi_requirements", {})
        required_pi_fields = ["conversational_model", "min_memory_gb", "embedding_dimension"]
        
        for field in required_pi_fields:
            if field not in pi_requirements:
                errors.append(f"Manifest pi_requirements missing required field: {field}")
        
        # Validate embedding_dimension is a positive integer
        if "embedding_dimension" in pi_requirements:
            dim = pi_requirements["embedding_dimension"]
            if not isinstance(dim, int) or dim <= 0:
                errors.append(f"Invalid embedding_dimension in pi_requirements: {dim}")
        
        # Validate min_memory_gb is a positive number
        if "min_memory_gb" in pi_requirements:
            mem = pi_requirements["min_memory_gb"]
            if not isinstance(mem, (int, float)) or mem <= 0:
                errors.append(f"Invalid min_memory_gb in pi_requirements: {mem}")
        
        # Check that embedding dimensions match between desktop and Pi
        desktop_dim = desktop_config.get("embedding_dimension")
        pi_dim = pi_requirements.get("embedding_dimension")
        
        if desktop_dim is not None and pi_dim is not None:
            if desktop_dim != pi_dim:
                errors.append(
                    f"Embedding dimension mismatch: desktop={desktop_dim}, pi={pi_dim}"
                )
        
        # Validate statistics fields
        statistics = manifest.get("statistics", {})
        expected_stats = ["total_documents", "total_chunks", "total_embeddings"]
        
        for field in expected_stats:
            if field not in statistics:
                warnings.append(f"Manifest statistics missing field: {field}")
        
        # Check for reasonable statistics values
        if "total_chunks" in statistics and statistics["total_chunks"] == 0:
            warnings.append("Export package contains no chunks")
        
        if "total_documents" in statistics and statistics["total_documents"] == 0:
            warnings.append("Export package contains no documents")
        
        # Validate incremental metadata
        incremental = manifest.get("incremental", {})
        required_incremental_fields = ["is_incremental", "base_version", "since_timestamp"]
        
        for field in required_incremental_fields:
            if field not in incremental:
                errors.append(f"Manifest incremental metadata missing field: {field}")
        
        # If is_incremental is True, check that since_timestamp is provided
        if incremental.get("is_incremental") is True:
            if not incremental.get("since_timestamp"):
                warnings.append(
                    "Incremental export should have since_timestamp set"
                )
        
        # Validate export_type matches incremental flag
        export_type = manifest.get("export_type")
        is_incremental = incremental.get("is_incremental", False)
        
        if export_type == "incremental" and not is_incremental:
            warnings.append(
                "export_type is 'incremental' but is_incremental is False"
            )
        elif export_type == "full" and is_incremental:
            warnings.append(
                "export_type is 'full' but is_incremental is True"
            )
        
        # Determine if validation passed
        valid = len(errors) == 0
        
        if valid:
            logger.info("Manifest validation passed")
            if warnings:
                logger.warning(f"Manifest validation warnings: {warnings}")
        else:
            logger.error(f"Manifest validation failed: {errors}")
        
        return ValidationResult(valid=valid, errors=errors, warnings=warnings)
    
    def _gather_statistics(
        self,
        incremental: bool,
        since_timestamp: Optional[datetime]
    ) -> Dict[str, Any]:
        """
        Gather statistics about the export.
        
        Args:
            incremental: Whether this is an incremental export
            since_timestamp: Timestamp for incremental exports
            
        Returns:
            Dictionary with statistics
        """
        stats = {}
        
        # Get vector store stats
        vs_stats = self.vector_store.get_stats()
        
        # Get database stats
        with self.db_manager.transaction() as conn:
            # Count total documents
            cursor = conn.execute("SELECT COUNT(*) FROM processed_files")
            total_documents = cursor.fetchone()[0]
            
            if incremental and since_timestamp:
                # Count new/modified documents since timestamp
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM processed_files WHERE processed_at > ?",
                    (since_timestamp,)
                )
                new_documents = cursor.fetchone()[0]
                stats['new_documents'] = new_documents
                
                # Get file paths of modified files
                cursor = conn.execute(
                    "SELECT file_path FROM processed_files WHERE processed_at > ?",
                    (since_timestamp,)
                )
                modified_files = {row['file_path'] for row in cursor.fetchall()}
                
                # Count chunks from modified files
                # We need to get all chunks and filter by file path
                try:
                    all_data = self.vector_store.collection.get(
                        include=["metadatas"]
                    )
                    
                    new_chunks = 0
                    for metadata in all_data['metadatas']:
                        if 'filename' in metadata and 'folder_path' in metadata:
                            # Construct file path from metadata
                            # Use forward slashes for consistency with database storage
                            folder_path = metadata['folder_path'].replace('\\', '/')
                            filename = metadata['filename']
                            file_path = f"{folder_path}/{filename}" if not folder_path.endswith('/') else f"{folder_path}{filename}"
                            
                            # Also check with Path normalization for cross-platform compatibility
                            file_path_normalized = str(Path(metadata['folder_path']) / metadata['filename'])
                            
                            # Check if this file was modified after the timestamp
                            if file_path in modified_files or file_path_normalized in modified_files:
                                new_chunks += 1
                    
                    stats['new_chunks'] = new_chunks
                    stats['total_chunks'] = new_chunks
                    stats['total_embeddings'] = new_chunks
                    
                except Exception as e:
                    logger.warning(f"Failed to count incremental chunks: {e}")
                    # Fallback to estimation
                    if total_documents > 0:
                        avg_chunks_per_doc = vs_stats['total_chunks'] / total_documents
                        stats['new_chunks'] = int(new_documents * avg_chunks_per_doc)
                    else:
                        stats['new_chunks'] = 0
                    stats['total_chunks'] = stats['new_chunks']
                    stats['total_embeddings'] = stats['new_chunks']
            else:
                # Full export statistics
                stats['total_documents'] = total_documents
                stats['total_chunks'] = vs_stats['total_chunks']
                stats['total_embeddings'] = vs_stats['total_chunks']
        
        # Get file sizes
        chromadb_path = Path(self.config.CHROMADB_PATH)
        db_path = Path(self.config.SQLITE_PATH)
        
        if chromadb_path.exists():
            chromadb_size = sum(
                f.stat().st_size for f in chromadb_path.rglob('*') if f.is_file()
            )
            stats['vector_store_size_mb'] = chromadb_size / (1024 * 1024)
        else:
            stats['vector_store_size_mb'] = 0
        
        if db_path.exists():
            stats['database_size_mb'] = db_path.stat().st_size / (1024 * 1024)
        else:
            stats['database_size_mb'] = 0
        
        return stats
    
    def _create_manifest(
        self,
        incremental: bool,
        since_timestamp: Optional[datetime],
        statistics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create manifest file with model requirements and metadata.
        
        Args:
            incremental: Whether this is an incremental export
            since_timestamp: Timestamp for incremental exports
            statistics: Export statistics
            
        Returns:
            Manifest dictionary
        """
        # Get embedding dimension from vector store
        embedding_dim = self.vector_store.get_embedding_dimension()
        if embedding_dim is None:
            logger.warning("Could not determine embedding dimension, using default 384")
            embedding_dim = 384
        
        manifest = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "export_type": "incremental" if incremental else "full",
            "desktop_config": {
                "embedding_model": self.config.EMBEDDING_MODEL,
                "embedding_dimension": embedding_dim,
                "vision_model": self.config.OLLAMA_MODEL
            },
            "pi_requirements": {
                "conversational_model": self.config.CONVERSATIONAL_MODEL,
                "min_memory_gb": 4,
                "embedding_dimension": embedding_dim
            },
            "statistics": statistics,
            "incremental": {
                "is_incremental": incremental,
                "base_version": None,
                "since_timestamp": since_timestamp.isoformat() if since_timestamp else None
            }
        }
        
        return manifest
    
    def _create_incremental_chromadb(
        self,
        dest_path: Path,
        since_timestamp: datetime
    ) -> None:
        """
        Create incremental ChromaDB with only chunks modified after timestamp.
        
        Args:
            dest_path: Destination path for incremental ChromaDB
            since_timestamp: Only include chunks from files processed after this time
        """
        import chromadb
        from chromadb.config import Settings
        
        logger.info(f"Creating incremental ChromaDB at {dest_path}")
        
        # Get list of files processed after timestamp
        modified_files = set()
        with self.db_manager.transaction() as conn:
            cursor = conn.execute(
                "SELECT file_path FROM processed_files WHERE processed_at > ?",
                (since_timestamp,)
            )
            for row in cursor.fetchall():
                modified_files.add(row['file_path'])
        
        logger.info(f"Found {len(modified_files)} files modified after {since_timestamp}")
        
        if not modified_files:
            logger.warning("No modified files found for incremental export")
            # Create empty ChromaDB directory
            dest_path.mkdir(parents=True, exist_ok=True)
            return
        
        # Get all chunks from source vector store
        # ChromaDB doesn't have a direct "get all" method, so we need to use get() with no filters
        try:
            all_data = self.vector_store.collection.get(
                include=["documents", "metadatas", "embeddings"]
            )
        except Exception as e:
            logger.error(f"Failed to retrieve chunks from vector store: {e}")
            raise
        
        # Filter chunks that belong to modified files
        filtered_ids = []
        filtered_embeddings = []
        filtered_documents = []
        filtered_metadatas = []
        
        for i, metadata in enumerate(all_data['metadatas']):
            # Check if this chunk belongs to a modified file
            # The metadata should have 'filename' and 'folder_path'
            if 'filename' in metadata and 'folder_path' in metadata:
                # Construct file path from metadata
                # Use forward slashes for consistency with database storage
                folder_path = metadata['folder_path'].replace('\\', '/')
                filename = metadata['filename']
                file_path = f"{folder_path}/{filename}" if not folder_path.endswith('/') else f"{folder_path}{filename}"
                
                # Also check with Path normalization for cross-platform compatibility
                file_path_normalized = str(Path(metadata['folder_path']) / metadata['filename'])
                
                # Check if this file was modified after the timestamp
                if file_path in modified_files or file_path_normalized in modified_files:
                    filtered_ids.append(all_data['ids'][i])
                    filtered_embeddings.append(all_data['embeddings'][i])
                    filtered_documents.append(all_data['documents'][i])
                    filtered_metadatas.append(metadata)
        
        logger.info(f"Filtered {len(filtered_ids)} chunks from {len(all_data['ids'])} total chunks")
        
        # Create new ChromaDB at destination with filtered chunks
        if dest_path.exists():
            shutil.rmtree(dest_path)
        dest_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize new ChromaDB client
        client = chromadb.PersistentClient(
            path=str(dest_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create collection with same name as source
        collection = client.get_or_create_collection(
            name=self.vector_store.collection.name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Add filtered chunks to new collection
        if filtered_ids:
            collection.add(
                ids=filtered_ids,
                embeddings=filtered_embeddings,
                documents=filtered_documents,
                metadatas=filtered_metadatas
            )
            logger.info(f"Added {len(filtered_ids)} chunks to incremental ChromaDB")
        else:
            logger.warning("No chunks to add to incremental ChromaDB")

    
    def _generate_pi_config(self) -> str:
        """
        Generate Pi configuration template.
        
        Returns:
            Configuration file content as string
        """
        config_template = '''"""Configuration for Raspberry Pi deployment."""

import os
from pathlib import Path


class Config:
    """Pi Server configuration."""
    
    # Ollama configuration - use smaller conversational model
    OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "{conversational_model}")
    
    # ChromaDB configuration - read-only mode
    CHROMADB_PATH = os.getenv("CHROMADB_PATH", str(Path("data/chromadb").absolute()))
    
    # SQLite configuration - read-only mode
    SQLITE_PATH = os.getenv("SQLITE_PATH", str(Path("data/app.db").absolute()))
    
    # Data directory
    DATA_DIR = Path("data")
    
    # Deployment mode: MUST be False on Pi (disables document processing)
    ENABLE_DOCUMENT_PROCESSING = False
    
    # Model configuration
    EMBEDDING_MODEL = "{embedding_model}"
    CONVERSATIONAL_MODEL = "{conversational_model}"
    
    # Manifest path for validation
    MANIFEST_PATH = os.getenv("MANIFEST_PATH", "data/manifest.json")
    
    @classmethod
    def ensure_data_directories(cls):
        """Create data directories if they don't exist."""
        cls.DATA_DIR.mkdir(exist_ok=True)
        Path(cls.CHROMADB_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(cls.SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
'''
        
        return config_template.format(
            conversational_model=self.config.CONVERSATIONAL_MODEL,
            embedding_model=self.config.EMBEDDING_MODEL
        )
    
    def _create_archive(self, package_path: Path) -> str:
        """
        Create compressed tar.gz archive of export package.
        
        Args:
            package_path: Path to export package directory
            
        Returns:
            Path to created archive
        """
        archive_name = f"{package_path.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
        archive_path = package_path.parent / archive_name
        
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(package_path, arcname=package_path.name)
        
        return str(archive_path)
    
    def validate_export_package(self, package_path: str) -> ValidationResult:
        """
        Validate an export package before transfer.
        
        Args:
            package_path: Path to export package directory
            
        Returns:
            ValidationResult with validation status and any errors
        """
        logger.info(f"Validating export package: {package_path}")
        
        errors = []
        warnings = []
        package = Path(package_path)
        
        # Check if package directory exists
        if not package.exists():
            errors.append(f"Package directory not found: {package_path}")
            return ValidationResult(valid=False, errors=errors, warnings=warnings)
        
        # Check for required files/directories
        required_items = {
            "chromadb": "ChromaDB vector store directory",
            "app.db": "SQLite database file",
            "manifest.json": "Manifest file",
            "config_pi.py": "Pi configuration template",
            "DEPLOYMENT.md": "Deployment instructions"
        }
        
        for item_name, description in required_items.items():
            item_path = package / item_name
            if not item_path.exists():
                errors.append(f"Missing {description}: {item_name}")
        
        # If critical files are missing, return early
        if errors:
            return ValidationResult(valid=False, errors=errors, warnings=warnings)
        
        # Validate manifest content
        manifest_path = package / "manifest.json"
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            # Check required manifest fields
            required_fields = [
                "version",
                "created_at",
                "export_type",
                "desktop_config",
                "pi_requirements",
                "statistics"
            ]
            
            for field in required_fields:
                if field not in manifest:
                    errors.append(f"Manifest missing required field: {field}")
            
            # Validate desktop_config
            if "desktop_config" in manifest:
                desktop_config = manifest["desktop_config"]
                if "embedding_dimension" not in desktop_config:
                    errors.append("Manifest desktop_config missing embedding_dimension")
                if "embedding_model" not in desktop_config:
                    warnings.append("Manifest desktop_config missing embedding_model")
            
            # Validate pi_requirements
            if "pi_requirements" in manifest:
                pi_req = manifest["pi_requirements"]
                if "embedding_dimension" not in pi_req:
                    errors.append("Manifest pi_requirements missing embedding_dimension")
                if "conversational_model" not in pi_req:
                    warnings.append("Manifest pi_requirements missing conversational_model")
            
            # Validate statistics
            if "statistics" in manifest:
                stats = manifest["statistics"]
                if stats.get("total_chunks", 0) == 0:
                    warnings.append("Export package contains no chunks")
                if stats.get("total_documents", 0) == 0:
                    warnings.append("Export package contains no documents")
        
        except json.JSONDecodeError as e:
            errors.append(f"Invalid manifest JSON: {e}")
        except Exception as e:
            errors.append(f"Error reading manifest: {e}")
        
        # Validate ChromaDB directory
        chromadb_path = package / "chromadb"
        if chromadb_path.exists():
            # Check if it has any files
            files = list(chromadb_path.rglob('*'))
            if not files:
                warnings.append("ChromaDB directory is empty")
        
        # Validate database file
        db_path = package / "app.db"
        if db_path.exists():
            if db_path.stat().st_size == 0:
                warnings.append("SQLite database file is empty")
        
        # Determine if validation passed
        valid = len(errors) == 0
        
        if valid:
            logger.info("Export package validation passed")
            if warnings:
                logger.warning(f"Validation warnings: {warnings}")
        else:
            logger.error(f"Export package validation failed: {errors}")
        
        return ValidationResult(valid=valid, errors=errors, warnings=warnings)
    
    def generate_deployment_instructions(self, package_path: str) -> str:
        """
        Generate deployment instructions for Pi setup.
        
        Args:
            package_path: Path to export package
            
        Returns:
            Markdown-formatted deployment instructions
        """
        package_name = Path(package_path).name
        
        instructions = f"""# Deployment Instructions for Raspberry Pi

## Overview

This export package contains all processed data needed to run the RAG chatbot on your Raspberry Pi.

**Package**: `{package_name}`
**Created**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Prerequisites

Before deploying, ensure your Raspberry Pi has:

1. **Hardware Requirements**:
   - Raspberry Pi 4 (4GB RAM minimum, 8GB recommended)
   - 32GB+ microSD card or SSD
   - Network connectivity

2. **Software Requirements**:
   - Raspberry Pi OS (64-bit)
   - Python 3.10 or higher
   - Ollama installed with {self.config.CONVERSATIONAL_MODEL} model

3. **Install Ollama** (if not already installed):
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

4. **Pull the conversational model**:
   ```bash
   ollama pull {self.config.CONVERSATIONAL_MODEL}
   ```

## Transfer Instructions

### Step 1: Transfer Export Package to Pi

From your desktop machine, transfer the export package to your Raspberry Pi:

```bash
# Option 1: Using SCP (replace pi_hostname with your Pi's hostname or IP)
scp {package_name}.tar.gz pi@pi_hostname:~/

# Option 2: Using rsync (more efficient for large files)
rsync -avz --progress {package_name}.tar.gz pi@pi_hostname:~/
```

### Step 2: Extract Package on Pi

SSH into your Raspberry Pi and extract the package:

```bash
ssh pi@pi_hostname

# Extract the archive
tar -xzf {package_name}.tar.gz

# Navigate to the package directory
cd {package_name}
```

## Installation Instructions

### Step 3: Set Up Directory Structure

Create the required directory structure on your Pi:

```bash
# Create data directory
mkdir -p ~/rag-chatbot/data

# Copy ChromaDB vector store
cp -r chromadb ~/rag-chatbot/data/

# Copy SQLite database
cp app.db ~/rag-chatbot/data/

# Copy manifest
cp manifest.json ~/rag-chatbot/data/

# Copy Pi configuration
cp config_pi.py ~/rag-chatbot/backend/config.py
```

### Step 4: Install Python Dependencies

Install required Python packages:

```bash
cd ~/rag-chatbot

# Install dependencies
pip install -r requirements.txt
```

### Step 5: Configure Environment

Set environment variables for Pi deployment:

```bash
# Add to ~/.bashrc or create .env file
export ENABLE_DOCUMENT_PROCESSING=false
export OLLAMA_MODEL={self.config.CONVERSATIONAL_MODEL}
export CHROMADB_PATH=~/rag-chatbot/data/chromadb
export SQLITE_PATH=~/rag-chatbot/data/app.db
```

## Starting the Pi Server

### Step 6: Start the Server

Start the RAG chatbot server:

```bash
cd ~/rag-chatbot

# Start the backend server
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
```

### Step 7: Verify Server is Running

Check that the server is running:

```bash
# Check health endpoint
curl http://localhost:8000/api/health

# Expected response:
# {{"status": "healthy", "memory_usage_percent": ..., ...}}
```

### Step 8: Access Web Interface

Open a web browser and navigate to:

```
http://pi_hostname:8000
```

Replace `pi_hostname` with your Pi's hostname or IP address.

## Configuration Changes

The following configuration changes are required for Pi deployment:

1. **Disable Document Processing**: `ENABLE_DOCUMENT_PROCESSING=false`
   - Pi operates in read-only mode
   - No document processing or embedding generation

2. **Use Conversational Model**: `OLLAMA_MODEL={self.config.CONVERSATIONAL_MODEL}`
   - Smaller model optimized for Pi hardware
   - CPU-only inference

3. **Read-Only Data Access**:
   - Vector store operates in read-only mode
   - Database operates in read-only mode
   - No modifications to processed data

## Troubleshooting

### Server Won't Start

1. Check Ollama is running:
   ```bash
   systemctl status ollama
   ```

2. Verify model is available:
   ```bash
   ollama list
   ```

3. Check logs for errors:
   ```bash
   tail -f ~/rag-chatbot/logs/app.log
   ```

### Memory Issues

If you encounter memory issues:

1. Monitor memory usage:
   ```bash
   free -h
   ```

2. Consider using a smaller model (e.g., qwen2.5:1.5b)

3. Reduce concurrent request handling

### Query Performance Issues

If queries are slow:

1. Check vector store loaded correctly
2. Verify embedding dimensions match
3. Monitor CPU usage during queries
4. Consider using SSD instead of microSD card

## Incremental Updates

To update the Pi with new documents:

1. Create incremental export on desktop
2. Transfer incremental package to Pi
3. Stop Pi server
4. Merge incremental data
5. Restart Pi server

See main documentation for incremental update procedures.

## Support

For issues or questions:
- Check logs in `~/rag-chatbot/logs/`
- Review manifest.json for configuration details
- Verify model compatibility and embedding dimensions

---

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return instructions
    def create_manifest(
        self,
        incremental: bool = False,
        since_timestamp: Optional[datetime] = None,
        statistics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create manifest file with model requirements and metadata.

        Public method for creating manifests independently of export package creation.

        Args:
            incremental: Whether this is an incremental export
            since_timestamp: Timestamp for incremental exports
            statistics: Export statistics (if None, will gather statistics)

        Returns:
            Manifest dictionary
        """
        # Gather statistics if not provided
        if statistics is None:
            statistics = self._gather_statistics(incremental, since_timestamp)

        # Use the private method to create the manifest
        return self._create_manifest(incremental, since_timestamp, statistics)

    def validate_manifest(self, manifest: Dict[str, Any]) -> ValidationResult:
        """
        Validate a manifest file for completeness and correctness.

        Args:
            manifest: Manifest dictionary to validate

        Returns:
            ValidationResult with validation status and any errors
        """
        logger.info("Validating manifest")

        errors = []
        warnings = []

        # Check required top-level fields
        required_fields = [
            "version",
            "created_at",
            "export_type",
            "desktop_config",
            "pi_requirements",
            "statistics",
            "incremental"
        ]

        for field in required_fields:
            if field not in manifest:
                errors.append(f"Manifest missing required field: {field}")

        # If critical fields are missing, return early
        if errors:
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        # Validate desktop_config fields
        desktop_config = manifest.get("desktop_config", {})
        required_desktop_fields = ["embedding_model", "embedding_dimension", "vision_model"]

        for field in required_desktop_fields:
            if field not in desktop_config:
                errors.append(f"Manifest desktop_config missing required field: {field}")

        # Validate embedding_dimension is a positive integer
        if "embedding_dimension" in desktop_config:
            dim = desktop_config["embedding_dimension"]
            if not isinstance(dim, int) or dim <= 0:
                errors.append(f"Invalid embedding_dimension in desktop_config: {dim}")

        # Validate pi_requirements fields
        pi_requirements = manifest.get("pi_requirements", {})
        required_pi_fields = ["conversational_model", "min_memory_gb", "embedding_dimension"]

        for field in required_pi_fields:
            if field not in pi_requirements:
                errors.append(f"Manifest pi_requirements missing required field: {field}")

        # Validate embedding_dimension is a positive integer
        if "embedding_dimension" in pi_requirements:
            dim = pi_requirements["embedding_dimension"]
            if not isinstance(dim, int) or dim <= 0:
                errors.append(f"Invalid embedding_dimension in pi_requirements: {dim}")

        # Validate min_memory_gb is a positive number
        if "min_memory_gb" in pi_requirements:
            mem = pi_requirements["min_memory_gb"]
            if not isinstance(mem, (int, float)) or mem <= 0:
                errors.append(f"Invalid min_memory_gb in pi_requirements: {mem}")

        # Check that embedding dimensions match between desktop and Pi
        desktop_dim = desktop_config.get("embedding_dimension")
        pi_dim = pi_requirements.get("embedding_dimension")

        if desktop_dim is not None and pi_dim is not None:
            if desktop_dim != pi_dim:
                errors.append(
                    f"Embedding dimension mismatch: desktop={desktop_dim}, pi={pi_dim}"
                )

        # Validate statistics fields
        statistics = manifest.get("statistics", {})
        expected_stats = ["total_documents", "total_chunks", "total_embeddings"]

        for field in expected_stats:
            if field not in statistics:
                warnings.append(f"Manifest statistics missing field: {field}")

        # Check for reasonable statistics values
        if "total_chunks" in statistics and statistics["total_chunks"] == 0:
            warnings.append("Export package contains no chunks")

        if "total_documents" in statistics and statistics["total_documents"] == 0:
            warnings.append("Export package contains no documents")

        # Validate incremental metadata
        incremental = manifest.get("incremental", {})
        required_incremental_fields = ["is_incremental", "base_version", "since_timestamp"]

        for field in required_incremental_fields:
            if field not in incremental:
                errors.append(f"Manifest incremental metadata missing field: {field}")

        # If is_incremental is True, check that since_timestamp is provided
        if incremental.get("is_incremental") is True:
            if not incremental.get("since_timestamp"):
                warnings.append(
                    "Incremental export should have since_timestamp set"
                )

        # Validate export_type matches incremental flag
        export_type = manifest.get("export_type")
        is_incremental = incremental.get("is_incremental", False)

        if export_type == "incremental" and not is_incremental:
            warnings.append(
                "export_type is 'incremental' but is_incremental is False"
            )
        elif export_type == "full" and is_incremental:
            warnings.append(
                "export_type is 'full' but is_incremental is True"
            )

        # Determine if validation passed
        valid = len(errors) == 0

        if valid:
            logger.info("Manifest validation passed")
            if warnings:
                logger.warning(f"Manifest validation warnings: {warnings}")
        else:
            logger.error(f"Manifest validation failed: {errors}")

        return ValidationResult(valid=valid, errors=errors, warnings=warnings)
    
    def _validate_before_export(self, incremental: bool = False) -> List[str]:
        """
        Validate data before export to prevent corrupted data.
        
        Checks:
        - Vector store exists and is accessible
        - Database exists and is accessible
        - All chunks have embeddings (for full exports)
        - All chunks have required metadata
        
        Args:
            incremental: If True, allow empty exports (no new data)
        
        Returns:
            List of validation errors (empty if validation passes)
        """
        errors = []
        
        # Check vector store exists
        chromadb_path = Path(self.config.CHROMADB_PATH)
        if not chromadb_path.exists():
            errors.append(f"Vector store directory not found: {chromadb_path}")
            return errors  # Can't continue without vector store
        
        # Check database exists
        db_path = Path(self.config.SQLITE_PATH)
        if not db_path.exists():
            errors.append(f"SQLite database not found: {db_path}")
            return errors  # Can't continue without database
        
        # Check vector store is accessible and has data
        try:
            vs_stats = self.vector_store.get_stats()
            total_chunks = vs_stats.get('total_chunks', 0)
            
            # For full exports, require at least one chunk
            # For incremental exports, allow empty (no new data since last export)
            if total_chunks == 0 and not incremental:
                errors.append("Vector store contains no chunks - nothing to export")
                return errors
            
            logger.info(f"Vector store contains {total_chunks} chunks")
            
        except Exception as e:
            errors.append(f"Failed to access vector store: {e}")
            return errors
        
        # Check database is accessible
        try:
            with self.db_manager.transaction() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM processed_files")
                total_docs = cursor.fetchone()[0]
                logger.info(f"Database contains {total_docs} processed documents")
                
        except Exception as e:
            errors.append(f"Failed to access database: {e}")
            return errors
        
        # Validate data integrity using ProcessingValidator
        try:
            from backend.processing_validator import ProcessingValidator
            
            validator = ProcessingValidator(self.vector_store, self.db_manager)
            report = validator.validate_processing()
            
            if not report.validation_passed:
                if report.missing_embeddings:
                    errors.append(
                        f"Found {len(report.missing_embeddings)} chunks missing embeddings. "
                        f"Run document processing to fix this issue."
                    )
                
                if report.incomplete_metadata:
                    errors.append(
                        f"Found {len(report.incomplete_metadata)} chunks with incomplete metadata. "
                        f"Run document processing to fix this issue."
                    )
            
            logger.info(f"Data validation: {report.total_chunks} chunks, {report.total_embeddings} embeddings")
            
        except Exception as e:
            logger.warning(f"Failed to run data validation: {e}")
            # Don't fail export if validation itself fails, just log warning
        
        return errors
    
    def _check_disk_space(self, output_dir: str) -> Optional[str]:
        """
        Check if there's enough disk space for export.
        
        Estimates required space based on:
        - ChromaDB directory size
        - SQLite database size
        - 20% buffer for compression and temporary files
        
        Args:
            output_dir: Directory where export will be created
            
        Returns:
            Error message if insufficient space, None if sufficient
        """
        try:
            # Get sizes of source data
            chromadb_path = Path(self.config.CHROMADB_PATH)
            db_path = Path(self.config.SQLITE_PATH)
            
            chromadb_size = 0
            if chromadb_path.exists():
                chromadb_size = sum(
                    f.stat().st_size for f in chromadb_path.rglob('*') if f.is_file()
                )
            
            db_size = 0
            if db_path.exists():
                db_size = db_path.stat().st_size
            
            # Estimate required space (data + 20% buffer for compression/temp files)
            required_space = int((chromadb_size + db_size) * 1.2)
            
            # Get available disk space
            output_path = Path(output_dir).resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            stat = shutil.disk_usage(output_path.parent)
            available_space = stat.free
            
            logger.info(f"Required space: {required_space / (1024**3):.2f} GB")
            logger.info(f"Available space: {available_space / (1024**3):.2f} GB")
            
            if available_space < required_space:
                return (
                    f"Insufficient disk space for export. "
                    f"Required: {required_space / (1024**3):.2f} GB, "
                    f"Available: {available_space / (1024**3):.2f} GB. "
                    f"Please free up at least {(required_space - available_space) / (1024**3):.2f} GB."
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to check disk space: {e}")
            # Don't fail export if disk space check fails, just log warning
            return None

