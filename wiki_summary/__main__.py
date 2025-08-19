#!/usr/bin/env python3
"""
Main entry point for Wikipedia summarization pipeline.
Supports processing articles with relevance filtering and flagged content reporting.

Usage:
    python -m wiki_summary --help
    python -m wiki_summary process --limit 10
    python -m wiki_summary process --limit 50 --create-report
    python -m wiki_summary test --articles 5
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from wiki_summary/.env file
from dotenv import load_dotenv
load_dotenv("wiki_summary/.env")

from wiki_summary.main import main

if __name__ == "__main__":
    main()