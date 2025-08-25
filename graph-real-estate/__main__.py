"""Main entry point for graph-real-estate module when run with python -m"""

import sys
import os

# Add the module directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import main

if __name__ == "__main__":
    main()