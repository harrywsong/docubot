"""Force reprocessing of all documents by clearing processing state."""
import sys
sys.path.insert(0, '.')

from backend.config import Config
from backend.database import DatabaseManager

# Get database manager with correct path
db = DatabaseManager(Config.SQLITE_PATH)

print("Clearing processing state to force reprocessing...")

# Clear all processing state
with db.transaction() as conn:
    cursor = conn.execute("SELECT COUNT(*) FROM processed_files")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("No files in processing state.")
    else:
        print(f"Found {count} files in processing state")
        conn.execute("DELETE FROM processed_files")
        print(f"✓ Cleared processing state for {count} files")

print("\nAll files will be reprocessed on next document processing run.")
print("Go to the UI and click 'Process Documents' to reprocess everything.")
