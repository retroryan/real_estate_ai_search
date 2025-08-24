#!/usr/bin/env python3
"""
Simple evaluation comparison runner.

Runs evaluation with multiple config files and compares results.
"""

import os
import argparse
import subprocess
import sys
from pathlib import Path
import logging

# Load environment variables from .env file
from dotenv import load_dotenv
# Try to load from current directory first, then parent
if Path(".env").exists():
    load_dotenv(".env")
elif Path("../.env").exists():
    load_dotenv("../.env")

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def run_eval_with_config(config_path: str, force_recreate: bool = True) -> bool:
    """
    Run evaluation with a specific config file.
    
    Args:
        config_path: Path to eval config YAML
        force_recreate: Whether to force recreate collections
        
    Returns:
        True if successful
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Running eval with config: {config_path}")
    logger.info(f"{'='*60}")
    
    cmd = [
        sys.executable, "-m", "common_embeddings",
        "--data-type", "eval",
        "--config", config_path
    ]
    
    if force_recreate:
        cmd.append("--force-recreate")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to run eval: {result.stderr}")
            return False
            
        # Log key output lines
        for line in result.stdout.split('\n'):
            if any(keyword in line for keyword in ['Created evaluation collection', 'Total Embeddings Generated', 'Processing complete']):
                logger.info(f"  {line.strip()}")
                
        return True
        
    except Exception as e:
        logger.error(f"Error running eval: {e}")
        return False


def compare_models() -> bool:
    """
    Run the comparison after creating embeddings.
    
    Returns:
        True if successful
    """
    logger.info(f"\n{'='*60}")
    logger.info("Running model comparison...")
    logger.info(f"{'='*60}")
    
    cmd = [sys.executable, "-m", "common_embeddings.evaluate.run_comparison"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Comparison failed: {result.stderr}")
            return False
            
        # Show results
        print(result.stdout)
        return True
        
    except Exception as e:
        logger.error(f"Error running comparison: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run evaluation with multiple configs and compare"
    )
    
    parser.add_argument(
        "configs",
        nargs="+",
        help="Config files or directory containing configs (e.g., eval_configs/ or eval_configs/nomic.yaml)"
    )
    
    parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="Force recreate collections"
    )
    
    parser.add_argument(
        "--skip-comparison",
        action="store_true",
        help="Skip the comparison step"
    )
    
    args = parser.parse_args()
    
    # Collect all config files
    config_files = []
    for config_path_str in args.configs:
        config_path = Path(config_path_str)
        
        if config_path.is_dir():
            # If directory, find all .yaml files
            yaml_files = list(config_path.glob("*.yaml")) + list(config_path.glob("*.yml"))
            if not yaml_files:
                logger.warning(f"No YAML files found in directory: {config_path}")
                continue
            logger.info(f"Found {len(yaml_files)} config files in {config_path}")
            config_files.extend(sorted(yaml_files))
        elif config_path.exists():
            # Single file
            config_files.append(config_path)
        else:
            logger.error(f"Path not found: {config_path}")
            continue
    
    if not config_files:
        logger.error("No config files to process")
        sys.exit(1)
    
    logger.info(f"Processing {len(config_files)} config files:")
    for cf in config_files:
        logger.info(f"  - {cf}")
    
    # Run evaluation for each config
    success = True
    for config_path in config_files:            
        if not run_eval_with_config(str(config_path), args.force_recreate):
            success = False
    
    # Run comparison if requested
    if success and not args.skip_comparison:
        success = compare_models()
    
    if success:
        logger.info(f"\n✅ Evaluation complete!")
    else:
        logger.error(f"\n❌ Evaluation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()