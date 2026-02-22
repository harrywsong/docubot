"""
Migration script to add multi-user support to existing database.

This script:
1. Creates users table
2. Creates default users (Harry, Ryan, Mom)
3. Adds user_id column to conversations and processed_files tables
4. Assigns all existing data to the first user (Harry)
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import Config

def migrate_database():
    """Run database migration to add multi-user support."""
    db_path = Config.SQLITE_PATH
    
    print(f"Migrating database at: {db_path}")
    
    # Backup database first
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Creating backup at: {backup_path}")
    
    import shutil
    shutil.copy2(db_path, backup_path)
    print("Backup created successfully")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Step 1: Create users table
        print("\n1. Creating users table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                profile_picture TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   Users table created")
        
        # Step 2: Create default users
        print("\n2. Creating default users...")
        now = datetime.now()
        default_users = [
            ("Harry", None),
            ("Ryan", None),
            ("Mom", None)
        ]
        
        for username, profile_picture in default_users:
            cursor.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,)
            )
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO users (username, profile_picture, created_at, last_active)
                    VALUES (?, ?, ?, ?)
                    """,
                    (username, profile_picture, now, now)
                )
                print(f"   Created user: {username}")
            else:
                print(f"   User already exists: {username}")
        
        # Get Harry's user_id (first user)
        cursor.execute("SELECT id FROM users WHERE username = 'Harry'")
        harry_id = cursor.fetchone()[0]
        print(f"   Harry's user_id: {harry_id}")
        
        # Step 3: Add user_id to conversations table
        print("\n3. Migrating conversations table...")
        
        # Check if user_id column already exists
        cursor.execute("PRAGMA table_info(conversations)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'user_id' not in columns:
            # Create new table with user_id
            cursor.execute("""
                CREATE TABLE conversations_new (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Copy data from old table, assigning all to Harry
            cursor.execute(f"""
                INSERT INTO conversations_new (id, user_id, title, created_at, updated_at)
                SELECT id, {harry_id}, title, created_at, updated_at
                FROM conversations
            """)
            
            # Drop old table and rename new one
            cursor.execute("DROP TABLE conversations")
            cursor.execute("ALTER TABLE conversations_new RENAME TO conversations")
            
            # Create index
            cursor.execute("""
                CREATE INDEX idx_conversations_user 
                ON conversations(user_id, updated_at)
            """)
            
            print("   Conversations table migrated")
        else:
            print("   Conversations table already has user_id column")
        
        # Step 4: Add user_id to processed_files table
        print("\n4. Migrating processed_files table...")
        
        # Check if user_id column already exists
        cursor.execute("PRAGMA table_info(processed_files)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'user_id' not in columns:
            # Create new table with user_id
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
            
            # Copy data from old table, assigning all to Harry
            cursor.execute(f"""
                INSERT INTO processed_files_new 
                (id, file_path, folder_id, user_id, file_hash, modified_at, processed_at, file_type)
                SELECT id, file_path, folder_id, {harry_id}, file_hash, modified_at, processed_at, file_type
                FROM processed_files
            """)
            
            # Drop old table and rename new one
            cursor.execute("DROP TABLE processed_files")
            cursor.execute("ALTER TABLE processed_files_new RENAME TO processed_files")
            
            # Create index
            cursor.execute("""
                CREATE INDEX idx_processed_files_path 
                ON processed_files(file_path, user_id)
            """)
            
            print("   Processed_files table migrated")
        else:
            print("   Processed_files table already has user_id column")
        
        # Commit changes
        conn.commit()
        print("\n✅ Migration completed successfully!")
        print(f"   Backup saved at: {backup_path}")
        print(f"   All existing data assigned to user: Harry (ID: {harry_id})")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        print(f"   Database restored from backup: {backup_path}")
        raise
    
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Multi-User Database Migration")
    print("=" * 60)
    
    response = input("\nThis will modify your database. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Migration cancelled")
        sys.exit(0)
    
    migrate_database()
    
    print("\n" + "=" * 60)
    print("Migration complete! You can now restart the backend.")
    print("=" * 60)
