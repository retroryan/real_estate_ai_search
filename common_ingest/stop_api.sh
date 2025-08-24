#!/bin/bash

# Common Ingest API Stop Script - Simple version for demos
# Stops the FastAPI server

echo "Stopping Common Ingest API Server..."

PID_FILE="/tmp/common_ingest_api.pid"

# Kill using PID file if it exists
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    kill "$PID" 2>/dev/null
    rm -f "$PID_FILE"
fi

# Kill any uvicorn processes for common_ingest
pkill -f "uvicorn common_ingest.api.app:app" 2>/dev/null

echo "✓ Server stopped"