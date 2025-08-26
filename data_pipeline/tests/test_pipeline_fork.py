"""
Unit tests for the output-driven pipeline fork implementation.

Tests the PipelineFork class and ProcessingPaths for correct
determination of processing paths from output destinations.
"""

import pytest
from unittest.mock import Mock, MagicMock
from pyspark.sql import SparkSession, DataFrame

from data_pipeline.core.pipeline_fork import (
    PipelineFork,
    ProcessingPaths,
    ProcessingResult
)


@pytest.fixture
def spark():
    """Create a test Spark session."""
    return SparkSession.builder \
        .appName("test_pipeline_fork") \
        .master("local[1]") \
        .getOrCreate()


@pytest.fixture
def mock_entities():
    """Create mock entity DataFrames for testing."""
    properties_df = Mock(spec=DataFrame)
    properties_df.columns = ['listing_id', 'price', 'embedding_text']
    
    neighborhoods_df = Mock(spec=DataFrame)
    neighborhoods_df.columns = ['neighborhood_id', 'name', 'embedding_text']
    
    wikipedia_df = Mock(spec=DataFrame)
    wikipedia_df.columns = ['page_id', 'title', 'embedding_text']
    
    return {
        'properties': properties_df,
        'neighborhoods': neighborhoods_df,
        'wikipedia': wikipedia_df
    }


class TestProcessingPaths:
    """Test the ProcessingPaths model."""
    
    def test_parquet_only_lightweight(self):
        """Test that parquet-only destinations result in lightweight path."""
        paths = ProcessingPaths.from_destinations(["parquet"])
        assert paths.lightweight
        assert not paths.graph
        assert not paths.search
        assert paths.get_enabled_paths() == ["lightweight"]
    
    def test_neo4j_graph_path(self):
        """Test that neo4j destination enables graph path."""
        paths = ProcessingPaths.from_destinations(["neo4j"])
        assert not paths.lightweight
        assert paths.graph
        assert not paths.search
        assert paths.get_enabled_paths() == ["graph"]
    
    def test_elasticsearch_search_path(self):
        """Test that elasticsearch destination enables search path."""
        paths = ProcessingPaths.from_destinations(["elasticsearch"])
        assert not paths.lightweight
        assert not paths.graph
        assert paths.search
        assert paths.get_enabled_paths() == ["search"]
    
    def test_multiple_destinations(self):
        """Test multiple destinations enable corresponding paths."""
        paths = ProcessingPaths.from_destinations(["neo4j", "elasticsearch", "parquet"])
        assert not paths.lightweight  # Not parquet-only
        assert paths.graph
        assert paths.search
        assert set(paths.get_enabled_paths()) == {"graph", "search"}
    
    def test_neo4j_parquet_graph_path(self):
        """Test that neo4j + parquet enables graph path (not lightweight)."""
        paths = ProcessingPaths.from_destinations(["neo4j", "parquet"])
        assert not paths.lightweight  # Not parquet-only
        assert paths.graph
        assert not paths.search
        assert paths.get_enabled_paths() == ["graph"]


class TestPipelineFork:
    """Test the PipelineFork class."""
    
    def test_parquet_only_processing(self, mock_entities):
        """Test processing with parquet-only destination."""
        fork = PipelineFork(["parquet"])
        
        result, output_data = fork.process_paths(mock_entities)
        
        # Check result
        assert result.is_successful()
        assert result.lightweight_success
        assert result.paths_processed == ["lightweight"]
        
        # Check output data
        assert "parquet" in output_data
        assert output_data["parquet"] == mock_entities
        assert "neo4j" not in output_data
        assert "elasticsearch" not in output_data
    
    def test_neo4j_processing(self, mock_entities):
        """Test processing with neo4j destination."""
        fork = PipelineFork(["neo4j"])
        
        # Mock entity extractors
        extractors = {
            "feature_extractor": Mock(),
            "property_type_extractor": Mock(),
            "price_range_extractor": Mock(),
            "county_extractor": Mock(),
            "topic_extractor": Mock(),
        }
        
        # Mock the extraction methods
        for extractor in extractors.values():
            if hasattr(extractor, 'extract'):
                extractor.extract.return_value = Mock(spec=DataFrame)
            if hasattr(extractor, 'extract_property_types'):
                extractor.extract_property_types.return_value = Mock(spec=DataFrame)
            if hasattr(extractor, 'extract_price_ranges'):
                extractor.extract_price_ranges.return_value = Mock(spec=DataFrame)
            if hasattr(extractor, 'extract_counties'):
                extractor.extract_counties.return_value = Mock(spec=DataFrame)
            if hasattr(extractor, 'extract_topic_clusters'):
                extractor.extract_topic_clusters.return_value = Mock(spec=DataFrame)
        
        result, output_data = fork.process_paths(mock_entities, entity_extractors=extractors)
        
        # Check result
        assert result.is_successful()
        assert result.graph_success
        assert result.paths_processed == ["graph"]
        
        # Check output data
        assert "neo4j" in output_data
        assert len(output_data["neo4j"]) > len(mock_entities)  # Should have extracted entities
    
    def test_elasticsearch_processing(self, spark, mock_entities):
        """Test processing with elasticsearch destination."""
        fork = PipelineFork(["elasticsearch"])
        
        # Mock search config
        search_config = Mock()
        search_config.enabled = False  # Disable to avoid actual ES connection
        
        result, output_data = fork.process_paths(
            mock_entities, 
            spark=spark, 
            search_config=search_config
        )
        
        # Check result (should succeed with disabled search config)
        assert result.search_success
        assert result.paths_processed == ["search"]
        
        # Check output data
        assert "elasticsearch" in output_data
    
    def test_multiple_destinations(self, spark, mock_entities):
        """Test processing with multiple destinations."""
        fork = PipelineFork(["neo4j", "elasticsearch", "parquet"])
        
        # Mock extractors and search config
        extractors = {
            "feature_extractor": Mock(),
            "property_type_extractor": Mock(),
            "price_range_extractor": Mock(),
            "county_extractor": Mock(), 
            "topic_extractor": Mock(),
        }
        
        search_config = Mock()
        search_config.enabled = False
        
        result, output_data = fork.process_paths(
            mock_entities,
            spark=spark,
            search_config=search_config,
            entity_extractors=extractors
        )
        
        # Check result
        assert result.paths_processed == ["graph", "search"]
        
        # Check output data (both paths should be present)
        assert "neo4j" in output_data or "parquet" in output_data  # Graph processing
        assert "elasticsearch" in output_data  # Search processing
    
    def test_validate_entities_valid(self, mock_entities):
        """Test entity validation with valid entities."""
        fork = PipelineFork(["parquet"])
        
        assert fork.validate_entities(mock_entities)
    
    def test_validate_entities_empty(self):
        """Test entity validation with empty entities."""
        fork = PipelineFork(["parquet"])
        
        assert not fork.validate_entities({})
    
    def test_validate_entities_empty_columns(self):
        """Test entity validation with empty columns."""
        fork = PipelineFork(["parquet"])
        
        empty_df = Mock(spec=DataFrame)
        empty_df.columns = []
        
        entities = {"properties": empty_df}
        
        assert not fork.validate_entities(entities)


class TestProcessingResult:
    """Test the ProcessingResult model."""
    
    def test_default_result(self):
        """Test default ProcessingResult values."""
        result = ProcessingResult()
        assert result.is_successful()
        assert result.lightweight_success
        assert result.graph_success
        assert result.search_success
        assert len(result.get_errors()) == 0
    
    def test_with_errors(self):
        """Test ProcessingResult with errors."""
        result = ProcessingResult(
            lightweight_success=False,
            graph_success=True,
            search_success=False,
            lightweight_error="Lightweight failed",
            search_error="Search failed"
        )
        
        assert not result.is_successful()
        errors = result.get_errors()
        assert len(errors) == 2
        assert "Lightweight: Lightweight failed" in errors
        assert "Search: Search failed" in errors