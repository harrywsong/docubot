"""Check which folders are being watched and what files they contain."""
import sys
sys.path.insert(0, '.')

from backend.config import Config
from backend.database import DatabaseManager
from backend.folder_manager import FolderManager

# Get database manager
db = DatabaseManager(Config.SQLITE_PATH)

# Get folder manager
fm = FolderManager(db)

# List all watched folders
folders = fm.list_folders()

print(f"Found {len(folders)} watched folders:\n")

for folder in folders:
    print(f"Folder ID: {folder.id}")
    print(f"Path: {folder.path}")
    print(f"Added: {folder.added_at}")
    
    # Scan folder
    text_files, image_files = fm.scan_folder(folder.path)
    print(f"  Text files: {len(text_files)}")
    print(f"  Image files: {len(image_files)}")
    print(f"  Total: {len(text_files) + len(image_files)}")
    print()
