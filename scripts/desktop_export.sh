#!/bin/bash
# Desktop Export Script
# Run this on your desktop PC to process documents and create export package

set -e

echo "=========================================="
echo "Desktop-Pi RAG Pipeline - Export Script"
echo "=========================================="
echo ""

# Configuration
DESKTOP_URL="http://localhost:8000"
PI_HOST="${PI_HOST:-pi@raspberrypi.local}"
EXPORT_TYPE="${1:-full}"  # full or incremental

# Check if server is running
echo "Checking if server is running..."
if ! curl -s "$DESKTOP_URL/api/health" > /dev/null 2>&1; then
    echo "Error: Server is not running at $DESKTOP_URL"
    echo "Start it with: python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000"
    exit 1
fi
echo "✓ Server is running"
echo ""

# Step 1: Process documents
echo "Step 1: Processing documents..."
curl -X POST "$DESKTOP_URL/api/process" -s | jq '.'
echo ""

# Wait for processing to complete
echo "Waiting for processing to complete (10 seconds)..."
sleep 10
echo ""

# Step 2: Validate processing
echo "Step 2: Validating processing..."
VALIDATION=$(curl -s "$DESKTOP_URL/api/processing/report")
echo "$VALIDATION" | jq '.'

# Check if validation passed
VALIDATION_PASSED=$(echo "$VALIDATION" | jq -r '.validation_passed')
if [ "$VALIDATION_PASSED" != "true" ]; then
    echo ""
    echo "⚠ Warning: Validation failed. Check the report above."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo "✓ Validation passed"
echo ""

# Step 3: Create export
echo "Step 3: Creating export package..."
if [ "$EXPORT_TYPE" = "incremental" ]; then
    echo "Creating incremental export..."
    EXPORT_RESULT=$(curl -X POST "$DESKTOP_URL/api/export" \
        -H "Content-Type: application/json" \
        -d '{"incremental": true}' -s)
else
    echo "Creating full export..."
    EXPORT_RESULT=$(curl -X POST "$DESKTOP_URL/api/export" \
        -H "Content-Type: application/json" \
        -d '{"incremental": false}' -s)
fi

echo "$EXPORT_RESULT" | jq '.'

# Extract archive path
ARCHIVE_PATH=$(echo "$EXPORT_RESULT" | jq -r '.archive_path')
SUCCESS=$(echo "$EXPORT_RESULT" | jq -r '.success')

if [ "$SUCCESS" != "true" ]; then
    echo ""
    echo "✗ Export failed. Check the errors above."
    exit 1
fi

echo "✓ Export created: $ARCHIVE_PATH"
echo ""

# Step 4: Transfer to Pi
echo "Step 4: Transferring to Raspberry Pi..."
echo "Target: $PI_HOST"
echo ""

read -p "Transfer now? (Y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo ""
    echo "Skipping transfer. To transfer manually:"
    echo "  scp $ARCHIVE_PATH $PI_HOST:~/"
    echo "  or"
    echo "  rsync -avz --progress $ARCHIVE_PATH $PI_HOST:~/"
    exit 0
fi

echo "Transferring with rsync..."
rsync -avz --progress "$ARCHIVE_PATH" "$PI_HOST:~/"

echo ""
echo "=========================================="
echo "✓ Export Complete!"
echo "=========================================="
echo ""
echo "Archive: $ARCHIVE_PATH"
echo "Transferred to: $PI_HOST:~/"
echo ""
echo "Next steps on Raspberry Pi:"
echo "  1. SSH into Pi: ssh $PI_HOST"
echo "  2. Extract: tar -xzf $(basename $ARCHIVE_PATH)"
echo "  3. Run setup script: cd $(basename $ARCHIVE_PATH .tar.gz) && ./setup_pi.sh"
echo ""
