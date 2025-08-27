"""
Tests for document models.

Validates that document models work correctly with proper type safety
and validation.
"""

import pytest
from datetime import datetime
from data_pipeline.search_pipeline.models.documents import (
    PropertyDocument,
    NeighborhoodDocument,
    WikipediaDocument,
)


def test_property_document_creation():
    """Test creating a property document with valid data."""
    doc = PropertyDocument(
        id="prop-123",
        entity_type="property",
        listing_id="123",
        price=500000.0,
        bedrooms=3,
        bathrooms=2.5,
        square_feet=2000,
        city="San Francisco",
        state="CA",
        neighborhood_id="nb-456",
        neighborhood_name="Mission District",
        description="Beautiful home",
        features=["garage", "garden"],
    )
    
    assert doc.id == "prop-123"
    assert doc.entity_type == "property"
    assert doc.price == 500000.0
    assert doc.bedrooms == 3
    assert len(doc.features) == 2


def test_property_document_validation():
    """Test property document validation catches invalid data."""
    with pytest.raises(ValueError, match="Price must be non-negative"):
        PropertyDocument(
            id="prop-123",
            entity_type="property",
            listing_id="123",
            price=-1000.0,
        )
    
    with pytest.raises(ValueError, match="Value must be non-negative"):
        PropertyDocument(
            id="prop-123",
            entity_type="property",
            listing_id="123",
            bedrooms=-1,
        )


def test_neighborhood_document_creation():
    """Test creating a neighborhood document."""
    doc = NeighborhoodDocument(
        id="nb-456",
        entity_type="neighborhood",
        neighborhood_id="456",
        name="Mission District",
        city="San Francisco",
        state="CA",
        walkability_score=95,
        transit_score=88,
        description="Vibrant neighborhood",
    )
    
    assert doc.neighborhood_id == "456"
    assert doc.name == "Mission District"
    assert doc.walkability_score == 95
    assert doc.transit_score == 88


def test_neighborhood_score_validation():
    """Test neighborhood score validation."""
    with pytest.raises(ValueError, match="Score must be between 0 and 100"):
        NeighborhoodDocument(
            id="nb-456",
            entity_type="neighborhood",
            neighborhood_id="456",
            name="Test",
            walkability_score=101,
        )


def test_wikipedia_document_creation():
    """Test creating a Wikipedia document."""
    doc = WikipediaDocument(
        id="wiki-789",
        entity_type="wikipedia",
        page_id=789,
        title="San Francisco",
        url="https://en.wikipedia.org/wiki/San_Francisco",
        summary="San Francisco is a city in California",
        city="San Francisco",
        state="CA",
        topics=["Cities", "California"],
    )
    
    assert doc.page_id == 789
    assert doc.title == "San Francisco"
    assert len(doc.topics) == 2
    assert doc.city == "San Francisco"


def test_search_text_field():
    """Test that search_text field can be set."""
    doc = PropertyDocument(
        id="prop-123",
        entity_type="property",
        listing_id="123",
        search_text="Beautiful 3 bedroom home in Mission District San Francisco",
    )
    
    assert doc.search_text == "Beautiful 3 bedroom home in Mission District San Francisco"


def test_indexed_at_default():
    """Test that indexed_at gets set automatically."""
    doc = PropertyDocument(
        id="prop-123",
        entity_type="property",
        listing_id="123",
    )
    
    assert doc.indexed_at is not None
    assert isinstance(doc.indexed_at, datetime)