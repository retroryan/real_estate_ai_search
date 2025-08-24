"""
Main entry point for the data pipeline CLI with enhanced configuration support.

This module provides command-line interface for running the Spark data pipeline
with data subsetting and flexible embedding model selection.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from data_pipeline.core.pipeline_runner import DataPipelineRunner
from data_pipeline.config.settings import ConfigurationManager


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
    # Load environment variables from parent .env file
    parent_env = Path(__file__).parent.parent / ".env"
    if parent_env.exists():
        load_dotenv(parent_env)
    
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
        "--subset",
        action="store_true",
        help="Enable data subsetting for quick testing"
    )
    
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Number of records to sample from each source (requires --subset)"
    )
    
    parser.add_argument(
        "--sample-method",
        type=str,
        choices=["head", "random", "stratified"],
        default=None,
        help="Sampling method (requires --subset)"
    )
    
    
    parser.add_argument(
        "--embedding-model",
        type=str,
        default=None,
        help="Override embedding model from config"
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
    
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Run in test mode with minimal data (sets subset=10 records)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        
        # Handle test mode first (highest priority)
        if args.test_mode:
            os.environ["DATA_SUBSET_ENABLED"] = "true"
            os.environ["DATA_SUBSET_SAMPLE_SIZE"] = "10"
            os.environ["DEVELOPMENT_MODE"] = "true"
            logger.info("Test mode enabled: using 10 records per source")
        
        # Handle data subsetting
        elif args.subset:  # Use elif to avoid conflict with test_mode
            os.environ["DATA_SUBSET_ENABLED"] = "true"
            if args.sample_size:
                os.environ["DATA_SUBSET_SAMPLE_SIZE"] = str(args.sample_size)
                logger.info(f"Data subsetting enabled: {args.sample_size} records per source")
            else:
                logger.info("Data subsetting enabled with default sample size")
        
        # Set Spark configuration
        if args.cores:
            os.environ["SPARK_MASTER"] = f"local[{args.cores}]"
            logger.info(f"Configured Spark to use {args.cores} cores")
        
        
        if args.embedding_model:
            os.environ["EMBEDDING_MODEL"] = args.embedding_model
            logger.info(f"Using embedding model: {args.embedding_model}")
        
        # Initialize configuration manager
        config_manager = ConfigurationManager(
            config_path=args.config,
            environment=None
        )
        config = config_manager.load_config()
        
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
            
            print(f"\nData Subsetting:")
            print(f"  Enabled: {summary['data_subsetting']['enabled']}")
            if summary['data_subsetting']['enabled']:
                print(f"  Sample Size: {summary['data_subsetting']['sample_size']}")
                print(f"  Method: {summary['data_subsetting']['method']}")
            
            print(f"\nEmbedding:")
            print(f"  Provider: {summary['embedding']['provider']}")
            print(f"  Model: {summary['embedding']['model']}")
            print(f"  Batch Size: {summary['embedding']['batch_size']}")
            
            print(f"\nOutput:")
            print(f"  Format: {summary['output']['format']}")
            print(f"  Path: {summary['output']['path']}")
            
            print(f"\nProcessing:")
            print(f"  Quality Checks: {summary['processing']['quality_checks']}")
            print(f"  Cache Enabled: {summary['processing']['cache_enabled']}")
            print(f"  Parallel Tasks: {summary['processing']['parallel_tasks']}")
            
            print("=" * 60)
            return 0
        
        # Initialize pipeline runner with loaded configuration
        runner = DataPipelineRunner()
        
        # Validate only mode
        if args.validate_only:
            logger.info("Running in validation-only mode")
            
            # Validate configuration
            is_prod_ready = config_manager.validate_for_production()
            
            print("\n" + "=" * 60)
            print("PIPELINE VALIDATION RESULTS")
            print("=" * 60)
            print(f"Configuration valid: True")
            print(f"Production ready: {is_prod_ready}")
            
            # Show configuration summary
            summary = config_manager.get_effective_config_summary()
            print(f"\nEnvironment: {summary['pipeline']['environment']}")
            print(f"Data subsetting: {'ENABLED' if summary['data_subsetting']['enabled'] else 'DISABLED'}")
            print(f"Embedding provider: {summary['embedding']['provider']}")
            
            # Validate pipeline components
            validation = runner.validate_pipeline()
            
            print(f"\nSpark version: {validation['environment']['spark_version']}")
            print(f"Available cores: {validation['environment']['available_cores']}")
            
            print("\nData Sources:")
            for source, status in validation['data_sources'].items():
                symbol = "✓" if status['exists'] else "✗"
                enabled = "enabled" if status['enabled'] else "disabled"
                print(f"  {symbol} {source}: {enabled}")
            
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