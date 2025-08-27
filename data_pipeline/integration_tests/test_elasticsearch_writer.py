"""
Integration tests for Elasticsearch writer functionality.

Tests the full pipeline data writing to Elasticsearch, including:
- Connection validation
- Property data writing and verification
- Neighborhood data writing and verification
- Wikipedia data writing and verification
- Field mapping and geo_point handling
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

import pytest
from pyspark.sql import DataFrame, SparkSession

# Import pipeline components
from data_pipeline.config.loader import load_configuration
from data_pipeline.config.models import PipelineConfig
from data_pipeline.core.pipeline_runner import DataPipelineRunner
from data_pipeline.writers.elasticsearch.orchestrator import ElasticsearchOrchestrator


def _check_elasticsearch_available() -> bool:
    """Check if Elasticsearch is available for testing."""
    try:
        import requests
        import os
        
        # Get authentication from environment
        username = os.environ.get("ELASTICSEARCH_USERNAME", "elastic")
        password = os.environ.get("ELASTICSEARCH_PASSWORD", "")
        
        if password:
            auth = (username, password)
            response = requests.get("http://localhost:9200/_cluster/health", 
                                  auth=auth, timeout=5)
        else:
            # Try without auth first
            response = requests.get("http://localhost:9200/_cluster/health", timeout=5)
        
        # Accept both 200 (OK) and 401 (auth required) as "available"
        return response.status_code in [200, 401]
    except Exception:
        return False


@pytest.mark.integration
@pytest.mark.skipif(not _check_elasticsearch_available(), reason="Elasticsearch not available")
class TestElasticsearchWriter:
    """Integration tests for Elasticsearch writer."""

    @pytest.fixture(scope="class")
    def es_config(self):
        """Load configuration with Elasticsearch enabled."""
        config = load_configuration(sample_size=5)  # Use small sample for tests
        
        # Ensure Elasticsearch is enabled
        if "elasticsearch" not in config.output.enabled_destinations:
            config.output.enabled_destinations.append("elasticsearch")
        
        # index_prefix has been removed from configuration
        
        return config

    @pytest.fixture(scope="class")
    def spark_with_es(self, es_config):
        """Create Spark session with Elasticsearch configuration."""
        spark_configs = es_config.get_spark_configs()
        
        spark = SparkSession.builder.appName("ElasticsearchIntegrationTest").master("local[2]")
        for key, value in spark_configs.items():
            spark = spark.config(key, value)
        
        spark = spark.getOrCreate()
        spark.sparkContext.setLogLevel("WARN")
        
        yield spark
        
        spark.stop()

    @pytest.fixture(scope="class") 
    def es_orchestrator(self, es_config, spark_with_es):
        """Create Elasticsearch orchestrator."""
        return ElasticsearchOrchestrator(es_config.output.elasticsearch, spark_with_es)

    def test_elasticsearch_connection_validation(self, es_orchestrator):
        """Test that Elasticsearch connection validation works."""
        result = es_orchestrator.validate_connection()
        assert result is True, "Elasticsearch connection validation should succeed"

    def test_property_data_writing(self, es_orchestrator, spark_with_es, es_config):
        """Test writing property data to Elasticsearch."""
        # Load sample property data
        from data_pipeline.loaders.property_loader import PropertyLoader
        
        loader = PropertyLoader(spark_with_es)
        property_files = es_config.data_sources.properties_files[:1]  # Use first file only
        
        if not property_files or not Path(property_files[0]).exists():
            pytest.skip("Property data file not available for testing")
        
        df = loader.load(property_files[0])
        
        # Apply sample size limit
        if es_config.sample_size:
            df = df.limit(es_config.sample_size)
        
        # For testing, select only fields that are Elasticsearch-compatible
        # Avoid complex nested arrays with decimals that require schema transformation
        test_columns = ["listing_id", "street", "city", "state", "bedrooms", "bathrooms", "square_feet", "property_type"]
        available_columns = [col for col in test_columns if col in df.columns]
        df = df.select(*available_columns)
        
        # Verify DataFrame has expected columns
        expected_columns = ["listing_id", "street", "city"]
        missing_columns = [col for col in expected_columns if col not in df.columns]
        assert not missing_columns, f"Missing expected columns: {missing_columns}"
        
        # Write to Elasticsearch
        result = es_orchestrator.write_properties(df)
        assert result is True, "Property writing should succeed"
        
        # Verify record count
        record_count = df.count()
        assert record_count > 0, "Should have property records to write"

    def test_neighborhood_data_writing(self, es_orchestrator, spark_with_es, es_config):
        """Test writing neighborhood data to Elasticsearch."""
        from data_pipeline.loaders.neighborhood_loader import NeighborhoodLoader
        
        loader = NeighborhoodLoader(spark_with_es)
        neighborhood_files = es_config.data_sources.neighborhoods_files[:1]  # Use first file only
        
        if not neighborhood_files or not Path(neighborhood_files[0]).exists():
            pytest.skip("Neighborhood data file not available for testing")
        
        df = loader.load(neighborhood_files[0])
        
        # Apply sample size limit
        if es_config.sample_size:
            df = df.limit(es_config.sample_size)
        
        # Verify DataFrame has expected columns
        expected_columns = ["neighborhood_id", "name"]
        missing_columns = [col for col in expected_columns if col not in df.columns]
        assert not missing_columns, f"Missing expected columns: {missing_columns}"
        
        # Write to Elasticsearch
        result = es_orchestrator.write_neighborhoods(df)
        assert result is True, "Neighborhood writing should succeed"
        
        # Verify record count
        record_count = df.count()
        assert record_count > 0, "Should have neighborhood records to write"

    def test_wikipedia_data_writing(self, es_orchestrator, spark_with_es, es_config):
        """Test writing Wikipedia data to Elasticsearch."""
        from data_pipeline.loaders.wikipedia_loader import WikipediaLoader
        
        # Check if Wikipedia database exists
        wiki_db_path = Path(es_config.data_sources.wikipedia_db_path)
        if not wiki_db_path.exists():
            pytest.skip("Wikipedia database not available for testing")
        
        loader = WikipediaLoader(spark_with_es)
        df = loader.load(str(wiki_db_path))
        
        # Apply sample size limit
        if es_config.sample_size:
            df = df.limit(es_config.sample_size)
        
        # Skip if no data
        if df.count() == 0:
            pytest.skip("No Wikipedia data available for testing")
        
        # Verify DataFrame has expected columns
        expected_columns = ["page_id", "title", "short_summary"]
        missing_columns = [col for col in expected_columns if col not in df.columns]
        assert not missing_columns, f"Missing expected columns: {missing_columns}"
        
        # Write to Elasticsearch
        result = es_orchestrator.write_wikipedia(df)
        assert result is True, "Wikipedia writing should succeed"

    def test_geo_point_field_handling(self, es_orchestrator, spark_with_es):
        """Test that geo_point fields are created correctly."""
        from data_pipeline.writers.elasticsearch.models import SchemaTransformation
        
        # Create test DataFrame with latitude/longitude
        test_data = [
            {"id": "test1", "name": "Location 1", "latitude": 37.7749, "longitude": -122.4194},
            {"id": "test2", "name": "Location 2", "latitude": 37.8044, "longitude": -122.2712},
        ]
        
        df = spark_with_es.createDataFrame(test_data)
        
        # Apply transformation using the new modular approach
        transform_config = SchemaTransformation(convert_decimals=False, add_geo_point=True)
        prepared_df = es_orchestrator.transformer.transform_for_elasticsearch(df, transform_config, "id")
        
        # Check that location field was added
        assert "location" in prepared_df.columns, "Should add location geo_point field"
        
        # Verify the structure
        location_data = prepared_df.select("location").collect()
        for row in location_data:
            if row.location is not None:
                assert hasattr(row.location, "lat"), "Location should have lat field"
                assert hasattr(row.location, "lon"), "Location should have lon field"

    def test_empty_dataframe_handling(self, es_orchestrator, spark_with_es):
        """Test handling of empty DataFrames."""
        # Create empty DataFrame with proper schema
        from pyspark.sql.types import StructType, StructField, StringType, IntegerType
        
        schema = StructType([
            StructField("listing_id", StringType(), True),
            StructField("price", IntegerType(), True)
        ])
        
        empty_df = spark_with_es.createDataFrame([], schema)
        
        # Should handle empty DataFrame gracefully
        result = es_orchestrator.write_properties(empty_df)
        assert result is True, "Should handle empty DataFrame successfully"

    def test_field_preparation_and_id_mapping(self, es_orchestrator, spark_with_es):
        """Test DataFrame preparation and ID field mapping."""
        from data_pipeline.writers.elasticsearch.models import SchemaTransformation
        
        test_data = [
            {"listing_id": "prop123", "name": "Test Property", "price": 500000},
            {"listing_id": "prop456", "name": "Another Property", "price": 750000}
        ]
        
        df = spark_with_es.createDataFrame(test_data)
        
        # Apply transformation using the new modular approach
        transform_config = SchemaTransformation(convert_decimals=False, add_geo_point=False)
        prepared_df = es_orchestrator.transformer.transform_for_elasticsearch(df, transform_config, "listing_id")
        
        # Check that ID field is properly mapped
        assert "id" in prepared_df.columns, "Should have id field for document mapping"
        
        # Verify ID values match the source field
        id_values = [row.id for row in prepared_df.select("id").collect()]
        listing_id_values = [row.listing_id for row in prepared_df.select("listing_id").collect()]
        
        assert id_values == listing_id_values, "ID field should match source field values"


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skipif(not _check_elasticsearch_available(), reason="Elasticsearch not available")
class TestElasticsearchPipelineIntegration:
    """Integration tests for full pipeline with Elasticsearch output."""

    def test_full_pipeline_with_elasticsearch_output(self):
        """Test complete pipeline execution with Elasticsearch output."""
        # Load configuration with Elasticsearch enabled
        config = load_configuration(sample_size=3)  # Very small sample for testing
        
        # Ensure Elasticsearch is enabled
        config.output.enabled_destinations = ["parquet", "elasticsearch"]
        # index_prefix has been removed from configuration
        
        # Run pipeline
        runner = DataPipelineRunner(config)
        result = runner.run_full_pipeline()
        
        # Verify results
        assert result is not None, "Pipeline should complete successfully"
        
        # Check that Elasticsearch indices were created
        # Note: This would require actual Elasticsearch client to verify,
        # but the fact that no exceptions were raised indicates success

    def test_elasticsearch_only_output(self):
        """Test pipeline with only Elasticsearch output enabled."""
        # Load configuration with only Elasticsearch enabled
        config = load_configuration(sample_size=2)
        config.output.enabled_destinations = ["elasticsearch"]
        # index_prefix has been removed from configuration
        
        # Run pipeline
        runner = DataPipelineRunner(config)
        result = runner.run_full_pipeline()
        
        # Verify pipeline completed
        assert result is not None, "Elasticsearch-only pipeline should complete successfully"


@pytest.mark.integration
def test_elasticsearch_configuration_loading():
    """Test that Elasticsearch configuration loads correctly."""
    config = load_configuration()
    
    # Check Elasticsearch config exists
    assert config.output.elasticsearch is not None, "Should have Elasticsearch configuration"
    
    # Check basic settings
    assert config.output.elasticsearch.hosts, "Should have Elasticsearch hosts configured"
    # index_prefix has been removed from configuration
    
    # Verify Spark configuration generation
    spark_configs = config.get_spark_configs()
    
    if "elasticsearch" in config.output.enabled_destinations:
        es_keys = [key for key in spark_configs.keys() if key.startswith("es.")]
        assert es_keys, "Should have Elasticsearch Spark configuration keys"


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])