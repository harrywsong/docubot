"""Clear all data - vector store and processing state."""
import sys
sys.path.insert(0, '.')

from backend.config import Config
from backend.database import DatabaseManager
from backend.vector_store import VectorStore

print("Clearing all data for a clean slate...\n")

# Clear vector store
print("1. Clearing vector store...")
vs = VectorStore(Config.CHROMADB_PATH)
stats_before = vs.get_stats()
print(f"   Vector store has {stats_before['total_chunks']} chunks")
vs.reset()
stats_after = vs.get_stats()
print(f"   ✓ Vector store cleared. Now has {stats_after['total_chunks']} chunks\n")

# Clear processing state
print("2. Clearing processing state...")
db = DatabaseManager(Config.SQLITE_PATH)
with db.transaction() as conn:
    cursor = conn.execute("SELECT COUNT(*) FROM processed_files")
    count = cursor.fetchone()[0]
    print(f"   Found {count} files in processing state")
    
    if count > 0:
        conn.execute("DELETE FROM processed_files")
        print(f"   ✓ Cleared processing state for {count} files\n")
    else:
        print("   Processing state already empty\n")

print("✓ All data cleared! Ready for a clean start.")
print("\nGo to the UI and click 'Process Documents' to process all files fresh.")
