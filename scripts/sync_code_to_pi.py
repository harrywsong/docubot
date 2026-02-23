"""
Sync updated code files to Raspberry Pi.
"""
import subprocess
import sys
import os
from backend.config import Config

print("=== SYNCING CODE TO RASPBERRY PI ===\n")

# Check configuration
if not Config.PI_HOST:
    print("❌ ERROR: PI_HOST not configured in .env")
    sys.exit(1)

# Get current directory and convert to WSL path
current_dir = os.getcwd()
wsl_path = current_dir.replace('\\', '/').replace('E:', '/mnt/e').replace('C:', '/mnt/c')

print(f"Target: {Config.PI_HOST}:~/docubot/")
print(f"Source: {wsl_path}/\n")

# Sync backend directory
print("Syncing backend directory...")
try:
    result = subprocess.run(
        [
            "wsl", "-d", "Ubuntu", "--", "rsync", "-avz",
            "--exclude", "__pycache__",
            "--exclude", "*.pyc",
            f"{wsl_path}/backend/",
            f"{Config.PI_HOST}:~/docubot/backend/"
        ],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    if result.returncode == 0:
        print("✓ Backend synced successfully")
    else:
        print(f"❌ Backend sync failed: {result.stderr}")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Backend sync error: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("✓✓✓ CODE SYNC COMPLETE ✓✓✓")
print("="*60)
print("\nNext steps:")
print("1. SSH to Pi: wsl -d Ubuntu -- ssh hws@192.168.1.139")
print("2. Restart backend: cd ~/docubot && pkill -f 'python.*main.py' && ./scripts/start_pi.sh")
print("3. Test query: 2월에 코스트코에 총 얼마나 썼어?")
