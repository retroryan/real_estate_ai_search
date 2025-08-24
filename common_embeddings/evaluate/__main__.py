#!/usr/bin/env python3
"""
Entry point for evaluation module.

Usage:
    python -m common_embeddings.evaluate compare [configs...]
    python -m common_embeddings.evaluate run
"""

import sys
import argparse
from pathlib import Path

def main():
    """Main entry point for evaluate module."""
    parser = argparse.ArgumentParser(
        description="Embedding evaluation tools",
        prog="python -m common_embeddings.evaluate"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Compare command - runs multiple configs and compares
    compare_parser = subparsers.add_parser(
        'compare',
        help='Run evaluation with multiple configs and compare results'
    )
    compare_parser.add_argument(
        "configs",
        nargs="+",
        help="Config files or directory containing configs"
    )
    compare_parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="Force recreate collections"
    )
    compare_parser.add_argument(
        "--skip-comparison",
        action="store_true",
        help="Skip the comparison step"
    )
    
    # Run command - just runs comparison on existing collections
    run_parser = subparsers.add_parser(
        'run',
        help='Run comparison on existing collections'
    )
    run_parser.add_argument(
        "--config",
        default="common_embeddings/test.config.yaml",
        help="Test configuration file"
    )
    
    args = parser.parse_args()
    
    if args.command == 'compare':
        # Import and run the compare_models module
        from .compare_models import main as compare_main
        # Pass the args to the compare_models main
        sys.argv = ['compare_models.py'] + args.configs
        if args.force_recreate:
            sys.argv.append('--force-recreate')
        if args.skip_comparison:
            sys.argv.append('--skip-comparison')
        compare_main()
    elif args.command == 'run':
        # Import and run the run_comparison module
        from .run_comparison import main as run_main
        if args.config:
            sys.argv = ['run_comparison.py', '--config', args.config]
        else:
            sys.argv = ['run_comparison.py']
        run_main()
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()