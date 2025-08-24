"""
Pytest configuration for data pipeline integration tests.
"""

import tempfile
from pathlib import Path

import pytest
from pyspark.sql import SparkSession



@pytest.fixture(scope="session")
def spark_session():
    """Create a Spark session for the entire test session."""
    spark = SparkSession.builder \
        .appName("DataPipelineIntegrationTests") \
        .master("local[2]") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .config("spark.sql.execution.arrow.pyspark.enabled", "false") \
        .getOrCreate()
    
    # Set log level to reduce noise during testing
    spark.sparkContext.setLogLevel("WARN")
    
    yield spark
    
    spark.stop()


@pytest.fixture(scope="session")
def test_settings():
    """Create test settings with appropriate overrides.""" 
    from data_pipeline.config.settings import ConfigurationManager
    config_manager = ConfigurationManager(environment="test")
    settings = config_manager.load_config()
    
    # Override settings for testing (don't modify environment field, it's not writable)
    settings.data_subset.enabled = True
    settings.data_subset.sample_size = 15  # Small dataset for faster tests
    
    return settings


@pytest.fixture(scope="function")
def temp_output_directory():
    """Create a temporary directory for each test."""
    with tempfile.TemporaryDirectory(prefix="pipeline_test_") as temp_dir:
        yield Path(temp_dir)


@pytest.fixture(scope="function")
def test_settings_with_temp_output(test_settings, temp_output_directory):
    """Test settings with temporary output directory."""
    # Create a copy of settings to avoid modifying the original
    import copy
    settings_copy = copy.deepcopy(test_settings)
    
    # Override output_destinations to use temporary directory for Parquet output
    # Enable only Parquet output for testing
    settings_copy.output_destinations.enabled_destinations = ["parquet"]
    
    # Configure Parquet destination with temporary directory
    settings_copy.output_destinations.parquet.enabled = True
    settings_copy.output_destinations.parquet.base_path = str(temp_output_directory)
    settings_copy.output_destinations.parquet.mode = "overwrite"
    settings_copy.output_destinations.parquet.compression = "snappy"
    
    return settings_copy


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", 
        "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers",
        "parquet: mark test as parquet-related"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark integration tests."""
    for item in items:
        if "integration_tests" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
            
        # Mark tests that involve full pipeline runs as slow
        if any(keyword in item.name.lower() for keyword in ["pipeline", "full", "complete"]):
            item.add_marker(pytest.mark.slow)