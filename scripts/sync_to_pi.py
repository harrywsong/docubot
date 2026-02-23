"""
Sync updated ChromaDB and database to Raspberry Pi.
"""
import subprocess
import sys
import os
from backend.config import Config

print("=== SYNCING TO RASPBERRY PI ===\n")

# Check configuration
if not Config.PI_HOST or not Config.PI_PATH:
    print("❌ ERROR: PI_HOST or PI_PATH not configured in .env")
    print(f"   PI_HOST: {Config.PI_HOST}")
    print(f"   PI_PATH: {Config.PI_PATH}")
    sys.exit(1)

print(f"Target: {Config.PI_HOST}:{Config.PI_PATH}")

# Get current directory and convert to WSL path
current_dir = os.getcwd()
# Convert Windows path to WSL path (E:\codingprojects\docubot -> /mnt/e/codingprojects/docubot)
wsl_path = current_dir.replace('\\', '/').replace('E:', '/mnt/e').replace('C:', '/mnt/c')
print(f"Source: {wsl_path}/data/\n")

# Sync ChromaDB
print("Syncing ChromaDB vector store...")
try:
    result = subprocess.run(
        [
            "wsl", "-d", "Ubuntu", "--", "rsync", "-avz", "--delete",
            f"{wsl_path}/data/chromadb/",
            f"{Config.PI_HOST}:{Config.PI_PATH}chromadb/"
        ],
        capture_output=True,
        text=True,
        timeout=300
    )
    
    if result.returncode == 0:
        print("✓ ChromaDB synced successfully")
    else:
        print(f"❌ ChromaDB sync failed: {result.stderr}")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ ChromaDB sync error: {e}")
    sys.exit(1)

# Sync SQLite database
print("\nSyncing SQLite database...")
try:
    result = subprocess.run(
        [
            "wsl", "-d", "Ubuntu", "--", "rsync", "-avz",
            f"{wsl_path}/data/app.db",
            f"{Config.PI_HOST}:{Config.PI_PATH}"
        ],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    if result.returncode == 0:
        print("✓ Database synced successfully")
    else:
        print(f"❌ Database sync failed: {result.stderr}")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Database sync error: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("✓✓✓ SYNC COMPLETE ✓✓✓")
print("="*60)
print("\nNext steps:")
print("1. SSH to Pi: wsl -d Ubuntu -- ssh hws@192.168.1.139")
print("2. Restart backend: cd ~/docubot && ./scripts/start_pi.sh")
print("3. Test query: 2월에 코스트코에 총 얼마나 썼어?")
