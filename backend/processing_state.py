"""
Processing state manager for tracking document processing status.

Handles file state checking, hash computation, and state updates to enable
incremental document processing (skip unchanged files, process new/modified files).
"""

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal

from backend.database import DatabaseManager

logger = logging.getLogger(__name__)


class ProcessingStateManager:
    """Manages processing state for incremental document updates."""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize processing state manager.
        
        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
    
    def compute_file_hash(self, file_path: str) -> str:
        """
        Compute SHA-256 hash of file contents for change detection.
        
        Args:
            file_path: Path to file
            
        Returns:
            Hexadecimal hash string
            
        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file cannot be read
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not path.is_file():
            raise IOError(f"Not a file: {file_path}")
        
        try:
            sha256_hash = hashlib.sha256()
            
            # Read file in chunks to handle large files efficiently
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256_hash.update(chunk)
            
            return sha256_hash.hexdigest()
        
        except Exception as e:
            logger.error(f"Failed to compute hash for {file_path}: {e}")
            raise IOError(f"Cannot read file: {file_path}") from e
    
    def check_file_state(
        self, 
        file_path: str
    ) -> Literal["new", "modified", "unchanged"]:
        """
        Check if a file needs processing based on modification time and hash.
        
        Args:
            file_path: Path to file to check
            
        Returns:
            "new" if file has never been processed
            "modified" if file exists in DB but has changed
            "unchanged" if file exists in DB and hasn't changed
            
        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file cannot be accessed
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get current file state
        try:
            current_mtime = datetime.fromtimestamp(path.stat().st_mtime)
            current_hash = self.compute_file_hash(file_path)
        except Exception as e:
            logger.error(f"Failed to get file state for {file_path}: {e}")
            raise IOError(f"Cannot access file: {file_path}") from e
        
        # Check database for existing record
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT file_hash, modified_at 
                FROM processed_files 
                WHERE file_path = ?
                """,
                (str(path.absolute()),)
            )
            row = cursor.fetchone()
        
        # File not in database - it's new
        if row is None:
            logger.debug(f"File is new: {file_path}")
            return "new"
        
        stored_hash = row["file_hash"]
        stored_mtime = datetime.fromisoformat(row["modified_at"])
        
        # Check if file has been modified
        if current_hash != stored_hash or current_mtime > stored_mtime:
            logger.debug(f"File is modified: {file_path}")
            return "modified"
        
        logger.debug(f"File is unchanged: {file_path}")
        return "unchanged"
    
    def update_file_state(
        self,
        file_path: str,
        folder_id: int,
        file_type: Literal["text", "image"],
        user_id: int
    ) -> None:
        """
        Update processing state after successful file processing.
        
        Args:
            file_path: Path to processed file
            folder_id: ID of folder containing the file
            file_type: Type of file ("text" or "image")
            user_id: User ID who owns this file
            
        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file cannot be accessed
            ValueError: If folder_id is invalid or file_type is invalid
        """
        if file_type not in ("text", "image"):
            raise ValueError(f"Invalid file_type: {file_type}. Must be 'text' or 'image'")
        
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get current file state
        try:
            current_mtime = datetime.fromtimestamp(path.stat().st_mtime)
            current_hash = self.compute_file_hash(file_path)
        except Exception as e:
            logger.error(f"Failed to get file state for {file_path}: {e}")
            raise IOError(f"Cannot access file: {file_path}") from e
        
        # Verify folder_id exists
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "SELECT id FROM folders WHERE id = ?",
                (folder_id,)
            )
            if cursor.fetchone() is None:
                raise ValueError(f"Invalid folder_id: {folder_id}")
        
        # Insert or update processing state
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO processed_files 
                    (file_path, folder_id, user_id, file_hash, modified_at, file_type)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path, user_id) DO UPDATE SET
                    file_hash = excluded.file_hash,
                    modified_at = excluded.modified_at,
                    processed_at = CURRENT_TIMESTAMP,
                    file_type = excluded.file_type,
                    folder_id = excluded.folder_id
                """,
                (
                    str(path.absolute()),
                    folder_id,
                    user_id,
                    current_hash,
                    current_mtime.isoformat(),
                    file_type
                )
            )
        
        logger.info(f"Updated processing state for {file_path} (user_id={user_id})")
