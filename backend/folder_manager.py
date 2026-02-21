"""
Folder manager for RAG chatbot.

Handles folder addition, removal, listing, and scanning for supported file types.
"""

import os
import logging
from pathlib import Path
from typing import List, Tuple
from datetime import datetime

from backend.database import DatabaseManager
from backend.models import WatchedFolder

logger = logging.getLogger(__name__)

# Supported file extensions
SUPPORTED_TEXT_EXTENSIONS = {'.pdf', '.txt'}
SUPPORTED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg'}
SUPPORTED_EXTENSIONS = SUPPORTED_TEXT_EXTENSIONS | SUPPORTED_IMAGE_EXTENSIONS


class FolderManager:
    """Manages watched folders for document processing."""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize folder manager.
        
        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
    
    def add_folder(self, folder_path: str) -> Tuple[bool, str, WatchedFolder]:
        """
        Add a folder to the watched folders list.
        
        Args:
            folder_path: Path to folder to watch
            
        Returns:
            Tuple of (success, message, watched_folder or None)
        """
        # Validate folder path
        is_valid, error_msg = self._validate_folder_path(folder_path)
        if not is_valid:
            return False, error_msg, None
        
        # Convert to absolute path
        abs_path = str(Path(folder_path).resolve())
        
        try:
            with self.db.transaction() as conn:
                # Check if folder already exists
                cursor = conn.execute(
                    "SELECT id, path, added_at FROM folders WHERE path = ?",
                    (abs_path,)
                )
                existing = cursor.fetchone()
                
                if existing:
                    folder = WatchedFolder(
                        id=existing['id'],
                        path=existing['path'],
                        added_at=datetime.fromisoformat(existing['added_at'])
                    )
                    return False, f"Folder already exists: {abs_path}", folder
                
                # Insert new folder
                cursor = conn.execute(
                    "INSERT INTO folders (path) VALUES (?)",
                    (abs_path,)
                )
                folder_id = cursor.lastrowid
                
                # Fetch the created folder
                cursor = conn.execute(
                    "SELECT id, path, added_at FROM folders WHERE id = ?",
                    (folder_id,)
                )
                row = cursor.fetchone()
                
                folder = WatchedFolder(
                    id=row['id'],
                    path=row['path'],
                    added_at=datetime.fromisoformat(row['added_at'])
                )
                
                logger.info(f"Added folder: {abs_path}")
                return True, f"Folder added successfully: {abs_path}", folder
                
        except Exception as e:
            logger.error(f"Failed to add folder {folder_path}: {e}")
            return False, f"Failed to add folder: {str(e)}", None
    
    def remove_folder(self, folder_path: str) -> Tuple[bool, str]:
        """
        Remove a folder from the watched folders list.
        
        Args:
            folder_path: Path to folder to remove
            
        Returns:
            Tuple of (success, message)
        """
        # Convert to absolute path for consistency
        abs_path = str(Path(folder_path).resolve())
        
        try:
            with self.db.transaction() as conn:
                # Check if folder exists
                cursor = conn.execute(
                    "SELECT id FROM folders WHERE path = ?",
                    (abs_path,)
                )
                existing = cursor.fetchone()
                
                if not existing:
                    return False, f"Folder not found: {abs_path}"
                
                # Delete folder (CASCADE will delete associated processed_files)
                conn.execute(
                    "DELETE FROM folders WHERE path = ?",
                    (abs_path,)
                )
                
                logger.info(f"Removed folder: {abs_path}")
                return True, f"Folder removed successfully: {abs_path}"
                
        except Exception as e:
            logger.error(f"Failed to remove folder {folder_path}: {e}")
            return False, f"Failed to remove folder: {str(e)}"
    
    def list_folders(self) -> List[WatchedFolder]:
        """
        List all watched folders.
        
        Returns:
            List of WatchedFolder objects
        """
        try:
            with self.db.transaction() as conn:
                cursor = conn.execute(
                    "SELECT id, path, added_at FROM folders ORDER BY added_at DESC"
                )
                rows = cursor.fetchall()
                
                folders = [
                    WatchedFolder(
                        id=row['id'],
                        path=row['path'],
                        added_at=datetime.fromisoformat(row['added_at'])
                    )
                    for row in rows
                ]
                
                return folders
                
        except Exception as e:
            logger.error(f"Failed to list folders: {e}")
            return []
    
    def scan_folder(self, folder_path: str) -> Tuple[List[str], List[str]]:
        """
        Scan a folder for supported files.
        
        Args:
            folder_path: Path to folder to scan
            
        Returns:
            Tuple of (text_files, image_files) with absolute paths
        """
        text_files = []
        image_files = []
        
        try:
            folder = Path(folder_path)
            
            if not folder.exists() or not folder.is_dir():
                logger.warning(f"Folder does not exist or is not a directory: {folder_path}")
                return text_files, image_files
            
            # Recursively scan folder
            for file_path in folder.rglob('*'):
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    
                    if ext in SUPPORTED_TEXT_EXTENSIONS:
                        text_files.append(str(file_path.resolve()))
                    elif ext in SUPPORTED_IMAGE_EXTENSIONS:
                        image_files.append(str(file_path.resolve()))
            
            logger.info(f"Scanned {folder_path}: {len(text_files)} text files, {len(image_files)} image files")
            return text_files, image_files
            
        except Exception as e:
            logger.error(f"Failed to scan folder {folder_path}: {e}")
            return text_files, image_files
    
    def _validate_folder_path(self, folder_path: str) -> Tuple[bool, str]:
        """
        Validate a folder path.
        
        Args:
            folder_path: Path to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not folder_path or not isinstance(folder_path, str):
            return False, "Folder path cannot be empty"
        
        try:
            path = Path(folder_path)
            
            # Check if path exists
            if not path.exists():
                return False, f"Folder does not exist or is not accessible: {folder_path}"
            
            # Check if it's a directory
            if not path.is_dir():
                return False, f"Path is not a directory: {folder_path}"
            
            # Check if we can read the directory
            if not os.access(path, os.R_OK):
                return False, f"Folder is not accessible (no read permission): {folder_path}"
            
            return True, ""
            
        except Exception as e:
            return False, f"Invalid folder path: {str(e)}"
