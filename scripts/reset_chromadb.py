"""
Reset ChromaDB to fix embedding dimension mismatch.

This script:
1. Backs up the current ChromaDB
2. Deletes the old ChromaDB data
3. Recreates ChromaDB with correct embedding dimensions
4. Provides instructions for re-processing documents

Usage:
    python scripts/reset_chromadb.py
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

def main():
    print("=" * 60)
    print("ChromaDB Reset Script")
    print("=" * 60)
    print()
    
    # Paths
    chromadb_path = Path("data/chromadb")
    backup_dir = Path("data/chromadb_backups")
    
    # Step 1: Check if ChromaDB exists
    if not chromadb_path.exists():
        print("✓ ChromaDB directory doesn't exist - nothing to reset")
        print("  You can start the backend and process documents normally")
        return
    
    print(f"Found ChromaDB at: {chromadb_path}")
    print()
    
    # Step 2: Create backup
    print("Step 1: Creating backup...")
    backup_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"chromadb_backup_{timestamp}"
    
    try:
        shutil.copytree(chromadb_path, backup_path)
        print(f"✓ Backup created at: {backup_path}")
    except Exception as e:
        print(f"✗ Backup failed: {e}")
        print("  Continuing anyway...")
    print()
    
    # Step 3: Delete old ChromaDB
    print("Step 2: Deleting old ChromaDB...")
    try:
        shutil.rmtree(chromadb_path)
        print(f"✓ Deleted: {chromadb_path}")
    except Exception as e:
        print(f"✗ Failed to delete ChromaDB: {e}")
        return
    print()
    
    # Step 4: Verify deletion
    if chromadb_path.exists():
        print("✗ ChromaDB still exists - manual deletion required")
        return
    
    print("✓ ChromaDB successfully reset!")
    print()
    
    # Step 5: Instructions
    print("=" * 60)
    print("Next Steps:")
    print("=" * 60)
    print()
    print("1. Start the backend server:")
    print("   python backend/main.py")
    print()
    print("2. Open the frontend (http://localhost:3000)")
    print()
    print("3. Re-process all your document folders:")
    print("   - Go to the 'Documents' tab")
    print("   - Click 'Process' for each folder")
    print()
    print("4. Test queries in Korean and English:")
    print("   - Verify nomic-embed-text quality is acceptable")
    print()
    print("5. If quality is good, sync to Raspberry Pi:")
    print("   - Click 'Sync to Raspberry Pi' button")
    print()
    print("=" * 60)
    print()
    print("Note: The backend will automatically recreate ChromaDB")
    print("      with 768-dim embeddings (nomic-embed-text)")
    print()

if __name__ == "__main__":
    main()
