#!/bin/bash

# Common Ingest API Stop Script
# Stops the FastAPI server started by start_api.sh

echo "Stopping Common Ingest API Server..."
echo "===================================="

PID_FILE="/tmp/common_ingest_api.pid"

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo "No PID file found at $PID_FILE"
    echo "The server might not be running or was started differently"
    
    # Try to find uvicorn process anyway
    echo ""
    echo "Searching for uvicorn processes..."
    UVICORN_PIDS=$(pgrep -f "uvicorn common_ingest.api.app:app")
    
    if [ -z "$UVICORN_PIDS" ]; then
        echo "No uvicorn processes found for common_ingest.api"
        exit 0
    else
        echo "Found uvicorn process(es): $UVICORN_PIDS"
        read -p "Do you want to stop these processes? (y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kill $UVICORN_PIDS
            echo "✓ Stopped uvicorn processes"
        fi
        exit 0
    fi
fi

# Read PID from file
PID=$(cat "$PID_FILE")

# Check if process is running
if ! kill -0 "$PID" 2>/dev/null; then
    echo "Process $PID is not running"
    rm -f "$PID_FILE"
    exit 0
fi

# Try graceful shutdown first (SIGTERM)
echo "Sending SIGTERM to process $PID..."
kill "$PID"

# Wait up to 5 seconds for graceful shutdown
COUNTER=0
while [ $COUNTER -lt 5 ]; do
    if ! kill -0 "$PID" 2>/dev/null; then
        echo "✓ Server stopped gracefully"
        rm -f "$PID_FILE"
        exit 0
    fi
    sleep 1
    COUNTER=$((COUNTER + 1))
    echo "  Waiting for shutdown... ($COUNTER/5)"
done

# Force kill if still running (SIGKILL)
echo "Process did not stop gracefully, forcing shutdown..."
kill -9 "$PID" 2>/dev/null

# Final check
if kill -0 "$PID" 2>/dev/null; then
    echo "✗ Failed to stop server (PID: $PID)"
    echo "You may need to manually kill the process"
    exit 1
else
    echo "✓ Server forcefully stopped"
    rm -f "$PID_FILE"
fi

# Clean up any remaining uvicorn workers
echo "Cleaning up any remaining workers..."
pkill -f "uvicorn common_ingest.api.app:app" 2>/dev/null

echo "✓ Cleanup complete"