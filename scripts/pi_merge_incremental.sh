#!/bin/bash
# Raspberry Pi Incremental Merge Script
# Run this on your Pi after transferring an incremental export package

set -e

echo "=========================================="
echo "Desktop-Pi RAG Pipeline - Incremental Merge"
echo "=========================================="
echo ""

# Configuration
APP_DIR="${APP_DIR:-$HOME/rag-chatbot}"
DATA_DIR="$APP_DIR/data"
PI_URL="http://localhost:8000"

# Check if we're in an incremental export package directory
if [ ! -f "manifest.json" ]; then
    echo "Error: manifest.json not found in current directory"
    echo "Please run this script from the extracted incremental export package directory"
    exit 1
fi

# Verify this is an incremental package
IS_INCREMENTAL=$(jq -r '.incremental.is_incremental' manifest.json)
if [ "$IS_INCREMENTAL" != "true" ]; then
    echo "Error: This is not an incremental export package"
    echo "For full exports, use the pi_setup.sh script instead"
    exit 1
fi

echo "Found incremental export package"
SINCE_TIMESTAMP=$(jq -r '.incremental.since_timestamp' manifest.json)
NEW_CHUNKS=$(jq -r '.statistics.new_chunks // .statistics.total_chunks' manifest.json)
echo "  Since: $SINCE_TIMESTAMP"
echo "  New chunks: $NEW_CHUNKS"
echo ""

# Step 1: Check if server is running
echo "Step 1: Checking server status..."
if curl -s "$PI_URL/api/health" > /dev/null 2>&1; then
    echo "⚠ Server is currently running"
    read -p "Stop server to perform merge? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo "Stopping server..."
        if systemctl is-active --quiet rag-chatbot; then
            sudo systemctl stop rag-chatbot
            echo "✓ Stopped systemd service"
        else
            pkill -f "uvicorn backend.api:app" || true
            echo "✓ Stopped server process"
        fi
        sleep 2
    else
        echo "Cannot merge while server is running. Exiting."
        exit 1
    fi
else
    echo "✓ Server is not running"
fi
echo ""

# Step 2: Backup current data (optional)
echo "Step 2: Backup current data (optional)..."
read -p "Create backup before merge? (Y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    BACKUP_DIR="$DATA_DIR/backup_$(date +%Y%m%d_%H%M%S)"
    echo "Creating backup at $BACKUP_DIR..."
    mkdir -p "$BACKUP_DIR"
    cp -r "$DATA_DIR/chromadb" "$BACKUP_DIR/" 2>/dev/null || true
    cp "$DATA_DIR/app.db" "$BACKUP_DIR/" 2>/dev/null || true
    cp "$DATA_DIR/manifest.json" "$BACKUP_DIR/" 2>/dev/null || true
    echo "✓ Backup created"
fi
echo ""

# Step 3: Validate compatibility
echo "Step 3: Validating compatibility..."

# Check embedding dimensions match
PACKAGE_DIM=$(jq -r '.pi_requirements.embedding_dimension' manifest.json)
CURRENT_DIM=$(jq -r '.pi_requirements.embedding_dimension' "$DATA_DIR/manifest.json" 2>/dev/null || echo "unknown")

if [ "$CURRENT_DIM" != "unknown" ] && [ "$PACKAGE_DIM" != "$CURRENT_DIM" ]; then
    echo "✗ Error: Embedding dimension mismatch"
    echo "  Current: $CURRENT_DIM"
    echo "  Package: $PACKAGE_DIM"
    echo "Cannot merge incompatible data"
    exit 1
fi
echo "✓ Compatibility check passed"
echo ""

# Step 4: Merge data using Python script
echo "Step 4: Merging incremental data..."

# Create a temporary Python script to perform the merge
MERGE_SCRIPT=$(mktemp)
cat > "$MERGE_SCRIPT" <<'PYTHON_EOF'
import sys
import os
sys.path.insert(0, os.path.expanduser('~/rag-chatbot'))

from backend.config import Config
from backend.vector_store import VectorStore
from backend.database import DatabaseManager
from backend.incremental_merger import IncrementalMerger

# Initialize components
config = Config()
vector_store = VectorStore(persist_directory=config.CHROMADB_PATH, read_only=False)
vector_store.initialize()
db_manager = DatabaseManager(db_path=config.SQLITE_PATH)

# Create merger
merger = IncrementalMerger(vector_store, db_manager)

# Perform merge
package_path = sys.argv[1]
result = merger.merge_incremental_package(package_path)

# Print results
print(f"\nMerge Results:")
print(f"  Success: {result.success}")
print(f"  Merged chunks: {result.merged_chunks}")
print(f"  Updated chunks: {result.updated_chunks}")
print(f"  Deleted chunks: {result.deleted_chunks}")
print(f"  Time: {result.merge_time_seconds:.2f}s")

if result.errors:
    print(f"\nErrors:")
    for error in result.errors:
        print(f"  - {error}")
    sys.exit(1)
else:
    print("\n✓ Merge completed successfully")
PYTHON_EOF

# Run the merge
python3 "$MERGE_SCRIPT" "$(pwd)"
MERGE_STATUS=$?
rm "$MERGE_SCRIPT"

if [ $MERGE_STATUS -ne 0 ]; then
    echo ""
    echo "✗ Merge failed"
    if [ -d "$BACKUP_DIR" ]; then
        echo ""
        echo "To restore from backup:"
        echo "  rm -rf $DATA_DIR/chromadb"
        echo "  cp -r $BACKUP_DIR/chromadb $DATA_DIR/"
        echo "  cp $BACKUP_DIR/app.db $DATA_DIR/"
        echo "  cp $BACKUP_DIR/manifest.json $DATA_DIR/"
    fi
    exit 1
fi
echo ""

# Step 5: Update manifest
echo "Step 5: Updating manifest..."
cp manifest.json "$DATA_DIR/manifest.json"
echo "✓ Manifest updated"
echo ""

# Step 6: Restart server
echo "Step 6: Restarting server..."
read -p "Start server now? (Y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    if systemctl list-unit-files | grep -q rag-chatbot.service; then
        sudo systemctl start rag-chatbot
        echo "✓ Started systemd service"
        echo ""
        echo "Check status: sudo systemctl status rag-chatbot"
        echo "View logs: sudo journalctl -u rag-chatbot -f"
    else
        cd "$APP_DIR"
        echo "Starting server..."
        echo "Access at: http://$(hostname -I | awk '{print $1}'):8000"
        echo ""
        python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000 &
        SERVER_PID=$!
        echo "✓ Server started (PID: $SERVER_PID)"
    fi
fi
echo ""

echo "=========================================="
echo "✓ Incremental Merge Complete!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  New chunks added: $NEW_CHUNKS"
echo "  Data directory: $DATA_DIR"
if [ -d "$BACKUP_DIR" ]; then
    echo "  Backup location: $BACKUP_DIR"
fi
echo ""
echo "The system is now serving queries with updated data."
echo ""
