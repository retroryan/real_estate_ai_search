"""
Basic pipeline usage example.

This script demonstrates how to use the data pipeline to load and process
real estate and Wikipedia data.
"""

import logging
from pathlib import Path

from data_pipeline.core.pipeline_runner import DataPipelineRunner


def main():
    """Run basic pipeline example."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Get config path (assumes running from project root)
    config_path = Path(__file__).parent.parent / "config" / "pipeline_config.yaml"
    
    # Initialize pipeline runner
    print("Initializing pipeline...")
    runner = DataPipelineRunner(str(config_path))
    
    # Validate pipeline configuration
    print("\nValidating pipeline configuration...")
    validation = runner.validate_pipeline()
    print(f"Configuration valid: {validation['configuration']['is_valid']}")
    print(f"Production ready: {validation['configuration']['production_ready']}")
    print(f"Spark version: {validation['environment']['spark_version']}")
    
    # Run the full pipeline
    print("\nRunning full pipeline...")
    result_df = runner.run_full_pipeline()
    
    # Show sample results
    print("\nSample results (first 5 records):")
    result_df.select(
        "entity_id", 
        "entity_type", 
        "city", 
        "state"
    ).show(5, truncate=False)
    
    # Show schema
    print("\nDataFrame schema:")
    result_df.printSchema()
    
    # Get entity type statistics
    print("\nEntity type distribution:")
    result_df.groupBy("entity_type").count().show()
    
    # Save results if needed
    # runner.save_results("data/output/pipeline_results")
    
    # Clean up
    print("\nCleaning up...")
    runner.stop()
    print("Pipeline example completed successfully!")


if __name__ == "__main__":
    main()