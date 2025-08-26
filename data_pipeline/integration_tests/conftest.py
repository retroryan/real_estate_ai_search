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
def spark():
    """Alias for spark_session to match test expectations."""
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
    from pathlib import Path
    import yaml
    from data_pipeline.config.models import PipelineConfig
    
    # Load test-specific configuration
    test_config_path = Path(__file__).parent / "test_config.yaml"
    
    if test_config_path.exists():
        # Use test-specific config if available
        with open(test_config_path, "r") as f:
            config_dict = yaml.safe_load(f)
        settings = PipelineConfig(**config_dict)
    else:
        # Fallback to loading main config with overrides
        from data_pipeline.config.loader import load_configuration
        from data_pipeline.config.models import EmbeddingProvider
        settings = load_configuration(sample_size=None)
        settings.embedding.provider = EmbeddingProvider.MOCK  # Use mock for tests
        settings.output.enabled_destinations = ["parquet"]  # Disable Neo4j for tests
    
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
    
    # Override output to use temporary directory for Parquet output
    # Enable only Parquet output for testing
    settings_copy.output.enabled_destinations = ["parquet"]
    
    # Configure Parquet destination with temporary directory
    settings_copy.output.parquet.base_path = str(temp_output_directory)
    settings_copy.output.parquet.compression = "snappy"
    
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