"""
Tests for neighborhood document builder.

Tests transformation of neighborhood DataFrames into NeighborhoodDocument models.
"""

import pytest
from unittest.mock import Mock
from data_pipeline.search_pipeline.builders.neighborhood_builder import NeighborhoodDocumentBuilder
from data_pipeline.search_pipeline.models.documents import NeighborhoodDocument


def create_mock_row(data):
    """Create a mock Spark Row object."""
    mock_row = Mock()
    mock_row.asDict.return_value = data
    return mock_row


def test_neighborhood_builder_transform():
    """Test transforming neighborhood DataFrame into documents."""
    builder = NeighborhoodDocumentBuilder()
    
    # Create mock DataFrame
    mock_df = Mock()
    mock_df.columns = ["neighborhood_id", "name", "city", "state"]
    mock_df.count.return_value = 2
    
    # Create mock rows
    row1 = create_mock_row({
        "neighborhood_id": "456",
        "name": "Mission District",
        "city": "San Francisco",
        "state": "CA",
        "walkability_score": 95,
        "transit_score": 88,
        "school_rating": 8.5,
        "description": "Vibrant neighborhood with great food",
        "latitude": 37.7599,
        "longitude": -122.4148,
    })
    
    row2 = create_mock_row({
        "neighborhood_id": "789",
        "name": "SOMA",
        "city": "San Francisco",
        "state": "CA",
        "walkability_score": 98,
    })
    
    mock_df.collect.return_value = [row1, row2]
    
    # Transform
    documents = builder.transform(mock_df)
    
    # Verify
    assert len(documents) == 2
    assert all(isinstance(doc, NeighborhoodDocument) for doc in documents)
    
    # Check first document
    doc1 = documents[0]
    assert doc1.neighborhood_id == "456"
    assert doc1.name == "Mission District"
    assert doc1.walkability_score == 95
    assert doc1.transit_score == 88
    assert doc1.school_rating == 8.5


def test_neighborhood_builder_search_text_generation():
    """Test search text generation for neighborhoods."""
    builder = NeighborhoodDocumentBuilder()
    
    # Create mock DataFrame
    mock_df = Mock()
    mock_df.columns = ["neighborhood_id", "name"]
    mock_df.count.return_value = 1
    
    row = create_mock_row({
        "neighborhood_id": "123",
        "name": "Mission District",
        "description": "Historic neighborhood known for murals",
        "city": "San Francisco",
        "state": "CA",
    })
    
    mock_df.collect.return_value = [row]
    
    # Transform
    documents = builder.transform(mock_df)
    
    # Check search text
    assert len(documents) == 1
    doc = documents[0]
    assert doc.search_text is not None
    assert "Mission District" in doc.search_text
    assert "Historic neighborhood" in doc.search_text
    assert "San Francisco" in doc.search_text
    assert "CA" in doc.search_text


def test_neighborhood_builder_score_validation():
    """Test score validation in neighborhood builder."""
    builder = NeighborhoodDocumentBuilder()
    
    mock_df = Mock()
    mock_df.columns = ["neighborhood_id", "name"]
    mock_df.count.return_value = 1
    
    # Test with out-of-range score (should be ignored)
    row = create_mock_row({
        "neighborhood_id": "123",
        "name": "Test",
        "walkability_score": 150,  # Out of range
        "transit_score": -10,  # Out of range
    })
    
    mock_df.collect.return_value = [row]
    
    documents = builder.transform(mock_df)
    
    assert len(documents) == 1
    doc = documents[0]
    assert doc.walkability_score is None  # Invalid score ignored
    assert doc.transit_score is None  # Invalid score ignored


def test_neighborhood_builder_boundaries_handling():
    """Test handling of boundaries field."""
    builder = NeighborhoodDocumentBuilder()
    
    mock_df = Mock()
    mock_df.columns = ["neighborhood_id", "name"]
    mock_df.count.return_value = 1
    
    # Test with dict boundaries (should be serialized to JSON)
    boundaries_dict = {"north": 37.76, "south": 37.75, "east": -122.40, "west": -122.42}
    row = create_mock_row({
        "neighborhood_id": "123",
        "name": "Test",
        "boundaries": boundaries_dict,
    })
    
    mock_df.collect.return_value = [row]
    
    documents = builder.transform(mock_df)
    
    assert len(documents) == 1
    doc = documents[0]
    assert doc.boundaries is not None
    assert isinstance(doc.boundaries, str)  # Should be JSON string
    assert "north" in doc.boundaries


def test_neighborhood_builder_validates_required_fields():
    """Test builder validates required fields."""
    builder = NeighborhoodDocumentBuilder()
    
    # Mock DataFrame missing required fields
    mock_df = Mock()
    mock_df.columns = ["city", "state"]  # Missing neighborhood_id and name
    
    with pytest.raises(ValueError, match="Missing required columns"):
        builder.transform(mock_df)


def test_neighborhood_builder_creates_proper_document_id():
    """Test document ID creation for neighborhoods."""
    builder = NeighborhoodDocumentBuilder()
    
    mock_df = Mock()
    mock_df.columns = ["neighborhood_id", "name"]
    mock_df.count.return_value = 1
    
    row = create_mock_row({
        "neighborhood_id": "nb456",
        "name": "Test Neighborhood",
    })
    
    mock_df.collect.return_value = [row]
    
    documents = builder.transform(mock_df)
    
    assert len(documents) == 1
    assert documents[0].id == "neighborhood_nb456"