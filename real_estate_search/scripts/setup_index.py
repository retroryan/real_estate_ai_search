#!/usr/bin/env python3
"""
Setup script - backward compatibility wrapper for main.py.
Use 'python main.py --mode ingest' instead for new code.
"""

import subprocess
import sys
import argparse
from pathlib import Path


def main():
    """Wrapper that calls main.py with appropriate arguments."""
    parser = argparse.ArgumentParser(
        description="Setup index (deprecated - use main.py directly)"
    )
    parser.add_argument('--recreate', action='store_true', help='Recreate index')
    parser.add_argument('--test-data', action='store_true', help='Use test data (not implemented)')
    args = parser.parse_args()
    
    # Build command for main.py
    main_path = Path(__file__).parent.parent / "main.py"
    cmd = [sys.executable, str(main_path), "--mode", "ingest"]
    
    if args.recreate:
        cmd.append("--recreate")
    
    if args.test_data:
        print("Warning: --test-data flag is not implemented in new architecture")
    
    # Execute main.py
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()