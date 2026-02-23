"""Clear processed files records to force reprocessing."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import DatabaseManager
from backend.config import Config

db = DatabaseManager(db_path=Config.SQLITE_PATH)

with db.transaction() as conn:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM processed_files")
    count = cursor.rowcount
    print(f"Deleted {count} processed file records")

print("Done! Files will be reprocessed on next run.")
