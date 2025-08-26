"""
Unit tests for the pipeline fork implementation.

Tests the PipelineFork class and ForkConfiguration for correct
routing of DataFrames to processing paths.
"""

import pytest
from unittest.mock import Mock, MagicMock
from pyspark.sql import SparkSession, DataFrame

from data_pipeline.core.pipeline_fork import (
    PipelineFork,
    ForkConfiguration,
    ForkResult
)


@pytest.fixture
def spark():
    """Create a test Spark session."""
    return SparkSession.builder \
        .appName("test_pipeline_fork") \
        .master("local[1]") \
        .getOrCreate()


@pytest.fixture
def mock_dataframes():
    """Create mock DataFrames for testing."""
    properties_df = Mock(spec=DataFrame)
    properties_df.columns = ['listing_id', 'price', 'embedding_text']
    
    neighborhoods_df = Mock(spec=DataFrame)
    neighborhoods_df.columns = ['neighborhood_id', 'name', 'embedding_text']
    
    wikipedia_df = Mock(spec=DataFrame)
    wikipedia_df.columns = ['page_id', 'title', 'embedding_text']
    
    return properties_df, neighborhoods_df, wikipedia_df


class TestForkConfiguration:
    """Test the ForkConfiguration model."""
    
    def test_default_configuration(self):
        """Test default fork configuration."""
        config = ForkConfiguration()
        assert config.enabled_paths == ["graph"]
        assert config.is_graph_enabled()
        assert not config.is_search_enabled()
    
    def test_both_paths_enabled(self):
        """Test configuration with both paths enabled."""
        config = ForkConfiguration(enabled_paths=["graph", "search"])
        assert config.is_graph_enabled()
        assert config.is_search_enabled()
    
    def test_search_only(self):
        """Test configuration with only search enabled."""
        config = ForkConfiguration(enabled_paths=["search"])
        assert not config.is_graph_enabled()
        assert config.is_search_enabled()
    
    def test_invalid_path(self):
        """Test that invalid paths are rejected."""
        with pytest.raises(ValueError, match="Invalid paths"):
            ForkConfiguration(enabled_paths=["invalid"])


class TestPipelineFork:
    """Test the PipelineFork class."""
    
    def test_graph_only_routing(self, mock_dataframes):
        """Test routing with only graph path enabled."""
        config = ForkConfiguration(enabled_paths=["graph"])
        fork = PipelineFork(config)
        
        properties_df, neighborhoods_df, wikipedia_df = mock_dataframes
        
        result, routed = fork.route(properties_df, neighborhoods_df, wikipedia_df)
        
        # Check result
        assert result.graph_success
        assert not result.search_success
        assert result.graph_error is None
        assert result.search_error is None
        
        # Check routed DataFrames
        assert "graph" in routed
        assert "search" not in routed
        assert routed["graph"]["properties"] == properties_df
        assert routed["graph"]["neighborhoods"] == neighborhoods_df
        assert routed["graph"]["wikipedia"] == wikipedia_df
    
    def test_both_paths_routing(self, mock_dataframes):
        """Test routing with both paths enabled."""
        config = ForkConfiguration(enabled_paths=["graph", "search"])
        fork = PipelineFork(config)
        
        properties_df, neighborhoods_df, wikipedia_df = mock_dataframes
        
        result, routed = fork.route(properties_df, neighborhoods_df, wikipedia_df)
        
        # Check result
        assert result.graph_success
        assert result.search_success
        assert result.graph_error is None
        assert result.search_error is None
        
        # Check routed DataFrames
        assert "graph" in routed
        assert "search" in routed
        
        # Both paths should get the same DataFrames
        assert routed["graph"]["properties"] == properties_df
        assert routed["search"]["properties"] == properties_df
    
    def test_search_only_routing(self, mock_dataframes):
        """Test routing with only search path enabled."""
        config = ForkConfiguration(enabled_paths=["search"])
        fork = PipelineFork(config)
        
        properties_df, neighborhoods_df, wikipedia_df = mock_dataframes
        
        result, routed = fork.route(properties_df, neighborhoods_df, wikipedia_df)
        
        # Check result
        assert not result.graph_success
        assert result.search_success
        assert result.graph_error is None
        assert result.search_error is None
        
        # Check routed DataFrames
        assert "graph" not in routed
        assert "search" in routed
        assert routed["search"]["properties"] == properties_df
    
    def test_validate_dataframes_valid(self, mock_dataframes):
        """Test DataFrame validation with valid DataFrames."""
        config = ForkConfiguration()
        fork = PipelineFork(config)
        
        properties_df, neighborhoods_df, wikipedia_df = mock_dataframes
        
        assert fork.validate_dataframes(properties_df, neighborhoods_df, wikipedia_df)
    
    def test_validate_dataframes_none(self):
        """Test DataFrame validation with None DataFrames."""
        config = ForkConfiguration()
        fork = PipelineFork(config)
        
        assert not fork.validate_dataframes(None, Mock(spec=DataFrame), Mock(spec=DataFrame))
        assert not fork.validate_dataframes(Mock(spec=DataFrame), None, Mock(spec=DataFrame))
        assert not fork.validate_dataframes(Mock(spec=DataFrame), Mock(spec=DataFrame), None)
    
    def test_validate_dataframes_empty_columns(self):
        """Test DataFrame validation with empty columns."""
        config = ForkConfiguration()
        fork = PipelineFork(config)
        
        properties_df = Mock(spec=DataFrame)
        properties_df.columns = []
        
        neighborhoods_df = Mock(spec=DataFrame)
        neighborhoods_df.columns = ['id']
        
        wikipedia_df = Mock(spec=DataFrame)
        wikipedia_df.columns = ['id']
        
        assert not fork.validate_dataframes(properties_df, neighborhoods_df, wikipedia_df)
    
    def test_routing_with_none_dataframes(self):
        """Test routing handles None DataFrames gracefully."""
        config = ForkConfiguration(enabled_paths=["graph"])
        fork = PipelineFork(config)
        
        result, routed = fork.route(None, None, None)
        
        # Should still succeed but with None values
        assert result.graph_success
        assert "graph" in routed
        assert routed["graph"]["properties"] is None
        assert routed["graph"]["neighborhoods"] is None
        assert routed["graph"]["wikipedia"] is None
    
    def test_error_handling(self, mock_dataframes):
        """Test error handling in routing."""
        config = ForkConfiguration(enabled_paths=["graph"])
        fork = PipelineFork(config)
        
        # Make properties_df raise an exception when accessed
        properties_df = Mock(spec=DataFrame)
        properties_df.columns = Mock(side_effect=Exception("Test error"))
        
        neighborhoods_df, wikipedia_df = mock_dataframes[1:]
        
        # The route method should handle exceptions gracefully
        result, routed = fork.route(properties_df, neighborhoods_df, wikipedia_df)
        
        # Should still route successfully (error handling is in validation, not routing)
        assert result.graph_success
        assert "graph" in routed


class TestForkResult:
    """Test the ForkResult model."""
    
    def test_default_result(self):
        """Test default ForkResult values."""
        result = ForkResult()
        assert not result.graph_success
        assert not result.search_success
        assert result.graph_error is None
        assert result.search_error is None
    
    def test_with_errors(self):
        """Test ForkResult with errors."""
        result = ForkResult(
            graph_success=False,
            search_success=True,
            graph_error="Graph processing failed",
            search_error=None
        )
        assert not result.graph_success
        assert result.search_success
        assert result.graph_error == "Graph processing failed"
        assert result.search_error is None