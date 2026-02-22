# Raspberry Pi Sync Setup Guide

This guide explains how to set up automatic syncing of processed documents from your desktop PC to your Raspberry Pi.

## Overview

The sync functionality allows you to:
1. Process documents on your powerful desktop PC
2. Sync the processed data (vector store + database) to your Raspberry Pi
3. Query documents from the Raspberry Pi without needing to reprocess

## Prerequisites

### On Windows PC:
- Git Bash, WSL, or Cygwin (for rsync command)
- SSH access to your Raspberry Pi

### On Raspberry Pi:
- SSH server enabled
- DocuBot installed at `/home/pi/docubot/`

## Setup Steps

### 1. Install rsync on Windows

**Option A: Git Bash (Recommended)**
- Install [Git for Windows](https://git-scm.com/download/win)
- rsync comes bundled with Git Bash

**Option B: WSL (Windows Subsystem for Linux)**
```bash
wsl --install
# After WSL is installed:
sudo apt update
sudo apt install rsync
```

**Option C: Cygwin**
- Download from [cygwin.com](https://www.cygwin.com/)
- Select rsync during installation

### 2. Set Up SSH Key Authentication (No Password Prompts)

This allows automatic syncing without entering passwords.

**On your Windows PC (in Git Bash or WSL):**

```bash
# Generate SSH key if you don't have one
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# Copy your public key to the Raspberry Pi
ssh-copy-id pi@raspberrypi.local

# Test the connection (should not ask for password)
ssh pi@raspberrypi.local
```

If `ssh-copy-id` doesn't work, manually copy the key:

```bash
# Display your public key
cat ~/.ssh/id_rsa.pub

# SSH into Pi and add the key
ssh pi@raspberrypi.local
mkdir -p ~/.ssh
echo "YOUR_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
exit
```

### 3. Configure Pi Settings

Create a `.env` file in your project root (copy from `.env.example`):

```bash
# Raspberry Pi Sync Configuration
PI_HOST=pi@raspberrypi.local
PI_PATH=/home/pi/docubot/data/
```

**Customize these values:**
- `PI_HOST`: SSH connection string (user@hostname or user@ip_address)
  - Examples: `pi@192.168.1.100`, `pi@raspberrypi.local`
- `PI_PATH`: Absolute path to DocuBot data directory on Pi
  - Default: `/home/pi/docubot/data/`

### 4. Test the Sync

**From the UI:**
1. Start the DocuBot application on your PC
2. Login as any user
3. Go to the "Documents" tab
4. Click "Sync to Raspberry Pi"
5. Check the toast notification for success/error

**From Command Line (Alternative):**

```bash
# Test rsync manually
rsync -avz --progress ./data/chromadb/ pi@raspberrypi.local:/home/pi/docubot/data/chromadb/
rsync -avz --progress ./data/app.db pi@raspberrypi.local:/home/pi/docubot/data/
```

## Usage Workflow

### Typical Daily Workflow:

1. **On Desktop PC:**
   - Start DocuBot
   - Add folders with documents
   - Click "Process All Folders"
   - Wait for processing to complete
   - Click "Sync to Raspberry Pi"

2. **On Raspberry Pi:**
   - Start DocuBot (or it's already running)
   - All processed documents are now available for querying
   - Users can chat and query their documents

### What Gets Synced:

- **ChromaDB Vector Store** (`data/chromadb/`)
  - All document embeddings
  - Vector indices
  
- **SQLite Database** (`data/app.db`)
  - User information
  - Folder configurations
  - Processing state
  - Conversation history

## Troubleshooting

### Error: "rsync not found"

**Solution:** Install rsync using one of the methods in Step 1.

### Error: "Permission denied (publickey)"

**Solution:** SSH key authentication not set up correctly.
```bash
# Re-run ssh-copy-id
ssh-copy-id pi@raspberrypi.local

# Or manually copy the key (see Step 2)
```

### Error: "Connection refused"

**Solutions:**
- Check if Pi is powered on and connected to network
- Verify hostname: `ping raspberrypi.local`
- Try using IP address instead: `PI_HOST=pi@192.168.1.100`
- Ensure SSH is enabled on Pi: `sudo systemctl status ssh`

### Error: "No such file or directory"

**Solution:** Create the data directory on Pi:
```bash
ssh pi@raspberrypi.local
mkdir -p /home/pi/docubot/data/chromadb
```

### Sync is Very Slow

**Solutions:**
- Use wired Ethernet instead of WiFi
- First sync is always slower (full copy)
- Subsequent syncs are incremental (only changed files)
- Check network speed: `iperf3` between PC and Pi

## Advanced Configuration

### Custom Sync Script

Create `scripts/sync_to_pi.sh` for manual syncing:

```bash
#!/bin/bash
PI_HOST="pi@raspberrypi.local"
PI_PATH="/home/pi/docubot/data/"

echo "Syncing ChromaDB..."
rsync -avz --progress ./data/chromadb/ "$PI_HOST:$PI_PATH/chromadb/"

echo "Syncing database..."
rsync -avz --progress ./data/app.db "$PI_HOST:$PI_PATH/"

echo "Sync complete!"
```

Make it executable:
```bash
chmod +x scripts/sync_to_pi.sh
```

### Automatic Sync After Processing

To automatically sync after processing completes, modify `backend/api.py`:

```python
# In run_document_processing() function, after processing completes:
if Config.AUTO_SYNC_TO_PI:
    try:
        await sync_to_pi_async()
    except Exception as e:
        logger.error(f"Auto-sync failed: {e}")
```

Add to `.env`:
```bash
AUTO_SYNC_TO_PI=true
```

## Security Notes

- SSH keys provide secure, password-less authentication
- Keep your private key (`~/.ssh/id_rsa`) secure
- Never share your private key
- Use strong passwords for your Pi user account
- Consider using SSH key passphrases for extra security

## Performance Tips

1. **First Sync:** Will take longer (full copy of all data)
2. **Incremental Syncs:** Much faster (only changed files)
3. **Network:** Use Gigabit Ethernet for best performance
4. **Compression:** rsync uses compression by default (`-z` flag)
5. **Timing:** Sync during off-hours if you have large datasets

## Monitoring Sync Progress

The sync button shows:
- "Syncing..." with spinner during sync
- Success toast notification when complete
- Error toast with details if sync fails

Check backend logs for detailed sync information:
```bash
# View logs in real-time
tail -f logs/app.log
```

## Alternative: Manual Sync Methods

### USB Drive Method:
1. Copy `data/` folder to USB drive
2. Plug USB into Pi
3. Copy from USB to `/home/pi/docubot/data/`

### Network Share Method:
1. Set up SMB/NFS share on your network
2. Mount share on both PC and Pi
3. Configure both to use shared `data/` directory

### SCP Method (without rsync):
```bash
scp -r ./data/chromadb pi@raspberrypi.local:/home/pi/docubot/data/
scp ./data/app.db pi@raspberrypi.local:/home/pi/docubot/data/
```

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review backend logs for error details
3. Test SSH connection manually: `ssh pi@raspberrypi.local`
4. Verify rsync is installed: `rsync --version`
