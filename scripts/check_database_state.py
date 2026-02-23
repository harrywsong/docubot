"""
Check the current state of the database and ChromaDB.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import DatabaseManager
from backend.vector_store import get_vector_store
from backend.config import Config

def main():
    print("=" * 60)
    print("Database State Check")
    print("=" * 60)
    print()
    
    # Initialize database (use the correct path from Config)
    db = DatabaseManager(db_path=Config.SQLITE_PATH)
    
    # Check folders
    print("FOLDERS:")
    print("-" * 60)
    with db.transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, path, user_id FROM folders")
        folders = cursor.fetchall()
        
        if folders:
            for row in folders:
                print(f"  ID: {row['id']}")
                print(f"  Path: {row['path']}")
                print(f"  User ID: {row['user_id']}")
                print()
        else:
            print("  No folders found")
    print()
    
    # Check processed files
    print("PROCESSED FILES:")
    print("-" * 60)
    with db.transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM processed_files")
        file_count = cursor.fetchone()['count']
        print(f"  Total files: {file_count}")
        
        if file_count > 0:
            cursor.execute("""
                SELECT file_path, user_id, file_type
                FROM processed_files 
                ORDER BY processed_at DESC 
                LIMIT 10
            """)
            files = cursor.fetchall()
            print()
            print("  Recent files:")
            for row in files:
                print(f"    - {row['file_path']}")
                print(f"      User: {row['user_id']}, Type: {row['file_type']}")
    print()
    
    # Check ChromaDB
    print("CHROMADB:")
    print("-" * 60)
    vector_store = get_vector_store()
    collection = vector_store.collection
    total_chunks = collection.count()
    print(f"  Total chunks: {total_chunks}")
    
    if total_chunks > 0:
        # Get sample chunks
        results = collection.get(limit=5, include=["metadatas"])
        print()
        print("  Sample chunks:")
        for i, metadata in enumerate(results['metadatas']):
            print(f"    Chunk {i+1}:")
            print(f"      Filename: {metadata.get('filename', 'N/A')}")
            print(f"      User ID: {metadata.get('user_id', 'N/A')}")
            print(f"      Chunk index: {metadata.get('chunk_index', 'N/A')}")
    print()
    
    # Check by user
    print("CHUNKS BY USER:")
    print("-" * 60)
    for user_id in [1, 2, 3]:
        try:
            user_results = collection.get(
                where={"user_id": user_id},
                limit=1000
            )
            count = len(user_results['ids'])
            print(f"  User {user_id}: {count} chunks")
        except Exception as e:
            print(f"  User {user_id}: Error - {e}")
    print()
    
    print("=" * 60)

if __name__ == "__main__":
    main()
