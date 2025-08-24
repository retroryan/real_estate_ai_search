#!/usr/bin/env python
"""
End-to-end test script for the data pipeline.

This script tests the complete pipeline flow with a small subset of data
to ensure all components work correctly together.
"""

import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_pipeline.config.models import (
    PipelineConfig,
    SparkConfig,
    DataSourceConfig,
    OutputDestinationsConfig,
    ParquetWriterConfig,
    ProcessingConfig,
    EnrichmentConfig,
    LoggingConfig,
    MetadataConfig
)
from data_pipeline.core.pipeline_runner import DataPipelineRunner


def create_test_config() -> PipelineConfig:
    """Create a test configuration with small data subset."""
    
    # Spark configuration
    spark_config = SparkConfig(
        app_name="test_pipeline",
        master="local[2]",
        memory="2g",
        executor_memory="1g",
        config={
            "spark.sql.adaptive.enabled": "true",
            "spark.sql.adaptive.coalescePartitions.enabled": "true"
        }
    )
    
    # Data sources - use small subset
    data_sources = {
        "properties": DataSourceConfig(
            path="real_estate_data/properties_sf.json",
            format="json",
            enabled=True,
            sample_size=50  # Small subset for testing
        ),
        "neighborhoods": DataSourceConfig(
            path="real_estate_data/neighborhoods_sf.json",
            format="json",
            enabled=True,
            sample_size=10
        ),
        "wikipedia": DataSourceConfig(
            path="data/wikipedia/wikipedia.db",
            format="sqlite",
            enabled=True,
            table_name="articles",
            sample_size=20
        )
    }
    
    # Output destinations
    parquet_config = ParquetWriterConfig(
        enabled=True,
        path="data_pipeline/test_output/parquet",
        partition_by=["state", "city"],
        compression="snappy"
    )
    
    # Output destinations - Parquet only for basic test
    output_destinations = OutputDestinationsConfig(
        enabled_destinations=["parquet"],
        parquet=parquet_config
    )
    
    # Processing configuration
    processing_config = ProcessingConfig(
        cache_intermediate_results=False,
        enable_quality_checks=True,
        enable_data_validation=True,
        max_records_per_partition=1000
    )
    
    # Enrichment configuration
    enrichment_config = EnrichmentConfig(
        add_derived_fields=True,
        normalize_features=True,
        quality_threshold=0.5,
        city_abbreviations={"SF": "San Francisco", "PC": "Park City"},
        state_abbreviations={"CA": "California", "UT": "Utah"}
    )
    
    # Logging configuration
    logging_config = LoggingConfig(
        level="INFO",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        console=True
    )
    
    # Pipeline metadata
    metadata = MetadataConfig(
        name="test_pipeline",
        version="1.0.0",
        description="End-to-end test of data pipeline"
    )
    
    # Create complete configuration
    config = PipelineConfig(
        metadata=metadata,
        spark=spark_config,
        data_sources=data_sources,
        output_destinations=output_destinations,
        processing=processing_config,
        enrichment=enrichment_config,
        logging=logging_config
    )
    
    return config


def test_pipeline():
    """Run the pipeline test."""
    
    logger.info("="*60)
    logger.info("🧪 DATA PIPELINE END-TO-END TEST")
    logger.info("="*60)
    
    try:
        # Create test configuration
        logger.info("📋 Creating test configuration...")
        config = create_test_config()
        
        # Initialize pipeline runner
        logger.info("🚀 Initializing pipeline runner...")
        runner = DataPipelineRunner(config_override=config)
        
        # Show basic configuration info
        logger.info("✅ Pipeline configuration loaded")
        logger.info(f"   Spark app: {runner.spark.sparkContext.appName}")
        logger.info(f"   Spark version: {runner.spark.sparkContext.version}")
        
        # Run the pipeline
        logger.info("🏃 Running pipeline...")
        result = runner.run_full_pipeline()
        
        # Check results
        logger.info("📊 Pipeline Results:")
        for entity_type, df in result.items():
            if df is not None:
                count = df.count()
                logger.info(f"   {entity_type}: {count} records")
                
                # Show sample records
                if count > 0:
                    logger.debug(f"   Sample {entity_type} columns: {df.columns[:5]}")
        
        # Write outputs
        logger.info("📤 Writing outputs...")
        runner.write_entity_outputs(result)
        
        # Clean up
        logger.info("🧹 Cleaning up...")
        runner.stop()
        
        logger.info("✅ TEST COMPLETED SUCCESSFULLY")
        logger.info("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ TEST FAILED: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    # Run basic test with Parquet output only
    success = test_pipeline()
    sys.exit(0 if success else 1)