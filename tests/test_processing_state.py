"""
Unit tests for processing state manager module.
"""

import pytest
import tempfile
import os
import time
from pathlib import Path
from datetime import datetime

from backend.processing_state import ProcessingStateManager
from backend.database import DatabaseManager


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    db_manager = DatabaseManager(db_path)
    yield db_manager
    
    db_manager.close_all()
    os.unlink(db_path)


@pytest.fixture
def state_manager(temp_db):
    """Create a processing state manager with temporary database."""
    return ProcessingStateManager(temp_db)


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Test content for hashing")
        temp_path = f.name
    
    yield temp_path
    
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def test_folder(temp_db):
    """Create a test folder in the database."""
    with temp_db.transaction() as conn:
        cursor = conn.execute(
            "INSERT INTO folders (path) VALUES (?)",
            ("/test/folder",)
        )
        folder_id = cursor.lastrowid
    
    return folder_id


class TestComputeFileHash:
    """Test file hash computation."""
    
    def test_compute_hash_basic(self, state_manager, temp_file):
        """Test computing hash of a file."""
        hash1 = state_manager.compute_file_hash(temp_file)
        
        # Hash should be a 64-character hex string (SHA-256)
        assert isinstance(hash1, str)
        assert len(hash1) == 64
        assert all(c in '0123456789abcdef' for c in hash1)
    
    def test_compute_hash_consistency(self, state_manager, temp_file):
        """Test that hash is consistent for same file."""
        hash1 = state_manager.compute_file_hash(temp_file)
        hash2 = state_manager.compute_file_hash(temp_file)
        
        assert hash1 == hash2
    
    def test_compute_hash_different_content(self, state_manager):
        """Test that different content produces different hashes."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f1:
            f1.write("Content A")
            path1 = f1.name
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f2:
            f2.write("Content B")
            path2 = f2.name
        
        try:
            hash1 = state_manager.compute_file_hash(path1)
            hash2 = state_manager.compute_file_hash(path2)
            
            assert hash1 != hash2
        finally:
            os.unlink(path1)
            os.unlink(path2)
    
    def test_compute_hash_nonexistent_file(self, state_manager):
        """Test computing hash of nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            state_manager.compute_file_hash("/nonexistent/file.txt")
    
    def test_compute_hash_directory(self, state_manager):
        """Test computing hash of directory raises error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(IOError):
                state_manager.compute_file_hash(temp_dir)
    
    def test_compute_hash_large_file(self, state_manager):
        """Test computing hash of large file (tests chunked reading)."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            # Write 1MB of data
            f.write("a" * (1024 * 1024))
            temp_path = f.name
        
        try:
            hash_value = state_manager.compute_file_hash(temp_path)
            assert len(hash_value) == 64
        finally:
            os.unlink(temp_path)


class TestCheckFileState:
    """Test file state checking."""
    
    def test_check_new_file(self, state_manager, temp_file):
        """Test checking state of new file (never processed)."""
        state = state_manager.check_file_state(temp_file)
        assert state == "new"
    
    def test_check_unchanged_file(self, state_manager, temp_file, test_folder):
        """Test checking state of unchanged file."""
        # First, update the file state
        state_manager.update_file_state(temp_file, test_folder, "text")
        
        # Check state - should be unchanged
        state = state_manager.check_file_state(temp_file)
        assert state == "unchanged"
    
    def test_check_modified_file_content(self, state_manager, temp_file, test_folder):
        """Test checking state of file with modified content."""
        # Process the file
        state_manager.update_file_state(temp_file, test_folder, "text")
        
        # Modify the file content
        time.sleep(0.01)  # Ensure timestamp changes
        with open(temp_file, 'a') as f:
            f.write("\nModified content")
        
        # Check state - should be modified
        state = state_manager.check_file_state(temp_file)
        assert state == "modified"
    
    def test_check_modified_file_timestamp(self, state_manager, temp_file, test_folder):
        """Test checking state of file with newer timestamp."""
        # Process the file
        state_manager.update_file_state(temp_file, test_folder, "text")
        
        # Touch the file to update timestamp
        time.sleep(0.01)
        Path(temp_file).touch()
        
        # Check state - should be modified (timestamp changed)
        state = state_manager.check_file_state(temp_file)
        assert state == "modified"
    
    def test_check_nonexistent_file(self, state_manager):
        """Test checking state of nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            state_manager.check_file_state("/nonexistent/file.txt")


class TestUpdateFileState:
    """Test file state updates."""
    
    def test_update_new_file(self, state_manager, temp_file, test_folder):
        """Test updating state for new file."""
        state_manager.update_file_state(temp_file, test_folder, "text")
        
        # Verify file is now in database
        state = state_manager.check_file_state(temp_file)
        assert state == "unchanged"
    
    def test_update_existing_file(self, state_manager, temp_file, test_folder):
        """Test updating state for already processed file."""
        # Process file first time
        state_manager.update_file_state(temp_file, test_folder, "text")
        
        # Modify file
        time.sleep(0.01)
        with open(temp_file, 'a') as f:
            f.write("\nNew content")
        
        # Process file second time
        state_manager.update_file_state(temp_file, test_folder, "text")
        
        # Should be unchanged now
        state = state_manager.check_file_state(temp_file)
        assert state == "unchanged"
    
    def test_update_with_image_type(self, state_manager, temp_file, test_folder):
        """Test updating state with image file type."""
        state_manager.update_file_state(temp_file, test_folder, "image")
        
        # Verify it's stored correctly
        with state_manager.db.transaction() as conn:
            cursor = conn.execute(
                "SELECT file_type FROM processed_files WHERE file_path = ?",
                (str(Path(temp_file).absolute()),)
            )
            row = cursor.fetchone()
            assert row is not None
            assert row["file_type"] == "image"
    
    def test_update_invalid_file_type(self, state_manager, temp_file, test_folder):
        """Test updating with invalid file type raises error."""
        with pytest.raises(ValueError, match="Invalid file_type"):
            state_manager.update_file_state(temp_file, test_folder, "invalid")
    
    def test_update_invalid_folder_id(self, state_manager, temp_file):
        """Test updating with invalid folder_id raises error."""
        with pytest.raises(ValueError, match="Invalid folder_id"):
            state_manager.update_file_state(temp_file, 99999, "text")
    
    def test_update_nonexistent_file(self, state_manager, test_folder):
        """Test updating nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            state_manager.update_file_state("/nonexistent/file.txt", test_folder, "text")
    
    def test_update_stores_correct_metadata(self, state_manager, temp_file, test_folder):
        """Test that update stores correct file metadata."""
        # Get file info before update
        path = Path(temp_file)
        expected_mtime = datetime.fromtimestamp(path.stat().st_mtime)
        expected_hash = state_manager.compute_file_hash(temp_file)
        
        # Update state
        state_manager.update_file_state(temp_file, test_folder, "text")
        
        # Verify stored metadata
        with state_manager.db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT file_hash, modified_at, folder_id, file_type 
                FROM processed_files 
                WHERE file_path = ?
                """,
                (str(path.absolute()),)
            )
            row = cursor.fetchone()
            
            assert row is not None
            assert row["file_hash"] == expected_hash
            assert row["folder_id"] == test_folder
            assert row["file_type"] == "text"
            
            # Check timestamp is close (within 1 second)
            stored_mtime = datetime.fromisoformat(row["modified_at"])
            time_diff = abs((stored_mtime - expected_mtime).total_seconds())
            assert time_diff < 1.0


class TestIntegration:
    """Integration tests for processing state workflow."""
    
    def test_full_workflow_new_file(self, state_manager, temp_file, test_folder):
        """Test complete workflow: check new file, process, check again."""
        # Check initial state
        assert state_manager.check_file_state(temp_file) == "new"
        
        # Process file
        state_manager.update_file_state(temp_file, test_folder, "text")
        
        # Check state after processing
        assert state_manager.check_file_state(temp_file) == "unchanged"
    
    def test_full_workflow_modified_file(self, state_manager, temp_file, test_folder):
        """Test complete workflow: process, modify, detect change, reprocess."""
        # Initial processing
        state_manager.update_file_state(temp_file, test_folder, "text")
        assert state_manager.check_file_state(temp_file) == "unchanged"
        
        # Modify file
        time.sleep(0.01)
        with open(temp_file, 'a') as f:
            f.write("\nModified")
        
        # Detect modification
        assert state_manager.check_file_state(temp_file) == "modified"
        
        # Reprocess
        state_manager.update_file_state(temp_file, test_folder, "text")
        
        # Should be unchanged again
        assert state_manager.check_file_state(temp_file) == "unchanged"
    
    def test_multiple_files_same_folder(self, state_manager, test_folder):
        """Test processing multiple files in same folder."""
        files = []
        
        # Create multiple temp files
        for i in range(3):
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(f"Content {i}")
                files.append(f.name)
        
        try:
            # Process all files
            for file_path in files:
                assert state_manager.check_file_state(file_path) == "new"
                state_manager.update_file_state(file_path, test_folder, "text")
                assert state_manager.check_file_state(file_path) == "unchanged"
        finally:
            for file_path in files:
                if os.path.exists(file_path):
                    os.unlink(file_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
