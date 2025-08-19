#!/bin/bash
# Run wiki_summary with automatic virtual environment activation

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to script directory
cd "$SCRIPT_DIR"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating it now..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Run the module with all arguments passed to this script
python main.py "$@"

# Deactivate virtual environment
deactivate

# Return to original directory
cd - > /dev/null