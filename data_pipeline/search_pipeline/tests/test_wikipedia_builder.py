"""
Tests for Wikipedia document builder.

Tests transformation of Wikipedia DataFrames into WikipediaDocument models.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime
from data_pipeline.search_pipeline.builders.wikipedia_builder import WikipediaDocumentBuilder
from data_pipeline.search_pipeline.models.documents import WikipediaDocument


def create_mock_row(data):
    """Create a mock Spark Row object."""
    mock_row = Mock()
    mock_row.asDict.return_value = data
    return mock_row


def test_wikipedia_builder_transform():
    """Test transforming Wikipedia DataFrame into documents."""
    builder = WikipediaDocumentBuilder()
    
    # Create mock DataFrame
    mock_df = Mock()
    mock_df.columns = ["page_id", "title", "url", "summary"]
    mock_df.count.return_value = 2
    
    # Create mock rows
    row1 = create_mock_row({
        "page_id": 12345,
        "title": "San Francisco",
        "url": "https://en.wikipedia.org/wiki/San_Francisco",
        "summary": "San Francisco is a city in California",
        "content": "San Francisco, officially the City and County of San Francisco...",
        "city": "San Francisco",
        "state": "CA",
        "topics": ["Cities", "California", "Bay Area"],
    })
    
    row2 = create_mock_row({
        "page_id": 67890,
        "title": "Golden Gate Park",
        "summary": "Large urban park in San Francisco",
        "best_city": "San Francisco",
        "best_state": "CA",
    })
    
    mock_df.collect.return_value = [row1, row2]
    
    # Transform
    documents = builder.transform(mock_df)
    
    # Verify
    assert len(documents) == 2
    assert all(isinstance(doc, WikipediaDocument) for doc in documents)
    
    # Check first document
    doc1 = documents[0]
    assert doc1.page_id == 12345
    assert doc1.title == "San Francisco"
    assert doc1.url == "https://en.wikipedia.org/wiki/San_Francisco"
    assert doc1.city == "San Francisco"
    assert doc1.state == "CA"
    assert len(doc1.topics) == 3
    assert "Cities" in doc1.topics


def test_wikipedia_builder_search_text_generation():
    """Test search text generation for Wikipedia articles."""
    builder = WikipediaDocumentBuilder()
    
    # Create mock DataFrame
    mock_df = Mock()
    mock_df.columns = ["page_id", "title"]
    mock_df.count.return_value = 1
    
    row = create_mock_row({
        "page_id": 123,
        "title": "Mission District",
        "summary": "The Mission District is a neighborhood in San Francisco",
        "content": "The Mission District, commonly called the Mission...",
        "topics": ["Neighborhoods", "San Francisco"],
        "city": "San Francisco",
        "state": "California",
    })
    
    mock_df.collect.return_value = [row]
    
    # Transform
    documents = builder.transform(mock_df)
    
    # Check search text
    assert len(documents) == 1
    doc = documents[0]
    assert doc.search_text is not None
    assert "Mission District" in doc.search_text
    assert "neighborhood" in doc.search_text
    assert "San Francisco" in doc.search_text
    assert "Neighborhoods" in doc.search_text


def test_wikipedia_builder_handles_alternate_field_names():
    """Test builder handles alternate field names for city/state."""
    builder = WikipediaDocumentBuilder()
    
    mock_df = Mock()
    mock_df.columns = ["page_id", "title"]
    mock_df.count.return_value = 1
    
    # Use alternate field names (best_city, best_state)
    row = create_mock_row({
        "page_id": 123,
        "title": "Test Article",
        "best_city": "Oakland",
        "best_state": "CA",
        # Regular city/state fields not present
    })
    
    mock_df.collect.return_value = [row]
    
    documents = builder.transform(mock_df)
    
    assert len(documents) == 1
    doc = documents[0]
    assert doc.city == "Oakland"
    assert doc.state == "CA"


def test_wikipedia_builder_extracts_topics_from_various_fields():
    """Test topic extraction from different field names."""
    builder = WikipediaDocumentBuilder()
    
    mock_df = Mock()
    mock_df.columns = ["page_id", "title"]
    mock_df.count.return_value = 3
    
    # Different ways to specify topics
    row1 = create_mock_row({
        "page_id": 1,
        "title": "Article 1",
        "topics": ["Topic1", "Topic2"],
    })
    
    row2 = create_mock_row({
        "page_id": 2,
        "title": "Article 2",
        "categories": "Category1, Category2",
    })
    
    row3 = create_mock_row({
        "page_id": 3,
        "title": "Article 3",
        "key_topics": "KeyTopic1",
    })
    
    mock_df.collect.return_value = [row1, row2, row3]
    
    documents = builder.transform(mock_df)
    
    assert len(documents) == 3
    assert documents[0].topics == ["Topic1", "Topic2"]
    assert documents[1].topics == ["Category1", "Category2"]
    assert documents[2].topics == ["KeyTopic1"]


def test_wikipedia_builder_validates_page_id():
    """Test page_id validation."""
    builder = WikipediaDocumentBuilder()
    
    mock_df = Mock()
    mock_df.columns = ["page_id", "title"]
    mock_df.count.return_value = 1
    
    # Invalid page_id (not convertible to int)
    row = create_mock_row({
        "page_id": "not_a_number",
        "title": "Test",
    })
    
    mock_df.collect.return_value = [row]
    
    # Should skip invalid row
    documents = builder.transform(mock_df)
    assert len(documents) == 0  # Row skipped due to error


def test_wikipedia_builder_validates_required_fields():
    """Test builder validates required fields."""
    builder = WikipediaDocumentBuilder()
    
    # Mock DataFrame missing required fields
    mock_df = Mock()
    mock_df.columns = ["summary", "content"]  # Missing page_id and title
    
    with pytest.raises(ValueError, match="Missing required columns"):
        builder.transform(mock_df)


def test_wikipedia_builder_creates_proper_document_id():
    """Test document ID creation for Wikipedia articles."""
    builder = WikipediaDocumentBuilder()
    
    mock_df = Mock()
    mock_df.columns = ["page_id", "title"]
    mock_df.count.return_value = 1
    
    row = create_mock_row({
        "page_id": 98765,
        "title": "Test Article",
    })
    
    mock_df.collect.return_value = [row]
    
    documents = builder.transform(mock_df)
    
    assert len(documents) == 1
    assert documents[0].id == "wikipedia_98765"


def test_wikipedia_builder_limits_content_length():
    """Test that content field is limited in search text."""
    builder = WikipediaDocumentBuilder()
    
    mock_df = Mock()
    mock_df.columns = ["page_id", "title"]
    mock_df.count.return_value = 1
    
    # Create very long content
    long_content = "A" * 10000  # 10,000 characters
    
    row = create_mock_row({
        "page_id": 123,
        "title": "Test",
        "content": long_content,
    })
    
    mock_df.collect.return_value = [row]
    
    documents = builder.transform(mock_df)
    
    assert len(documents) == 1
    doc = documents[0]
    # Search text should contain truncated content
    assert doc.search_text is not None
    assert len(doc.search_text) < 10000  # Much shorter than original
    assert "..." in doc.search_text  # Should have truncation indicator