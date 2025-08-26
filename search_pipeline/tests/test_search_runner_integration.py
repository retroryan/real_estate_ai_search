"""
Integration tests for SearchPipelineRunner with document builders.

Tests the complete flow from DataFrames to Elasticsearch documents.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from pyspark.sql import SparkSession

from search_pipeline.core.search_runner import SearchPipelineRunner
from search_pipeline.models.config import SearchPipelineConfig, ElasticsearchConfig, BulkWriteConfig
from search_pipeline.models.documents import PropertyDocument, NeighborhoodDocument, WikipediaDocument


@pytest.fixture
def spark_session():
    """Create a mock Spark session."""
    spark = Mock(spec=SparkSession)
    spark.version = "3.4.0"
    spark.createDataFrame = MagicMock()
    return spark


@pytest.fixture
def search_config():
    """Create search pipeline configuration."""
    es_config = ElasticsearchConfig(
        nodes=["localhost:9200"],
        index_prefix="test",
        username="test_user",
        password="test_pass",
        bulk=BulkWriteConfig(
            batch_size_entries=1000,
            batch_size_mb=5
        )
    )
    
    config = SearchPipelineConfig(
        enabled=True,
        elasticsearch=es_config,
        validate_connection=False
    )
    return config


def create_mock_property_df():
    """Create a mock property DataFrame."""
    mock_df = Mock()
    mock_df.columns = ["listing_id", "price", "bedrooms", "city", "state"]
    mock_df.count.return_value = 2
    
    # Create mock rows
    row1 = Mock()
    row1.asDict.return_value = {
        "listing_id": "prop-1",
        "price": 500000.0,
        "bedrooms": 3,
        "bathrooms": 2,
        "city": "San Francisco",
        "state": "CA",
        "neighborhood_id": "nb-1",
        "neighborhood_name": "Mission",
        "description": "Beautiful home"
    }
    
    row2 = Mock()
    row2.asDict.return_value = {
        "listing_id": "prop-2",
        "price": 750000.0,
        "bedrooms": 4,
        "city": "San Francisco",
        "state": "CA"
    }
    
    mock_df.collect.return_value = [row1, row2]
    return mock_df


def create_mock_neighborhood_df():
    """Create a mock neighborhood DataFrame."""
    mock_df = Mock()
    mock_df.columns = ["neighborhood_id", "name", "city", "state"]
    mock_df.count.return_value = 1
    
    row = Mock()
    row.asDict.return_value = {
        "neighborhood_id": "nb-1",
        "name": "Mission District",
        "city": "San Francisco",
        "state": "CA",
        "walkability_score": 95
    }
    
    mock_df.collect.return_value = [row]
    return mock_df


def create_mock_wikipedia_df():
    """Create a mock Wikipedia DataFrame."""
    mock_df = Mock()
    mock_df.columns = ["page_id", "title"]
    mock_df.count.return_value = 1
    
    row = Mock()
    row.asDict.return_value = {
        "page_id": 12345,
        "title": "San Francisco",
        "summary": "City in California",
        "city": "San Francisco",
        "state": "CA"
    }
    
    mock_df.collect.return_value = [row]
    return mock_df


def test_search_runner_initialization(spark_session, search_config):
    """Test SearchPipelineRunner initialization with builders."""
    runner = SearchPipelineRunner(spark_session, search_config)
    
    # Check builders are initialized
    assert "properties" in runner.builders
    assert "neighborhoods" in runner.builders
    assert "wikipedia" in runner.builders
    
    # Check builder types
    from search_pipeline.builders import PropertyDocumentBuilder, NeighborhoodDocumentBuilder, WikipediaDocumentBuilder
    assert isinstance(runner.builders["properties"], PropertyDocumentBuilder)
    assert isinstance(runner.builders["neighborhoods"], NeighborhoodDocumentBuilder)
    assert isinstance(runner.builders["wikipedia"], WikipediaDocumentBuilder)


def test_process_with_builders(spark_session, search_config):
    """Test processing DataFrames through builders."""
    runner = SearchPipelineRunner(spark_session, search_config)
    
    # Create mock DataFrames
    dataframes = {
        "properties": create_mock_property_df(),
        "neighborhoods": create_mock_neighborhood_df(),
        "wikipedia": create_mock_wikipedia_df()
    }
    
    # Mock the write method
    with patch.object(runner, '_write_documents_to_elasticsearch') as mock_write:
        result = runner.process(dataframes)
        
        # Verify processing succeeded
        assert result.success
        assert len(result.entity_results) == 3
        
        # Verify write was called for each entity type
        assert mock_write.call_count == 3
        
        # Check that documents were created (not DataFrames)
        for call in mock_write.call_args_list:
            documents = call[0][0]  # First argument is documents list
            assert isinstance(documents, list)
            assert len(documents) > 0
            # Verify documents are Pydantic models
            assert isinstance(documents[0], (PropertyDocument, NeighborhoodDocument, WikipediaDocument))


def test_process_entity_properties(spark_session, search_config):
    """Test processing property entities specifically."""
    runner = SearchPipelineRunner(spark_session, search_config)
    
    mock_df = create_mock_property_df()
    
    with patch.object(runner, '_write_documents_to_elasticsearch') as mock_write:
        result = runner._process_entity("properties", mock_df)
        
        # Check result
        assert result.entity_type == "properties"
        assert result.documents_indexed == 2
        assert result.documents_failed == 0
        assert len(result.error_messages) == 0
        
        # Verify documents were created correctly
        mock_write.assert_called_once()
        documents = mock_write.call_args[0][0]
        assert len(documents) == 2
        assert all(isinstance(doc, PropertyDocument) for doc in documents)
        
        # Check document content
        doc1 = documents[0]
        assert doc1.listing_id == "prop-1"
        assert doc1.price == 500000.0
        assert doc1.neighborhood_name == "Mission"


def test_process_entity_neighborhoods(spark_session, search_config):
    """Test processing neighborhood entities."""
    runner = SearchPipelineRunner(spark_session, search_config)
    
    mock_df = create_mock_neighborhood_df()
    
    with patch.object(runner, '_write_documents_to_elasticsearch') as mock_write:
        result = runner._process_entity("neighborhoods", mock_df)
        
        # Check result
        assert result.entity_type == "neighborhoods"
        assert result.documents_indexed == 1
        assert result.documents_failed == 0
        
        # Verify documents
        mock_write.assert_called_once()
        documents = mock_write.call_args[0][0]
        assert len(documents) == 1
        assert isinstance(documents[0], NeighborhoodDocument)
        assert documents[0].name == "Mission District"
        assert documents[0].walkability_score == 95


def test_process_entity_wikipedia(spark_session, search_config):
    """Test processing Wikipedia entities."""
    runner = SearchPipelineRunner(spark_session, search_config)
    
    mock_df = create_mock_wikipedia_df()
    
    with patch.object(runner, '_write_documents_to_elasticsearch') as mock_write:
        result = runner._process_entity("wikipedia", mock_df)
        
        # Check result
        assert result.entity_type == "wikipedia"
        assert result.documents_indexed == 1
        
        # Verify documents
        mock_write.assert_called_once()
        documents = mock_write.call_args[0][0]
        assert len(documents) == 1
        assert isinstance(documents[0], WikipediaDocument)
        assert documents[0].page_id == 12345
        assert documents[0].title == "San Francisco"


def test_write_documents_to_elasticsearch(spark_session, search_config):
    """Test writing documents to Elasticsearch."""
    runner = SearchPipelineRunner(spark_session, search_config)
    
    # Create sample documents
    documents = [
        PropertyDocument(
            id="property_123",
            entity_type="property",
            listing_id="123",
            price=500000.0,
            city="San Francisco"
        ),
        PropertyDocument(
            id="property_456",
            entity_type="property",
            listing_id="456",
            price=600000.0,
            city="Oakland"
        )
    ]
    
    # Mock DataFrame creation and write with proper chaining
    mock_df = Mock()
    mock_write_chain = Mock()
    mock_write_chain.format.return_value = mock_write_chain
    mock_write_chain.options.return_value = mock_write_chain
    mock_write_chain.mode.return_value = mock_write_chain
    mock_df.write = mock_write_chain
    spark_session.createDataFrame.return_value = mock_df
    
    # Call write method
    runner._write_documents_to_elasticsearch(documents, "test_index")
    
    # Verify DataFrame was created from documents
    spark_session.createDataFrame.assert_called_once()
    call_args = spark_session.createDataFrame.call_args[0][0]
    assert len(call_args) == 2
    assert call_args[0]["listing_id"] == "123"
    assert call_args[1]["listing_id"] == "456"
    
    # Verify write was configured correctly
    assert mock_write_chain.format.called
    assert mock_write_chain.options.called
    assert mock_write_chain.mode.called
    assert mock_write_chain.save.called


def test_process_handles_empty_dataframes(spark_session, search_config):
    """Test handling of empty DataFrames."""
    runner = SearchPipelineRunner(spark_session, search_config)
    
    # Create empty DataFrame
    mock_df = Mock()
    mock_df.columns = ["listing_id"]
    mock_df.count.return_value = 0
    mock_df.collect.return_value = []
    
    with patch.object(runner, '_write_documents_to_elasticsearch') as mock_write:
        result = runner._process_entity("properties", mock_df)
        
        # Should handle gracefully
        assert result.documents_indexed == 0
        assert result.documents_failed == 0
        
        # Write should not be called for empty documents
        mock_write.assert_not_called()


def test_process_handles_builder_errors(spark_session, search_config):
    """Test handling of builder transformation errors."""
    runner = SearchPipelineRunner(spark_session, search_config)
    
    # Create DataFrame that will cause error
    mock_df = Mock()
    mock_df.columns = ["listing_id"]
    mock_df.count.return_value = 1
    mock_df.collect.side_effect = Exception("Transformation error")
    
    result = runner._process_entity("properties", mock_df)
    
    # Should capture error
    assert result.documents_indexed == 0
    assert result.documents_failed == 1
    assert len(result.error_messages) == 1
    assert "Transformation error" in result.error_messages[0]


def test_disabled_pipeline(spark_session):
    """Test that disabled pipeline doesn't process."""
    config = SearchPipelineConfig(
        enabled=False,
        elasticsearch=ElasticsearchConfig(
            nodes=["localhost:9200"],
            index_prefix="test"
        )
    )
    
    runner = SearchPipelineRunner(spark_session, config)
    
    dataframes = {
        "properties": create_mock_property_df()
    }
    
    result = runner.process(dataframes)
    
    # Should return success without processing
    assert result.success
    assert len(result.entity_results) == 0