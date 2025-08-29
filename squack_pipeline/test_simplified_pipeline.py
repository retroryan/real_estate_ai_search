#!/usr/bin/env python3
"""Test script for the simplified pipeline with entity-specific processors.

This script tests the complete flow:
1. Bronze: Load with nested structures
2. Silver: Clean and denormalize while preserving nesting
3. Gold: Minimal transformation for Elasticsearch
"""

from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.orchestrator.pipeline_simple import SimplifiedPipelineOrchestrator
from squack_pipeline.utils.logging import PipelineLogger


def main():
    """Run simplified pipeline test."""
    logger = PipelineLogger.get_logger("test_pipeline")
    
    try:
        # Load settings
        config_path = Path("squack_pipeline/config.yaml")
        if not config_path.exists():
            logger.error(f"Config file not found: {config_path}")
            return 1
        
        settings = PipelineSettings.load_from_yaml(config_path)
        
        # Override settings for testing
        settings.data.sample_size = 5  # Small sample for testing
        # Note: embedding and elasticsearch settings are controlled by config
        
        logger.info("Starting simplified pipeline test...")
        logger.info(f"Sample size: {settings.data.sample_size}")
        
        # Create and run pipeline
        pipeline = SimplifiedPipelineOrchestrator(settings)
        pipeline.run()
        
        logger.success("✓ Pipeline test completed successfully!")
        
        # Show final table names
        logger.info("\nFinal Tables Created:")
        for tier, tables in pipeline.tables.items():
            if tables:
                logger.info(f"\n{tier.upper()} Tier:")
                for entity, table_name in tables.items():
                    if table_name:
                        count = pipeline.metrics[tier].get(entity, 0)
                        logger.info(f"  {entity:12} → {table_name:30} ({count} records)")
        
        return 0
        
    except Exception as e:
        logger.error(f"Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())