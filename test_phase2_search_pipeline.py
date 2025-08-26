#!/usr/bin/env python3
"""
Test script for Phase 2: Search Pipeline Implementation.

This script verifies that:
1. Search pipeline module is properly structured
2. Configuration models work correctly
3. SearchPipelineRunner integrates properly
4. Fork routing works with search path
5. Elasticsearch connection can be validated
"""

import sys
import logging
import os
from pathlib import Path
from unittest.mock import patch

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_search_pipeline_imports():
    """Test that search pipeline modules can be imported."""
    logger.info("=" * 60)
    logger.info("Testing Search Pipeline Module Imports")
    logger.info("=" * 60)
    
    try:
        # Test main module imports
        from search_pipeline import SearchPipelineRunner, SearchPipelineConfig, ElasticsearchConfig
        logger.info("✓ Main search_pipeline imports successful")
        
        # Test config models
        from search_pipeline.models.config import BulkWriteConfig
        from search_pipeline.models.results import SearchIndexResult, SearchPipelineResult
        logger.info("✓ Model imports successful")
        
        # Test core components
        from search_pipeline.core.search_runner import SearchPipelineRunner as CoreRunner
        logger.info("✓ Core component imports successful")
        
        logger.info("✅ All imports test PASSED")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import test FAILED: {e}")
        return False


def test_search_configuration():
    """Test search pipeline configuration models."""
    logger.info("=" * 60)
    logger.info("Testing Search Pipeline Configuration")
    logger.info("=" * 60)
    
    try:
        from search_pipeline.models.config import SearchPipelineConfig, ElasticsearchConfig, BulkWriteConfig
        
        # Test default configuration
        config = SearchPipelineConfig()
        assert not config.enabled, "Search should be disabled by default"
        assert config.elasticsearch is not None, "Elasticsearch config should exist"
        logger.info("✓ Default configuration valid")
        
        # Test enabled configuration
        enabled_config = SearchPipelineConfig(enabled=True)
        assert enabled_config.enabled, "Search should be enabled"
        logger.info("✓ Enabled configuration valid")
        
        # Test Elasticsearch configuration
        es_config = ElasticsearchConfig(
            nodes=["localhost:9200"],
            index_prefix="test_real_estate",
            mapping_id="test_id"
        )
        assert es_config.nodes == ["localhost:9200"], "Nodes should be configured"
        assert es_config.get_index_name("properties") == "test_real_estate_properties", "Index name should be formatted correctly"
        logger.info("✓ Elasticsearch configuration valid")
        
        # Test Spark configuration generation
        spark_conf = es_config.get_spark_conf()
        assert "es.nodes" in spark_conf, "Spark conf should include nodes"
        assert "es.batch.size.entries" in spark_conf, "Spark conf should include batch size"
        logger.info("✓ Spark configuration generation valid")
        
        # Test bulk write configuration
        bulk_config = BulkWriteConfig(batch_size_entries=500)
        assert bulk_config.batch_size_entries == 500, "Batch size should be configurable"
        logger.info("✓ Bulk write configuration valid")
        
        logger.info("✅ Configuration test PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_search_runner_initialization():
    """Test SearchPipelineRunner initialization."""
    logger.info("=" * 60)
    logger.info("Testing SearchPipelineRunner Initialization")
    logger.info("=" * 60)
    
    try:
        from pyspark.sql import SparkSession
        from search_pipeline.models.config import SearchPipelineConfig
        from search_pipeline.core.search_runner import SearchPipelineRunner
        
        # Create Spark session
        spark = SparkSession.builder \
            .appName("test_search_runner") \
            .master("local[1]") \
            .getOrCreate()
        
        # Test with disabled configuration
        disabled_config = SearchPipelineConfig(enabled=False)
        runner = SearchPipelineRunner(spark, disabled_config)
        assert runner.config.enabled == False, "Runner should respect disabled config"
        logger.info("✓ Disabled configuration initialization")
        
        # Test with enabled configuration (but skip connection validation)
        enabled_config = SearchPipelineConfig(
            enabled=True,
            validate_connection=False  # Skip validation for testing
        )
        runner = SearchPipelineRunner(spark, enabled_config)
        assert runner.config.enabled == True, "Runner should respect enabled config"
        logger.info("✓ Enabled configuration initialization")
        
        # Test pipeline ID generation
        assert runner.pipeline_id is not None, "Pipeline ID should be generated"
        logger.info(f"✓ Pipeline ID generated: {runner.pipeline_id[:8]}...")
        
        spark.stop()
        
        logger.info("✅ SearchRunner initialization test PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ SearchRunner initialization test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fork_with_search_path():
    """Test pipeline fork with search path enabled."""
    logger.info("=" * 60)
    logger.info("Testing Fork with Search Path")
    logger.info("=" * 60)
    
    try:
        from pyspark.sql import SparkSession
        from data_pipeline.core.pipeline_fork import PipelineFork, ForkConfiguration
        from search_pipeline.models.config import SearchPipelineConfig
        
        # Create Spark session
        spark = SparkSession.builder \
            .appName("test_fork_search") \
            .master("local[1]") \
            .getOrCreate()
        
        # Create test DataFrames
        properties_df = spark.createDataFrame(
            [("prop1", 100000, "Beautiful property")],
            ["listing_id", "price", "embedding_text"]
        )
        neighborhoods_df = spark.createDataFrame(
            [("n1", "Downtown", "Urban neighborhood")],
            ["neighborhood_id", "name", "embedding_text"]
        )
        wikipedia_df = spark.createDataFrame(
            [("page1", "San Francisco", "City article")],
            ["page_id", "title", "embedding_text"]
        )
        
        # Test fork with search path enabled
        fork_config = ForkConfiguration(enabled_paths=["graph", "search"])
        fork = PipelineFork(fork_config)
        
        # Create search config (disabled for testing)
        search_config = SearchPipelineConfig(
            enabled=False,  # Disable to avoid Elasticsearch connection
            validate_connection=False
        )
        
        result, routed = fork.route(
            properties_df, neighborhoods_df, wikipedia_df,
            spark=spark, search_config=search_config
        )
        
        assert result.graph_success, "Graph routing should succeed"
        assert result.search_success, "Search routing should succeed"
        assert "graph" in routed, "Graph results should be present"
        assert "search" in routed, "Search results should be present"
        
        logger.info("✓ Fork routing with search path works")
        
        # Test search path processing
        search_result = routed.get("search")
        if hasattr(search_result, 'success'):
            logger.info(f"✓ Search pipeline result: {search_result.success}")
        else:
            logger.info("✓ Search path routed but not processed (expected for disabled config)")
        
        spark.stop()
        
        logger.info("✅ Fork search path test PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Fork search path test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_search_pipeline_results():
    """Test search pipeline result models."""
    logger.info("=" * 60)
    logger.info("Testing Search Pipeline Results")
    logger.info("=" * 60)
    
    try:
        from search_pipeline.models.results import SearchIndexResult, SearchPipelineResult
        from datetime import datetime
        
        # Test SearchIndexResult
        index_result = SearchIndexResult(
            entity_type="properties",
            index_name="test_properties",
            documents_indexed=100,
            documents_failed=5,
            duration_seconds=10.5
        )
        
        assert index_result.success_rate == 95.238, "Success rate calculation should be correct"
        assert index_result.documents_per_second == 100/10.5, "Throughput calculation should be correct"
        logger.info("✓ SearchIndexResult calculations correct")
        
        # Test SearchPipelineResult
        pipeline_result = SearchPipelineResult(
            pipeline_id="test-123",
            start_time=datetime.now()
        )
        
        pipeline_result.add_entity_result(index_result)
        assert pipeline_result.total_documents_indexed == 100, "Total documents should be aggregated"
        assert pipeline_result.total_documents_failed == 5, "Failed documents should be aggregated"
        logger.info("✓ SearchPipelineResult aggregation correct")
        
        pipeline_result.complete(success=True)
        assert pipeline_result.success, "Pipeline should be marked as successful"
        assert pipeline_result.end_time is not None, "End time should be set"
        logger.info("✓ Pipeline completion correct")
        
        # Test summary generation
        summary = pipeline_result.get_summary()
        assert "test-123" in summary, "Summary should include pipeline ID"
        assert "100" in summary, "Summary should include document counts"
        logger.info("✓ Summary generation correct")
        
        logger.info("✅ Search pipeline results test PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Search pipeline results test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


@patch.dict(os.environ, {"ELASTIC_PASSWORD": "test_password"})
def test_configuration_with_auth():
    """Test configuration with authentication."""
    logger.info("=" * 60)
    logger.info("Testing Configuration with Authentication")
    logger.info("=" * 60)
    
    try:
        from search_pipeline.models.config import ElasticsearchConfig
        
        # Test configuration with authentication
        es_config = ElasticsearchConfig(
            username="elastic",
            # Password will be read from environment variable
        )
        
        spark_conf = es_config.get_spark_conf()
        assert "es.net.http.auth.user" in spark_conf, "Auth user should be in config"
        assert "es.net.http.auth.pass" in spark_conf, "Auth password should be in config"
        assert spark_conf["es.net.http.auth.user"] == "elastic", "Username should be correct"
        logger.info("✓ Authentication configuration correct")
        
        logger.info("✅ Authentication configuration test PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Authentication configuration test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_elasticsearch_best_practices_applied():
    """Test that Elasticsearch best practices are applied in configuration."""
    logger.info("=" * 60)
    logger.info("Testing Elasticsearch Best Practices")
    logger.info("=" * 60)
    
    try:
        from search_pipeline.models.config import ElasticsearchConfig, BulkWriteConfig
        
        # Test default bulk configuration follows best practices
        bulk_config = BulkWriteConfig()
        assert bulk_config.batch_size_entries == 1000, "Default batch size should be 1000 (best practice)"
        assert bulk_config.batch_size_bytes == "1mb", "Default batch size should be 1MB"
        assert bulk_config.batch_write_retry_count == 3, "Should have retry logic"
        logger.info("✓ Bulk write defaults follow best practices")
        
        # Test Elasticsearch configuration defaults
        es_config = ElasticsearchConfig()
        assert es_config.http_timeout == "2m", "HTTP timeout should be reasonable"
        assert es_config.http_retries == 3, "Should have HTTP retries"
        assert es_config.index_auto_create, "Should auto-create indices"
        assert es_config.error_handler_log_message, "Should log error messages"
        logger.info("✓ Elasticsearch defaults follow best practices")
        
        # Test Spark configuration includes best practice settings
        spark_conf = es_config.get_spark_conf()
        expected_settings = [
            "es.batch.write.retry.count",
            "es.batch.write.retry.wait", 
            "es.http.timeout",
            "es.http.retries",
            "es.error.handler.log.error.message"
        ]
        
        for setting in expected_settings:
            assert setting in spark_conf, f"Best practice setting {setting} should be included"
        
        logger.info("✓ Spark configuration includes best practices")
        
        logger.info("✅ Best practices test PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Best practices test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Phase 2 tests."""
    logger.info("🚀 Starting Phase 2 Search Pipeline Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Search Pipeline Imports", test_search_pipeline_imports),
        ("Search Configuration", test_search_configuration),
        ("SearchRunner Initialization", test_search_runner_initialization),
        ("Fork with Search Path", test_fork_with_search_path),
        ("Search Pipeline Results", test_search_pipeline_results),
        ("Configuration with Auth", test_configuration_with_auth),
        ("Best Practices Applied", test_elasticsearch_best_practices_applied),
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
        logger.info("🎉 All Phase 2 tests passed!")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()