"""
Main entry point for the data pipeline CLI.

This module provides command-line interface for running the Spark data pipeline.
"""

import argparse
import logging
import sys
from pathlib import Path

from data_pipeline.core.pipeline_runner import DataPipelineRunner


def setup_logging(level: str) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout
    )


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run the unified Spark data pipeline for real estate and Wikipedia data"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="data_pipeline/config/pipeline_config.yaml",
        help="Path to pipeline configuration file (default: data_pipeline/config/pipeline_config.yaml)"
    )
    
    parser.add_argument(
        "--cores",
        type=int,
        default=None,
        help="Number of cores to use (default: all available)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path for results (overrides config)"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate configuration and environment, don't run pipeline"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Update Spark configuration if cores specified
        if args.cores:
            import os
            os.environ["SPARK_MASTER"] = f"local[{args.cores}]"
            logger.info(f"Configured Spark to use {args.cores} cores")
        
        # Initialize pipeline runner
        runner = DataPipelineRunner(args.config)
        
        # Validate only mode
        if args.validate_only:
            logger.info("Running in validation-only mode")
            validation = runner.validate_pipeline()
            
            print("\n" + "=" * 60)
            print("PIPELINE VALIDATION RESULTS")
            print("=" * 60)
            print(f"Configuration valid: {validation['configuration']['is_valid']}")
            print(f"Production ready: {validation['configuration']['production_ready']}")
            print(f"Spark version: {validation['environment']['spark_version']}")
            print(f"Available cores: {validation['environment']['available_cores']}")
            
            print("\nData Sources:")
            for source, status in validation['data_sources'].items():
                symbol = "✓" if status['exists'] else "✗"
                enabled = "enabled" if status['enabled'] else "disabled"
                print(f"  {symbol} {source}: {enabled}")
            
            print("=" * 60)
            return 0
        
        # Run the full pipeline with embeddings (always included for simplicity)
        result_df = runner.run_full_pipeline_with_embeddings()
        
        # Save results if output path specified
        if args.output:
            logger.info(f"Saving results to: {args.output}")
            runner.save_results(args.output)
        else:
            # Save using configured output
            runner.save_results()
        
        # Clean up
        runner.stop()
        
        return 0
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())