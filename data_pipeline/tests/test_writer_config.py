"""
Tests for writer configuration models and orchestrator.
"""

import pytest
from unittest.mock import Mock, MagicMock
from pyspark.sql import SparkSession

from data_pipeline.config.models import (
    Neo4jConfig,
    ElasticsearchConfig,
    ParquetWriterConfig,
    OutputDestinationsConfig,
    PipelineConfig
)
from data_pipeline.writers.base import DataWriter, WriterConfig
from data_pipeline.writers.orchestrator import WriterOrchestrator


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
        """Test Parquet writer configuration with defaults."""
        config = ParquetWriterConfig()
        assert config.enabled is True
        assert config.path == "data/processed/entity_datasets"
        assert config.partitioning_columns == ["source_entity"]
        assert config.compression == "snappy"
        assert config.mode == "overwrite"
    
    def test_output_destinations_config(self):
        """Test output destinations configuration."""
        config = OutputDestinationsConfig()
        assert config.enabled_destinations == ["parquet"]
        assert isinstance(config.parquet, ParquetWriterConfig)
        assert isinstance(config.neo4j, Neo4jConfig)
        assert isinstance(config.elasticsearch, ElasticsearchConfig)
    
    def test_pipeline_config_with_destinations(self):
        """Test pipeline configuration includes output destinations."""
        config = PipelineConfig()
        assert hasattr(config, 'output_destinations')
        assert isinstance(config.output_destinations, OutputDestinationsConfig)
    
    def test_environment_variable_substitution(self):
        """Test password environment variable substitution."""
        import os
        os.environ['NEO4J_PASSWORD'] = 'test_password'
        
        config = Neo4jConfig(password="${NEO4J_PASSWORD}")
        assert config.get_password() == 'test_password'
        
        # Clean up
        del os.environ['NEO4J_PASSWORD']


class MockWriter(DataWriter):
    """Mock writer for testing orchestrator."""
    
    def __init__(self, name: str, enabled: bool = True, should_fail: bool = False):
        config = WriterConfig(enabled=enabled)
        super().__init__(config)
        self.name = name
        self.should_fail = should_fail
        self.write_called = False
        self.validate_called = False
    
    def validate_connection(self) -> bool:
        self.validate_called = True
        return not self.should_fail
    
    def write(self, df, metadata) -> bool:
        self.write_called = True
        return not self.should_fail
    
    def get_writer_name(self) -> str:
        return self.name


class TestWriterOrchestrator:
    """Test writer orchestrator functionality."""
    
    def test_orchestrator_initialization(self):
        """Test orchestrator initialization."""
        writers = [
            MockWriter("writer1"),
            MockWriter("writer2")
        ]
        orchestrator = WriterOrchestrator(writers)
        assert len(orchestrator.writers) == 2
        assert orchestrator.get_all_writers() == ["writer1", "writer2"]
    
    def test_orchestrator_sequential_write(self):
        """Test sequential write to all destinations."""
        writers = [
            MockWriter("writer1"),
            MockWriter("writer2"),
            MockWriter("writer3")
        ]
        orchestrator = WriterOrchestrator(writers)
        
        # Create mock DataFrame
        mock_df = Mock()
        metadata = {"test": "metadata"}
        
        # Execute write
        orchestrator.write_to_all(mock_df, metadata)
        
        # Verify all writers were called
        for writer in writers:
            assert writer.write_called is True
    
    def test_orchestrator_fail_fast(self):
        """Test fail-fast behavior when a writer fails."""
        writers = [
            MockWriter("writer1"),
            MockWriter("writer2", should_fail=True),
            MockWriter("writer3")
        ]
        orchestrator = WriterOrchestrator(writers)
        
        mock_df = Mock()
        metadata = {"test": "metadata"}
        
        # Should raise RuntimeError when writer2 fails
        with pytest.raises(RuntimeError) as exc_info:
            orchestrator.write_to_all(mock_df, metadata)
        
        assert "Failed to write to writer2" in str(exc_info.value)
        
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
        metadata = {"test": "metadata"}
        
        # Execute write
        orchestrator.write_to_all(mock_df, metadata)
        
        # Verify only enabled writers were called
        assert writers[0].write_called is True
        assert writers[1].write_called is False  # Disabled
        assert writers[2].write_called is True
    
    def test_orchestrator_validate_connections(self):
        """Test connection validation for all writers."""
        writers = [
            MockWriter("writer1"),
            MockWriter("writer2"),
            MockWriter("writer3")
        ]
        orchestrator = WriterOrchestrator(writers)
        
        # Validate all connections
        orchestrator.validate_all_connections()
        
        # Verify all writers validated
        for writer in writers:
            assert writer.validate_called is True
    
    def test_orchestrator_validate_fails(self):
        """Test validation failure handling."""
        writers = [
            MockWriter("writer1"),
            MockWriter("writer2", should_fail=True),
            MockWriter("writer3")
        ]
        orchestrator = WriterOrchestrator(writers)
        
        # Should raise RuntimeError when validation fails
        with pytest.raises(RuntimeError) as exc_info:
            orchestrator.validate_all_connections()
        
        assert "Connection validation failed for writer2" in str(exc_info.value)