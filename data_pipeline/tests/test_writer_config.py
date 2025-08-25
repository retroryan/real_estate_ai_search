"""
Tests for writer configuration models and orchestrator.
"""

import pytest
from unittest.mock import Mock, MagicMock
from pyspark.sql import SparkSession

from data_pipeline.config.pipeline_config import (
    Neo4jConfig,
    ElasticsearchConfig,
    ParquetWriterConfig,
    OutputDestinationsConfig,
    PipelineConfig
)
from data_pipeline.writers.base import EntityWriter, WriterConfig
from data_pipeline.writers.orchestrator import WriterOrchestrator
from data_pipeline.models.writer_models import (
    EntityType,
    WriteMetadata,
    WriteRequest,
)


class TestWriterConfiguration:
    """Test writer configuration models."""
    
    def test_neo4j_config_defaults(self):
        """Test Neo4j configuration with defaults."""
        config = Neo4jConfig()
        assert config.enabled is True
        assert config.uri == "bolt://localhost:7687"
        assert config.username == "neo4j"
        assert config.database == "neo4j"
        assert config.transaction_size == 1000
        assert config.clear_before_write is True
    
    def test_elasticsearch_config_defaults(self):
        """Test Elasticsearch configuration with defaults."""
        config = ElasticsearchConfig()
        assert config.enabled is True
        assert config.hosts == ["localhost:9200"]
        assert config.index_prefix == "realestate"
        assert config.bulk_size == 500
        assert config.clear_before_write is True
    
    def test_parquet_config_defaults(self):
        """Test Parquet writer configuration with entity-specific settings."""
        config = ParquetWriterConfig()
        assert config.enabled is True
        assert config.base_path == "data/entities"
        assert config.compression == "snappy"
        assert config.mode == "overwrite"
        # Check entity-specific configs
        assert config.properties.path == "properties"
        assert config.properties.partition_by == ["state", "city"]
        assert config.neighborhoods.path == "neighborhoods"
        assert config.neighborhoods.partition_by == ["state"]
        assert config.wikipedia.path == "wikipedia"
        assert config.wikipedia.partition_by == ["best_state"]
    
    def test_output_destinations_config(self):
        """Test output destinations configuration."""
        config = OutputDestinationsConfig()
        assert config.enabled_destinations == ["parquet"]
        assert config.parquet.enabled is True
        assert config.neo4j.enabled is True
        assert config.elasticsearch.enabled is True
    
    def test_password_resolution(self):
        """Test password resolution from environment variables."""
        import os
        os.environ["TEST_NEO4J_PASS"] = "secret_password"
        
        config = Neo4jConfig(password="${TEST_NEO4J_PASS}")
        assert config.get_password() == "secret_password"
        
        # Clean up
        del os.environ["TEST_NEO4J_PASS"]


class MockWriter(EntityWriter):
    """Mock writer for testing orchestrator."""
    
    def __init__(self, name: str, enabled: bool = True, should_fail: bool = False):
        super().__init__(WriterConfig(enabled=enabled))
        self.name = name
        self.should_fail = should_fail
        self.write_called = False
        self.validated = False
    
    def validate_connection(self) -> bool:
        self.validated = True
        return not self.should_fail
    
    def write(self, df, metadata: WriteMetadata) -> bool:
        self.write_called = True
        if self.should_fail:
            return False
        return True
    
    def get_writer_name(self) -> str:
        return self.name


class TestWriterOrchestrator:
    """Test writer orchestrator functionality."""
    
    def test_orchestrator_initialization(self):
        """Test orchestrator initialization with writers."""
        writers = [
            MockWriter("writer1"),
            MockWriter("writer2"),
            MockWriter("writer3")
        ]
        orchestrator = WriterOrchestrator(writers)
        
        assert len(orchestrator.get_all_writers()) == 3
        assert orchestrator.get_enabled_writers() == ["writer1", "writer2", "writer3"]
    
    def test_orchestrator_write_all(self):
        """Test writing to all configured destinations with type-safe API."""
        writers = [
            MockWriter("writer1"),
            MockWriter("writer2"),
            MockWriter("writer3")
        ]
        orchestrator = WriterOrchestrator(writers)
        
        # Create mock DataFrame
        mock_df = Mock()
        mock_df.count.return_value = 100
        
        # Create type-safe request
        write_metadata = WriteMetadata(
            pipeline_name="test_pipeline",
            pipeline_version="1.0.0",
            entity_type=EntityType.PROPERTY,
            record_count=100
        )
        request = WriteRequest(
            entity_type=EntityType.PROPERTY,
            dataframe=mock_df,
            metadata=write_metadata
        )
        
        # Execute write
        results = orchestrator.write_entity(request)
        
        # Verify all writers were called
        for writer in writers:
            assert writer.write_called is True
        
        # Verify results
        assert len(results) == 3
        for result in results:
            assert result.success is True
            assert result.records_written == 100
    
    def test_orchestrator_fail_fast(self):
        """Test fail-fast behavior when a writer fails."""
        writers = [
            MockWriter("writer1"),
            MockWriter("writer2", should_fail=True),
            MockWriter("writer3")
        ]
        orchestrator = WriterOrchestrator(writers)
        
        mock_df = Mock()
        mock_df.count.return_value = 100
        
        # Create type-safe request
        write_metadata = WriteMetadata(
            pipeline_name="test_pipeline",
            pipeline_version="1.0.0",
            entity_type=EntityType.PROPERTY,
            record_count=100
        )
        request = WriteRequest(
            entity_type=EntityType.PROPERTY,
            dataframe=mock_df,
            metadata=write_metadata
        )
        
        # Should raise RuntimeError when writer2 fails
        with pytest.raises(RuntimeError) as exc_info:
            orchestrator.write_entity(request)
        
        assert "Failed to write property to writer2" in str(exc_info.value)
        
        # Verify writer1 was called but writer3 was not (fail-fast)
        assert writers[0].write_called is True
        assert writers[1].write_called is True
        assert writers[2].write_called is False
    
    def test_orchestrator_disabled_writers(self):
        """Test that disabled writers are skipped."""
        writers = [
            MockWriter("writer1"),
            MockWriter("writer2", enabled=False),
            MockWriter("writer3")
        ]
        orchestrator = WriterOrchestrator(writers)
        
        # Check enabled writers
        assert orchestrator.get_enabled_writers() == ["writer1", "writer3"]
        
        mock_df = Mock()
        mock_df.count.return_value = 100
        
        # Create type-safe request
        write_metadata = WriteMetadata(
            pipeline_name="test_pipeline",
            pipeline_version="1.0.0",
            entity_type=EntityType.PROPERTY,
            record_count=100
        )
        request = WriteRequest(
            entity_type=EntityType.PROPERTY,
            dataframe=mock_df,
            metadata=write_metadata
        )
        
        # Execute write
        results = orchestrator.write_entity(request)
        
        # Verify only enabled writers were called
        assert writers[0].write_called is True
        assert writers[1].write_called is False  # Disabled
        assert writers[2].write_called is True
        
        # Verify results only include enabled writers
        assert len(results) == 2
    
    def test_orchestrator_validate_connections(self):
        """Test connection validation for all writers."""
        writers = [
            MockWriter("writer1"),
            MockWriter("writer2"),
            MockWriter("writer3", enabled=False)
        ]
        orchestrator = WriterOrchestrator(writers)
        
        # Validate all connections
        orchestrator.validate_all_connections()
        
        # Verify only enabled writers were validated
        assert writers[0].validated is True
        assert writers[1].validated is True
        assert writers[2].validated is False  # Disabled
    
    def test_orchestrator_write_dataframes(self):
        """Test convenience method for writing multiple entity DataFrames."""
        writers = [MockWriter("writer1")]
        orchestrator = WriterOrchestrator(writers)
        
        # Create mock DataFrames
        mock_properties = Mock()
        mock_properties.count.return_value = 100
        
        mock_neighborhoods = Mock()
        mock_neighborhoods.count.return_value = 50
        
        # Use convenience method
        result = orchestrator.write_dataframes(
            properties_df=mock_properties,
            neighborhoods_df=mock_neighborhoods,
            wikipedia_df=None,  # Test with None
            pipeline_name="test_pipeline",
            pipeline_version="1.0.0",
            environment="test"
        )
        
        # Verify session result
        assert result.all_successful()
        assert result.total_records_written == 150
        assert result.successful_writes == 2
        assert result.failed_writes == 0