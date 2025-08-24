#!/usr/bin/env python
"""
Entry point for running common_embeddings as a module.

Usage:
    python -m common_embeddings --data-type real_estate
    python -m common_embeddings --data-type wikipedia --max-articles 10
    python -m common_embeddings --data-type all --force-recreate
"""

import sys
import json
from pathlib import Path
from .main import main
from .utils import get_logger

if __name__ == "__main__":
    try:
        summary = main()
        # Optionally write summary to file for external tools
        if summary:
            summary_path = Path("data/common_embeddings/last_run_summary.json")
            summary_path.parent.mkdir(exist_ok=True, parents=True)
            with open(summary_path, "w") as f:
                # Convert any non-serializable objects
                json_summary = json.loads(json.dumps(summary, default=str))
                json.dump(json_summary, f, indent=2)
        sys.exit(0)
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)