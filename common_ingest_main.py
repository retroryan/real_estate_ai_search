#!/usr/bin/env python
"""
Main entry point for the common_ingest module (run from parent directory).

This script runs the common_ingest data loading pipeline and displays summary
statistics for properties, neighborhoods, and Wikipedia data.

Usage:
    python common_ingest_main.py
    python -m common_ingest_main
"""

import sys
from pathlib import Path

# Add project root to Python path to ensure imports work
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the main functionality from common_ingest
from common_ingest.__main__ import main


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)