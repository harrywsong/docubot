"""
Migration script to add user_id to folders table.

This script:
1. Adds user_id column to folders table
2. Updates the UNIQUE constraint to (path, user_id)
3. Assigns existing folders to user 1 (Harry) by default
"""

import sqlite3
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import Config

def migrate():
    """Run the migration."""
    db_path = Config.SQLITE_PATH
    
    print(f"Migrating database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Check if user_id column already exists
        cursor.execute("PRAGMA table_info(folders)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'user_id' in columns:
            print("✓ Migration already applied - user_id column exists")
            return
        
        print("Starting migration...")
        
        # Step 1: Create new folders table with user_id
        print("1. Creating new folders table...")
        cursor.execute("""
            CREATE TABLE folders_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(path, user_id)
            )
        """)
        
        # Step 2: Copy existing data, assigning all folders to user 1 (Harry)
        print("2. Copying existing folders (assigning to user 1 - Harry)...")
        cursor.execute("""
            INSERT INTO folders_new (id, path, user_id, added_at)
            SELECT id, path, 1, added_at
            FROM folders
        """)
        
        rows_copied = cursor.rowcount
        print(f"   Copied {rows_copied} folders")
        
        # Step 3: Drop old table
        print("3. Dropping old folders table...")
        cursor.execute("DROP TABLE folders")
        
        # Step 4: Rename new table
        print("4. Renaming new table...")
        cursor.execute("ALTER TABLE folders_new RENAME TO folders")
        
        # Step 5: Update processed_files if needed
        print("5. Checking processed_files table...")
        cursor.execute("PRAGMA table_info(processed_files)")
        pf_columns = [row[1] for row in cursor.fetchall()]
        
        if 'user_id' not in pf_columns:
            print("   Adding user_id to processed_files...")
            # This is more complex - need to recreate table
            cursor.execute("""
                CREATE TABLE processed_files_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    folder_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    file_hash TEXT NOT NULL,
                    modified_at TIMESTAMP NOT NULL,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_type TEXT NOT NULL,
                    FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(file_path, user_id)
                )
            """)
            
            cursor.execute("""
                INSERT INTO processed_files_new 
                (id, file_path, folder_id, user_id, file_hash, modified_at, processed_at, file_type)
                SELECT id, file_path, folder_id, 1, file_hash, modified_at, processed_at, file_type
                FROM processed_files
            """)
            
            cursor.execute("DROP TABLE processed_files")
            cursor.execute("ALTER TABLE processed_files_new RENAME TO processed_files")
            
            # Recreate index
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_processed_files_path 
                ON processed_files(file_path, user_id)
            """)
            
            print("   ✓ Updated processed_files table")
        else:
            print("   ✓ processed_files already has user_id")
        
        # Commit changes
        conn.commit()
        
        print("\n✅ Migration completed successfully!")
        print("\nSummary:")
        print(f"  - Folders table updated with user_id column")
        print(f"  - {rows_copied} existing folders assigned to user 1 (Harry)")
        print(f"  - UNIQUE constraint updated to (path, user_id)")
        print("\nNote: All existing folders are now owned by Harry (user_id=1)")
        print("You can reassign folders to other users through the UI")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
