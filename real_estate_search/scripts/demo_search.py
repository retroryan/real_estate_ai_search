#!/usr/bin/env python3
"""
Demo script - backward compatibility wrapper for main.py.
Use 'python main.py --mode search' or 'python main.py --mode demo' instead.
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Wrapper that calls main.py in demo mode."""
    # Build command for main.py
    main_path = Path(__file__).parent.parent / "main.py"
    cmd = [sys.executable, str(main_path), "--mode", "demo"]
    
    print("Note: This script is deprecated. Use 'python main.py --mode demo' directly.")
    print("Running demo through main.py...\n")
    
    # Execute main.py
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()