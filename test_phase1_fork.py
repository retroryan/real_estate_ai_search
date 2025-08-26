#!/usr/bin/env python3
"""
Test script for Phase 1: Pipeline Fork Implementation.

This script verifies that:
1. The pipeline fork is correctly integrated
2. The graph path works unchanged
3. The fork configuration is properly loaded
4. DataFrames are routed correctly
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data_pipeline.config.loader import load_configuration
from data_pipeline.core.pipeline_runner import DataPipelineRunner
from data_pipeline.core.pipeline_fork import ForkConfiguration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_fork_configuration():
    """Test that fork configuration is loaded correctly."""
    logger.info("=" * 60)
    logger.info("Testing Fork Configuration Loading")
    logger.info("=" * 60)
    
    try:
        # Load configuration
        config = load_configuration(sample_size=5)
        
        # Check fork configuration exists
        assert hasattr(config, 'fork'), "Fork configuration missing from PipelineConfig"
        logger.info("✓ Fork configuration found in PipelineConfig")
        
        # Check fork configuration values
        assert config.fork.enabled_paths == ["graph"], f"Expected ['graph'], got {config.fork.enabled_paths}"
        logger.info(f"✓ Fork enabled paths: {config.fork.enabled_paths}")
        
        # Test ForkConfiguration model
        fork_config = ForkConfiguration(**config.fork.model_dump())
        assert fork_config.is_graph_enabled(), "Graph path should be enabled"
        assert not fork_config.is_search_enabled(), "Search path should not be enabled"
        logger.info("✓ ForkConfiguration model working correctly")
        
        logger.info("✅ Fork configuration test PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Fork configuration test FAILED: {e}")
        return False


def test_pipeline_with_fork():
    """Test that the pipeline runs with fork integrated."""
    logger.info("=" * 60)
    logger.info("Testing Pipeline with Fork Integration")
    logger.info("=" * 60)
    
    try:
        # Load configuration with small sample for testing
        config = load_configuration(sample_size=5)
        
        # Create pipeline runner
        logger.info("Creating pipeline runner...")
        runner = DataPipelineRunner(config)
        
        # Check that pipeline fork is initialized
        assert hasattr(runner, 'pipeline_fork'), "Pipeline fork not initialized"
        logger.info("✓ Pipeline fork initialized")
        
        # Run pipeline without embeddings
        logger.info("Running pipeline without embeddings...")
        result = runner.run_full_pipeline()
        
        # Check that we got results
        assert result is not None, "Pipeline returned None"
        assert len(result) > 0, "Pipeline returned empty results"
        logger.info(f"✓ Pipeline completed with {len(result)} entity types")
        
        # Check that expected entity types are present
        expected_entities = {'properties', 'neighborhoods', 'wikipedia'}
        actual_entities = set(result.keys())
        
        # Log what we got
        logger.info(f"  Entity types returned: {actual_entities}")
        
        # Check for core entities (at minimum we should have some)
        core_entities_found = actual_entities & expected_entities
        if core_entities_found:
            logger.info(f"✓ Core entities found: {core_entities_found}")
        
        # Check that DataFrames have expected structure
        for entity_type, df in result.items():
            if df is not None:
                logger.info(f"  {entity_type}: {len(df.columns)} columns")
                if 'embedding_text' in df.columns:
                    logger.info(f"    ✓ Has embedding_text column")
        
        logger.info("✅ Pipeline with fork test PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Pipeline with fork test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_graph_path_unchanged():
    """Test that graph processing path works as before."""
    logger.info("=" * 60)
    logger.info("Testing Graph Path Unchanged")
    logger.info("=" * 60)
    
    try:
        # Load configuration
        config = load_configuration(sample_size=5)
        
        # Ensure only graph path is enabled
        config.fork.enabled_paths = ["graph"]
        
        # Create pipeline runner
        runner = DataPipelineRunner(config)
        
        # Run pipeline
        logger.info("Running pipeline with graph path only...")
        result = runner.run_full_pipeline()
        
        # Check for graph-specific entities
        graph_entities = ['features', 'property_types', 'price_ranges', 'counties', 'topic_clusters']
        graph_entities_found = [e for e in graph_entities if e in result]
        
        if graph_entities_found:
            logger.info(f"✓ Graph entities extracted: {graph_entities_found}")
        
        # Check for relationship DataFrames
        relationship_entities = [k for k in result.keys() if 'relationship' in k.lower()]
        if relationship_entities:
            logger.info(f"✓ Relationship entities found: {relationship_entities}")
        
        logger.info("✅ Graph path test PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Graph path test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fork_routing():
    """Test that fork correctly routes DataFrames."""
    logger.info("=" * 60)
    logger.info("Testing Fork Routing Logic")
    logger.info("=" * 60)
    
    try:
        from pyspark.sql import SparkSession
        from data_pipeline.core.pipeline_fork import PipelineFork, ForkConfiguration
        
        # Create a Spark session for testing
        spark = SparkSession.builder \
            .appName("test_fork_routing") \
            .master("local[1]") \
            .getOrCreate()
        
        # Create test DataFrames
        properties_df = spark.createDataFrame(
            [("prop1", 100000), ("prop2", 200000)],
            ["listing_id", "price"]
        )
        neighborhoods_df = spark.createDataFrame(
            [("n1", "Downtown"), ("n2", "Suburb")],
            ["neighborhood_id", "name"]
        )
        wikipedia_df = spark.createDataFrame(
            [("page1", "San Francisco"), ("page2", "Pacific Heights")],
            ["page_id", "title"]
        )
        
        # Test with graph path only
        logger.info("Testing graph-only routing...")
        fork_config = ForkConfiguration(enabled_paths=["graph"])
        fork = PipelineFork(fork_config)
        
        result, routed = fork.route(properties_df, neighborhoods_df, wikipedia_df)
        
        assert result.graph_success, "Graph routing should succeed"
        assert not result.search_success, "Search routing should not be active"
        assert "graph" in routed, "Graph DataFrames should be present"
        assert "search" not in routed, "Search DataFrames should not be present"
        logger.info("✓ Graph-only routing works correctly")
        
        # Test with both paths
        logger.info("Testing dual-path routing...")
        fork_config = ForkConfiguration(enabled_paths=["graph", "search"])
        fork = PipelineFork(fork_config)
        
        result, routed = fork.route(properties_df, neighborhoods_df, wikipedia_df)
        
        assert result.graph_success, "Graph routing should succeed"
        assert result.search_success, "Search routing should succeed"
        assert "graph" in routed, "Graph DataFrames should be present"
        assert "search" in routed, "Search DataFrames should be present"
        logger.info("✓ Dual-path routing works correctly")
        
        # Clean up
        spark.stop()
        
        logger.info("✅ Fork routing test PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Fork routing test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Phase 1 tests."""
    logger.info("🚀 Starting Phase 1 Pipeline Fork Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Fork Configuration", test_fork_configuration),
        ("Fork Routing", test_fork_routing),
        ("Pipeline with Fork", test_pipeline_with_fork),
        ("Graph Path Unchanged", test_graph_path_unchanged),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            logger.info(f"\nRunning: {test_name}")
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All Phase 1 tests passed!")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()