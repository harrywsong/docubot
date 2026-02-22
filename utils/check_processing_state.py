"""Check which files are in the processing state."""
import sys
sys.path.insert(0, '.')

from backend.config import Config
from backend.database import DatabaseManager

# Get database manager
db = DatabaseManager(Config.SQLITE_PATH)

# Get all processed files
with db.transaction() as conn:
    cursor = conn.execute("""
        SELECT file_path, file_type, processed_at 
        FROM processed_files 
        ORDER BY processed_at DESC
    """)
    rows = cursor.fetchall()

print(f"Found {len(rows)} files in processing state:\n")

for row in rows:
    print(f"File: {row['file_path']}")
    print(f"Type: {row['file_type']}")
    print(f"Processed: {row['processed_at']}")
    print()
