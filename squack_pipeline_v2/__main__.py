"""Main entry point for SQUACK Pipeline V2.

A clean medallion architecture pipeline using DuckDB best practices.

Usage:
    python -m squack_pipeline_v2 [options]
    
Examples:
    # Run full pipeline
    python -m squack_pipeline_v2
    
    # Run with sample data
    python -m squack_pipeline_v2 --sample-size 100
    
    # Export to Elasticsearch
    python -m squack_pipeline_v2 --elasticsearch
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from squack_pipeline_v2.core.settings import PipelineSettings
from squack_pipeline_v2.orchestration.pipeline import PipelineOrchestrator

logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="SQUACK Pipeline V2 - DuckDB Medallion Architecture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                     # Run full pipeline
  %(prog)s --sample-size 100   # Test with 100 records
  %(prog)s --elasticsearch     # Export to Elasticsearch
        """
    )
    
    # Data processing
    parser.add_argument(
        "--sample-size",
        type=int,
        help="Limit data to N records per entity (for testing)"
    )
    
    # Pipeline stages
    parser.add_argument(
        "--skip-bronze",
        action="store_true",
        help="Skip Bronze layer (use existing bronze tables)"
    )
    
    parser.add_argument(
        "--skip-silver",
        action="store_true",
        help="Skip Silver layer (use existing silver tables)"
    )
    
    parser.add_argument(
        "--skip-gold",
        action="store_true",
        help="Skip Gold layer (use existing gold tables)"
    )
    
    # Output options
    parser.add_argument(
        "--no-parquet",
        action="store_true",
        help="Skip Parquet export"
    )
    
    parser.add_argument(
        "--elasticsearch",
        action="store_true",
        help="Export to Elasticsearch"
    )
    
    # Configuration
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("squack_pipeline_v2/config.yaml"),
        help="Path to configuration file (default: squack_pipeline_v2/config.yaml)"
    )
    
    # Logging
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (overrides config)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    # Utility modes
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show table statistics and exit"
    )
    
    
    return parser.parse_args()




def show_statistics(orchestrator: PipelineOrchestrator) -> None:
    """Show table statistics.
    
    Args:
        orchestrator: Pipeline orchestrator
    """
    print("\n" + "=" * 60)
    print("SQUACK Pipeline V2 - Table Statistics")
    print("=" * 60)
    
    stats = orchestrator.get_table_stats()
    
    if not stats:
        print("No tables found")
        return
    
    # Group by layer
    layers = {
        "Bronze": [],
        "Silver": [],
        "Gold": [],
        "Embeddings": []
    }
    
    for table, count in stats.items():
        if table.startswith("bronze_"):
            layers["Bronze"].append((table, count))
        elif table.startswith("silver_"):
            layers["Silver"].append((table, count))
        elif table.startswith("gold_"):
            layers["Gold"].append((table, count))
        elif table.startswith("embeddings_"):
            layers["Embeddings"].append((table, count))
    
    # Display by layer
    for layer_name, tables in layers.items():
        if tables:
            print(f"\n{layer_name} Layer:")
            print("-" * 40)
            for table, count in sorted(tables):
                print(f"  {table:<30} {count:>10,} records")
    
    print("\n" + "=" * 60)


def clean_tables(orchestrator: PipelineOrchestrator) -> None:
    """Clean all pipeline tables.
    
    Args:
        orchestrator: Pipeline orchestrator
    """
    print("Cleaning all pipeline tables...")
    
    tables = [
        "bronze_properties", "bronze_neighborhoods", "bronze_wikipedia",
        "silver_properties", "silver_neighborhoods", "silver_wikipedia",
        "gold_properties", "gold_neighborhoods", "gold_wikipedia",
        "embeddings_properties", "embeddings_neighborhoods", "embeddings_wikipedia"
    ]
    
    for table in tables:
        if orchestrator.connection_manager.table_exists(table):
            orchestrator.connection_manager.execute(f"DROP TABLE {table}")
            print(f"  Dropped {table}")
    
    print("All tables cleaned")


def clean_database_file(settings: PipelineSettings) -> None:
    """Delete the entire database file for a completely fresh start.
    
    Args:
        settings: Pipeline settings
    """
    from pathlib import Path
    
    db_path = Path(settings.duckdb.database_file)
    
    if db_path.exists():
        db_path.unlink()
        print(f"Deleted database file: {db_path}")
    else:
        print(f"Database file does not exist: {db_path}")
    
    # Ensure output directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Output directory ready: {db_path.parent}")


def main() -> int:
    """Main entry point.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    args = parse_arguments()
    
    # Load configuration with environment variables and overrides
    try:
        # Prepare overrides from command line
        overrides = {}
        if args.sample_size:
            overrides["data"] = {"sample_size": args.sample_size}
        
        settings = PipelineSettings.load(config_path=args.config, **overrides)
    except Exception as e:
        print(f"Error loading config from {args.config}: {e}")
        return 1
    
    # Setup logging
    log_level = args.log_level or settings.logging.level
    if args.verbose:
        log_level = "DEBUG"
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create orchestrator
    orchestrator = PipelineOrchestrator(settings)
    
    try:
        # Special modes
        if args.stats:
            show_statistics(orchestrator)
            return 0
        
        # Always clean database for simple demo
        clean_database_file(settings)
        
        # Start timing
        start_time = time.time()
        
        print("\n" + "=" * 60)
        print("SQUACK Pipeline V2 - Starting")
        print("=" * 60)
        print(f"Config: {args.config}")
        print(f"Sample size: {args.sample_size or settings.data.sample_size or 'full data'}")
        print(f"Embeddings: enabled")
        print(f"Parquet export: {'enabled' if not args.no_parquet and settings.output.parquet_enabled else 'disabled'}")
        print(f"Elasticsearch: {'enabled' if args.elasticsearch or settings.output.elasticsearch_enabled else 'disabled'}")
        print("=" * 60 + "\n")
        
        # Run pipeline stages
        
        # Bronze layer
        if not args.skip_bronze:
            print("Running Bronze layer...")
            orchestrator.run_bronze_layer(settings.data.sample_size)
        
        # Silver layer
        if not args.skip_silver:
            print("Running Silver layer...")
            orchestrator.run_silver_layer()
        
        # Gold layer
        if not args.skip_gold:
            print("Running Gold layer...")
            orchestrator.run_gold_layer()
        
        # Embeddings
        print("Generating embeddings...")
        orchestrator.run_embeddings()
        
        # Writers
        write_parquet = not args.no_parquet and settings.output.parquet_enabled
        write_elasticsearch = args.elasticsearch or settings.output.elasticsearch_enabled
        
        if write_parquet or write_elasticsearch:
            print("Exporting data...")
            orchestrator.run_writers(
                write_parquet=write_parquet,
                write_elasticsearch=write_elasticsearch
            )
        
        # Calculate total elapsed time
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Format time display
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # Show final statistics
        print("\n" + "=" * 60)
        print("Pipeline completed successfully!")
        print("=" * 60)
        show_statistics(orchestrator)
        
        # Display timing information
        print("\n" + "=" * 60)
        print("Pipeline Execution Time")
        print("-" * 60)
        if hours > 0:
            print(f"Total time: {int(hours)}h {int(minutes)}m {seconds:.2f}s")
        elif minutes > 0:
            print(f"Total time: {int(minutes)}m {seconds:.2f}s")
        else:
            print(f"Total time: {seconds:.2f}s")
        print(f"Raw seconds: {elapsed_time:.3f}")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        return 1
        
    finally:
        orchestrator.cleanup()


if __name__ == "__main__":
    sys.exit(main())