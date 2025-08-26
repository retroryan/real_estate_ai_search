"""
Main entry point for the data pipeline CLI with enhanced configuration support.

This module provides command-line interface for running the Spark data pipeline
with data subsetting and flexible embedding model selection.

Can be run from within the module or from the parent directory:
    python -m data_pipeline (from parent directory)
    python __main__.py (from within data_pipeline directory)
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

from .core.pipeline_runner import DataPipelineRunner
from .config.settings import ConfigurationManager


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
    
    # Set py4j logging to INFO level to avoid extremely verbose debug output
    # py4j generates hundreds of debug messages per second which makes output unreadable
    logging.getLogger("py4j").setLevel(logging.INFO)
    logging.getLogger("py4j.java_gateway").setLevel(logging.INFO)
    logging.getLogger("py4j.clientserver").setLevel(logging.INFO)


def main():
    """Main CLI entry point with enhanced configuration options."""
    
    parser = argparse.ArgumentParser(
        description="Run the multi-entity Spark data pipeline for real estate and Wikipedia data"
    )
    
    # Configuration options
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to pipeline configuration file (default: searches for config.yaml)"
    )
    
    
    # Data subsetting options
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Number of records to sample from each source"
    )
    
    # Output options
    parser.add_argument(
        "--output-destination",
        type=str,
        default=None,
        help="Output destinations (comma-separated): parquet,neo4j,archive_elasticsearch"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Custom output directory path"
    )
    
    # Spark options
    parser.add_argument(
        "--cores",
        type=int,
        default=None,
        help="Number of cores to use (default: all available)"
    )
    
    
    # Operational options
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

    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Display effective configuration and exit"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        sample_size = args.sample_size
        embedding_provider = None
        if sample_size:
            logger.info(f"Data sample size enabled: {sample_size} records per source")
        
        # Initialize configuration manager with direct arguments
        config_manager = ConfigurationManager(
            config_path=args.config,
            environment=None,
            sample_size=sample_size,
            output_destinations=args.output_destination,
            output_path=args.output,
            cores=args.cores,
            embedding_provider=embedding_provider
        )
        config = config_manager.load_config()
        logger.debug(f"Config manager created: {config_manager}")
        logger.debug(f"Config loaded: {config}")
        
        # Show configuration and exit if requested
        if args.show_config:
            print("\n" + "=" * 60)
            print("EFFECTIVE PIPELINE CONFIGURATION")
            print("=" * 60)
            summary = config_manager.get_effective_config_summary()
            
            print(f"\nPipeline: {summary['pipeline']['name']} v{summary['pipeline']['version']}")
            print(f"Environment: {summary['pipeline']['environment']}")
            
            print(f"\nSpark:")
            print(f"  Master: {summary['spark']['master']}")
            print(f"  Memory: {summary['spark']['memory']}")
            
            
            print(f"\nEmbedding:")
            print(f"  Provider: {summary['embedding']['provider']}")
            print(f"  Model: {summary['embedding']['model']}")
            print(f"  Batch Size: {summary['embedding']['batch_size']}")
            
            print(f"\nOutput:")
            print(f"  Format: {summary['output']['format']}")
            print(f"  Path: {summary['output']['path']}")
            
            print(f"\nDestinations:")
            print(f"  Enabled: {summary['destinations']['enabled']}")
            
            print("=" * 60)
            return 0
        
        # Initialize pipeline runner with loaded configuration
        runner = DataPipelineRunner(config_override=config)
        
        # Validate only mode
        if args.validate_only:
            logger.info("Running in validation-only mode")
            
            # Validate configuration
            logger.debug(f"ConfigManager type: {type(config_manager)}")
            logger.debug(f"ConfigManager value: {config_manager}")
            is_prod_ready = config_manager.validate_for_production()
            
            print("\n" + "=" * 60)
            print("PIPELINE VALIDATION RESULTS")
            print("=" * 60)
            print(f"Configuration valid: True")
            print(f"Production ready: {is_prod_ready}")
            
            # Show configuration summary
            summary = config_manager.get_effective_config_summary()
            print(f"\nEnvironment: {summary['pipeline']['environment']}")
            print(f"Embedding provider: {summary['embedding']['provider']}")
            
            # Show basic Spark info
            print(f"\nSpark version: {runner.spark.sparkContext.version}")
            print(f"Available cores: {runner.spark.sparkContext.defaultParallelism}")
            
            print("\nData Sources:")
            print(f"  ✓ Properties: {len(config.properties)} files")
            print(f"  ✓ Neighborhoods: {len(config.neighborhoods)} files")
            print(f"  ✓ Wikipedia: enabled")
            print(f"  ✓ Locations: enabled")
            
            print("=" * 60)
            return 0
        
        # Run the full pipeline with embeddings (always included for simplicity)
        result_dataframes = runner.run_full_pipeline_with_embeddings()
        
        # Write results to all configured destinations using entity-specific method
        runner.write_entity_outputs(result_dataframes)
        
        # Clean up
        runner.stop()
        
        return 0
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())