"""
Main entry point for the data pipeline CLI.

Simple CLI with only --sample-size option for development/testing.
All other configuration comes from YAML and environment variables.
"""

import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is in Python path for imports when running as module
if __name__ == "__main__":
    # When running as python -m data_pipeline from parent directory
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from data_pipeline.config.loader import load_configuration
from data_pipeline.core.pipeline_runner import DataPipelineRunner


def setup_logging() -> None:
    """Configure logging with sensible defaults."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout
    )
    
    # Reduce noise from py4j
    logging.getLogger("py4j").setLevel(logging.WARNING)
    logging.getLogger("py4j.java_gateway").setLevel(logging.WARNING)
    logging.getLogger("py4j.clientserver").setLevel(logging.WARNING)


def main():
    """Main CLI entry point - simplified to only accept sample-size."""
    
    parser = argparse.ArgumentParser(
        description="Run the real estate data pipeline",
        epilog="All configuration is in config.yaml. Use environment variables for API keys."
    )
    
    # Single optional argument for development/testing
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Number of records to sample from each source (for development/testing only)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration with sample size if provided
        logger.info("Loading pipeline configuration...")
        config = load_configuration(sample_size=args.sample_size)
        
        if args.sample_size:
            logger.info(f"Running in development mode with sample size: {args.sample_size}")
        else:
            logger.info("Running in production mode with full datasets")
        
        # Create and run pipeline
        logger.info("Initializing pipeline runner...")
        runner = DataPipelineRunner(config)
        
        logger.info("Starting pipeline execution...")
        result = runner.run_full_pipeline_with_embeddings()
        
        # Write outputs
        logger.info("Writing outputs...")
        runner.write_entity_outputs(result)
        
        # Clean up
        runner.stop()
        
        logger.info("Pipeline completed successfully!")
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        logger.error("Please create a config.yaml file in the data_pipeline directory")
        return 1
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your config.yaml and environment variables")
        return 1
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())