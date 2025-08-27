"""
Tests for property document builder.

Tests transformation of property DataFrames into PropertyDocument models.
"""

import pytest
from unittest.mock import Mock, MagicMock
from search_pipeline.builders.property_builder import PropertyDocumentBuilder
from search_pipeline.models.documents import PropertyDocument


def create_mock_row(data):
    """Create a mock Spark Row object."""
    mock_row = Mock()
    mock_row.asDict.return_value = data
    return mock_row


def test_property_builder_transform():
    """Test transforming property DataFrame into documents."""
    builder = PropertyDocumentBuilder()
    
    # Create mock DataFrame
    mock_df = Mock()
    mock_df.columns = ["listing_id", "price", "bedrooms", "city"]
    mock_df.count.return_value = 2
    
    # Create mock rows
    row1 = create_mock_row({
        "listing_id": "123",
        "price": 500000.0,
        "bedrooms": 3,
        "bathrooms": 2.5,
        "square_feet": 2000,
        "city": "San Francisco",
        "state": "CA",
        "neighborhood_id": "nb-456",
        "neighborhood_name": "Mission District",
        "description": "Beautiful home",
        "features": ["garage", "garden"],
    })
    
    row2 = create_mock_row({
        "listing_id": "456",
        "price": 750000.0,
        "bedrooms": 4,
        "city": "San Francisco",
        "state": "CA",
    })
    
    mock_df.collect.return_value = [row1, row2]
    
    # Transform
    documents = builder.transform(mock_df)
    
    # Verify
    assert len(documents) == 2
    assert all(isinstance(doc, PropertyDocument) for doc in documents)
    
    # Check first document
    doc1 = documents[0]
    assert doc1.listing_id == "123"
    assert doc1.price == 500000.0
    assert doc1.bedrooms == 3
    assert doc1.neighborhood_name == "Mission District"
    assert len(doc1.features) == 2


def test_property_builder_search_text_generation():
    """Test search text generation for properties."""
    builder = PropertyDocumentBuilder()
    
    # Create mock DataFrame with single row
    mock_df = Mock()
    mock_df.columns = ["listing_id"]
    mock_df.count.return_value = 1
    
    row = create_mock_row({
        "listing_id": "123",
        "property_type": "House",
        "description": "Beautiful 3 bedroom home",
        "features": ["garage", "garden", "pool"],
        "neighborhood_name": "Mission District",
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
    assert "House" in doc.search_text
    assert "Beautiful 3 bedroom home" in doc.search_text
    assert "garage" in doc.search_text
    assert "Mission District" in doc.search_text
    assert "San Francisco" in doc.search_text


def test_property_builder_handles_missing_fields():
    """Test builder handles missing optional fields gracefully."""
    builder = PropertyDocumentBuilder()
    
    # Create mock DataFrame with minimal data
    mock_df = Mock()
    mock_df.columns = ["listing_id"]
    mock_df.count.return_value = 1
    
    row = create_mock_row({
        "listing_id": "123",
        # All other fields missing
    })
    
    mock_df.collect.return_value = [row]
    
    # Transform should succeed
    documents = builder.transform(mock_df)
    
    assert len(documents) == 1
    doc = documents[0]
    assert doc.listing_id == "123"
    assert doc.price is None
    assert doc.bedrooms is None
    assert doc.features == []


def test_property_builder_validates_required_fields():
    """Test builder validates required fields."""
    builder = PropertyDocumentBuilder()
    
    # Mock DataFrame missing required field
    mock_df = Mock()
    mock_df.columns = ["price", "bedrooms"]  # Missing listing_id
    
    with pytest.raises(ValueError, match="Missing required columns"):
        builder.transform(mock_df)


def test_property_builder_creates_proper_document_id():
    """Test document ID creation for properties."""
    builder = PropertyDocumentBuilder()
    
    mock_df = Mock()
    mock_df.columns = ["listing_id"]
    mock_df.count.return_value = 1
    
    row = create_mock_row({
        "listing_id": "abc123",
    })
    
    mock_df.collect.return_value = [row]
    
    documents = builder.transform(mock_df)
    
    assert len(documents) == 1
    assert documents[0].id == "property_abc123"