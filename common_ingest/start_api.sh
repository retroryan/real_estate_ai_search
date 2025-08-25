#!/bin/bash

# Common Ingest API Start Script - Simple version for demos
# Automatically stops any existing server and starts a new one
# Can be run from any directory - will automatically change to common_ingest/

# Get the directory where this script is located (common_ingest directory)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Change to the common_ingest directory for all operations
cd "$SCRIPT_DIR" || {
    echo "Error: Cannot change to directory $SCRIPT_DIR"
    exit 1
}

# First, stop any existing server
echo "Stopping any existing server..."
PID_FILE="/tmp/common_ingest_api.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ ! -z "$PID" ]; then
        kill "$PID" 2>/dev/null
    fi
    rm -f "$PID_FILE"
fi
pkill -f "uvicorn common_ingest.api.app:app" 2>/dev/null
sleep 2

echo "Starting Common Ingest API Server..."
echo "=================================="
echo "Working directory: $(pwd)"
echo ""

# Check if uvicorn is installed
if ! command -v uvicorn &> /dev/null; then
    echo "Error: uvicorn is not installed"
    echo "Please install with: pip install uvicorn"
    exit 1
fi

# Set Python path to ensure module can be imported
export PYTHONPATH="${PYTHONPATH}:$(dirname $(pwd))"

# Read configuration from config.yaml using Python
CONFIG_OUTPUT=$(python -c "
import sys
import os
from pathlib import Path
# Add parent directory to path for imports
sys.path.insert(0, str(Path.cwd().parent))
try:
    from common_ingest.utils.config import get_settings
    settings = get_settings()
    print(f'{settings.api.host}|{settings.api.port}|{settings.logging.level}')
except Exception as e:
    # Fallback to defaults
    print('0.0.0.0|8000|info')
" 2>/dev/null)

# Check if configuration was read successfully
if [ -z "$CONFIG_OUTPUT" ] || echo "$CONFIG_OUTPUT" | grep -q "WARNING\|ERROR\|Exception"; then
    echo "Note: Using default configuration"
    HOST="0.0.0.0"
    PORT="8000"
    LOG_LEVEL="info"
else
    IFS='|' read -r HOST PORT LOG_LEVEL <<< "$CONFIG_OUTPUT"
    # Ensure values are not empty and trim whitespace
    HOST=$(echo "${HOST:-0.0.0.0}" | xargs)
    PORT=$(echo "${PORT:-8000}" | xargs)
    LOG_LEVEL=$(echo "${LOG_LEVEL:-info}" | xargs)
fi

# Save PID for stop script
PID_FILE="/tmp/common_ingest_api.pid"

echo "Configuration (from config.yaml):"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Log Level: $LOG_LEVEL"
echo "  Config: common_ingest/config.yaml"
echo "  PID File: $PID_FILE"
echo ""

# Start uvicorn in background and save PID
echo "Starting server..."
nohup uvicorn common_ingest.api.app:app \
    --host "$HOST" \
    --port "$PORT" \
    --reload \
    --log-level "$LOG_LEVEL" \
    > /tmp/common_ingest_api.log 2>&1 &

# Save the PID
echo $! > "$PID_FILE"

# Wait a moment for server to start
sleep 2

# Check if server started successfully
if kill -0 $(cat "$PID_FILE") 2>/dev/null; then
    echo "✓ Server started successfully (PID: $(cat $PID_FILE))"
    echo ""
    echo "Access points:"
    echo "  API Root:        http://localhost:$PORT/"
    echo "  Interactive Docs: http://localhost:$PORT/docs"
    echo "  ReDoc:           http://localhost:$PORT/redoc"
    echo "  Health Check:    http://localhost:$PORT/api/v1/health"
    echo ""
    echo "Logs: tail -f /tmp/common_ingest_api.log"
    echo "Stop: ./stop_api.sh"
else
    echo "✗ Failed to start server"
    echo "Check logs: cat /tmp/common_ingest_api.log"
    rm -f "$PID_FILE"
    exit 1
fi