"""
Tests for base document builder.

Tests the common utilities and validation methods.
"""

import pytest
from unittest.mock import Mock
from data_pipeline.search_pipeline.builders.base import BaseDocumentBuilder


class MockBuilder(BaseDocumentBuilder):
    """Mock implementation of BaseDocumentBuilder for testing."""
    
    def transform(self, df):
        """Simple transform implementation for testing."""
        return []


def test_validate_dataframe_with_valid_df():
    """Test DataFrame validation with valid DataFrame."""
    builder = MockBuilder()
    
    # Mock DataFrame with required columns
    mock_df = Mock()
    mock_df.columns = ["id", "name", "price"]
    mock_df.count.return_value = 10
    
    # Should not raise any exception
    builder.validate_dataframe(mock_df, ["id", "name"])


def test_validate_dataframe_with_missing_columns():
    """Test DataFrame validation with missing columns."""
    builder = MockBuilder()
    
    # Mock DataFrame missing required columns
    mock_df = Mock()
    mock_df.columns = ["id", "name"]
    
    with pytest.raises(ValueError, match="Missing required columns: \\['price'\\]"):
        builder.validate_dataframe(mock_df, ["id", "name", "price"])


def test_validate_dataframe_with_none():
    """Test DataFrame validation with None DataFrame."""
    builder = MockBuilder()
    
    with pytest.raises(ValueError, match="DataFrame is None"):
        builder.validate_dataframe(None, ["id"])


def test_extract_field():
    """Test field extraction from row."""
    builder = MockBuilder()
    
    row = {"id": "123", "name": "Test", "price": 100.0}
    
    assert builder.extract_field(row, "id") == "123"
    assert builder.extract_field(row, "name") == "Test"
    assert builder.extract_field(row, "missing") is None
    assert builder.extract_field(row, "missing", "default") == "default"


def test_combine_text_fields():
    """Test combining text fields."""
    builder = MockBuilder()
    
    # Normal combination
    result = builder.combine_text_fields("Hello", "World")
    assert result == "Hello World"
    
    # With None values
    result = builder.combine_text_fields("Hello", None, "World")
    assert result == "Hello World"
    
    # All None
    result = builder.combine_text_fields(None, None)
    assert result is None
    
    # Empty strings
    result = builder.combine_text_fields("", "  ", "Hello")
    assert result == "Hello"
    
    # Custom separator
    result = builder.combine_text_fields("A", "B", "C", separator=", ")
    assert result == "A, B, C"


def test_clean_text():
    """Test text cleaning."""
    builder = MockBuilder()
    
    assert builder.clean_text("  Hello  World  ") == "Hello World"
    assert builder.clean_text("Multiple   spaces") == "Multiple spaces"
    assert builder.clean_text(None) is None
    assert builder.clean_text("") is None
    assert builder.clean_text("   ") is None
    assert builder.clean_text(123) == "123"


def test_parse_list_field():
    """Test parsing list fields."""
    builder = MockBuilder()
    
    # Already a list
    assert builder.parse_list_field(["a", "b", "c"]) == ["a", "b", "c"]
    
    # Comma-separated string
    assert builder.parse_list_field("a, b, c") == ["a", "b", "c"]
    
    # Single string
    assert builder.parse_list_field("single") == ["single"]
    
    # None
    assert builder.parse_list_field(None) == []
    
    # Empty string
    assert builder.parse_list_field("") == []
    
    # Number
    assert builder.parse_list_field(123) == ["123"]
    
    # List with None values
    assert builder.parse_list_field([1, None, 3]) == ["1", "3"]


def test_create_id():
    """Test document ID creation."""
    builder = MockBuilder()
    
    assert builder.create_id("property", "123") == "property_123"
    assert builder.create_id("neighborhood", "abc") == "neighborhood_abc"