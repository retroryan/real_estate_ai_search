"""
Simple integration test for Elasticsearch writer.

Tests basic connectivity, data writing, and field validation.
"""

import pytest
from pyspark.sql import SparkSession
from unittest.mock import Mock

from data_pipeline.writers.elasticsearch.elasticsearch_orchestrator import ElasticsearchOrchestrator
from data_pipeline.config.models import ElasticsearchConfig
from data_pipeline.models.writer_models import WriteMetadata, EntityType


class TestElasticsearchIntegration:
    """Test Elasticsearch writer integration."""
    
    def test_elasticsearch_writer_initialization(self, spark_session):
        """Test that Elasticsearch writer initializes correctly."""
        config = ElasticsearchConfig(
            enabled=True,
            hosts=["localhost:9200"],
            index_prefix="test",
            bulk_size=100,
            clear_before_write=True
        )
        
        writer = ElasticsearchOrchestrator(config, spark_session)
        
        assert writer.config == config
        assert writer.spark == spark_session
        assert writer.format_string == "es"
        assert writer.get_writer_name() == "elasticsearch"
    
    def test_geo_point_transformation(self, spark_session):
        """Test that latitude/longitude are properly transformed to geo_point."""
        config = ElasticsearchConfig(
            enabled=True,
            hosts=["localhost:9200"],
            index_prefix="test",
            bulk_size=100
        )
        
        writer = ElasticsearchOrchestrator(config, spark_session)
        
        # Create test DataFrame with coordinates
        test_data = [
            {"id": "1", "latitude": 37.7749, "longitude": -122.4194, "name": "San Francisco"},
            {"id": "2", "latitude": None, "longitude": -122.4194, "name": "Invalid"}
        ]
        df = spark_session.createDataFrame(test_data)
        
        # Apply geo_point transformation
        result_df = writer._add_geo_point(df)
        
        # Collect results
        results = result_df.collect()
        
        # Validate first row has proper geo_point structure
        assert "location" in result_df.columns
        first_row = results[0]
        assert first_row.location is not None
        assert first_row.location.lat == 37.7749
        assert first_row.location.lon == -122.4194
        
        # Validate second row has null location due to missing latitude
        second_row = results[1]
        assert second_row.location is None
    
    def test_prepare_dataframe(self, spark_session):
        """Test DataFrame preparation including ID mapping and geo_point."""
        config = ElasticsearchConfig(
            enabled=True,
            hosts=["localhost:9200"],
            index_prefix="test",
            bulk_size=100
        )
        
        writer = ElasticsearchOrchestrator(config, spark_session)
        
        # Create test DataFrame
        test_data = [
            {"listing_id": "prop_1", "city": "Seattle", "latitude": 47.6062, "longitude": -122.3321, "price": 500000}
        ]
        df = spark_session.createDataFrame(test_data)
        
        # Prepare DataFrame
        result_df = writer._prepare_dataframe(df, "listing_id")
        
        # Validate transformations
        assert "id" in result_df.columns
        assert "location" in result_df.columns
        
        row = result_df.collect()[0]
        assert row.id == "prop_1"
        assert row.location.lat == 47.6062
        assert row.location.lon == -122.3321
    
    def test_write_mode_configuration(self, spark_session):
        """Test write mode determination based on clear_before_write setting."""
        # Test with clear_before_write = True
        config_overwrite = ElasticsearchConfig(
            enabled=True,
            hosts=["localhost:9200"],
            clear_before_write=True
        )
        writer_overwrite = ElasticsearchOrchestrator(config_overwrite, spark_session)
        assert writer_overwrite._get_write_mode() == "overwrite"
        
        # Test with clear_before_write = False
        config_append = ElasticsearchConfig(
            enabled=True,
            hosts=["localhost:9200"],
            clear_before_write=False
        )
        writer_append = ElasticsearchOrchestrator(config_append, spark_session)
        assert writer_append._get_write_mode() == "append"
    
    def test_session_config_validation(self, spark_session):
        """Test validation of session-level Elasticsearch configuration."""
        config = ElasticsearchConfig(
            enabled=True,
            hosts=["localhost:9200"],
            index_prefix="test"
        )
        
        writer = ElasticsearchOrchestrator(config, spark_session)
        
        # Mock spark configuration without es.nodes
        mock_conf = Mock()
        mock_conf.get.return_value = None
        spark_session.sparkContext.getConf = Mock(return_value=mock_conf)
        
        # Validation should fail without session config
        result = writer.validate_connection()
        assert result is False
    
    def test_empty_dataframe_handling(self, spark_session):
        """Test handling of empty DataFrames."""
        config = ElasticsearchConfig(
            enabled=True,
            hosts=["localhost:9200"],
            index_prefix="test"
        )
        
        writer = ElasticsearchOrchestrator(config, spark_session)
        
        # Create empty DataFrame
        empty_df = spark_session.createDataFrame([], schema="listing_id STRING, city STRING")
        metadata = WriteMetadata(entity_type=EntityType.PROPERTY)
        
        # Should return True for empty DataFrame without attempting write
        result = writer._write_properties(empty_df, metadata)
        assert result is True


def test_quick_elasticsearch_smoke():
    """Quick smoke test for Elasticsearch writer without external dependencies."""
    # Test basic configuration validation
    config = ElasticsearchConfig(
        enabled=True,
        hosts=["localhost:9200"],
        index_prefix="test_smoke",
        bulk_size=50,
        clear_before_write=True
    )
    
    # Validate configuration
    assert config.enabled is True
    assert config.hosts == ["localhost:9200"]
    assert config.index_prefix == "test_smoke"
    assert config.bulk_size == 50
    assert config.get_password() is None  # No password configured


if __name__ == "__main__":
    # Allow running this test directly
    pytest.main([__file__, "-v"])