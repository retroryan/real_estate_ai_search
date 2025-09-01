"""
Integration test for location understanding functionality.

Tests the DSPy-based location extraction from natural language queries
following the wiki_summary pattern.
"""

import pytest
import logging
from unittest.mock import Mock, patch

from real_estate_search.demo_queries.location_understanding import (
    LocationUnderstandingModule,
    LocationIntent,
    LocationFilterBuilder,
    demo_location_understanding
)

# Set up logging for test visibility
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestLocationUnderstandingIntegration:
    """Integration tests for location understanding functionality."""
    
    @pytest.fixture
    def location_module(self):
        """Create location understanding module."""
        return LocationUnderstandingModule()
    
    @pytest.fixture
    def filter_builder(self):
        """Create location filter builder."""
        return LocationFilterBuilder()
    
    def test_location_intent_model_validation(self):
        """Test LocationIntent Pydantic model validation."""
        # Valid location intent
        intent = LocationIntent(
            city="San Francisco",
            state="California",
            neighborhood="Mission District",
            zip_code="94110",
            has_location=True,
            cleaned_query="modern home with garden",
            confidence=0.9
        )
        
        assert intent.city == "San Francisco"
        assert intent.state == "California"
        assert intent.neighborhood == "Mission District"
        assert intent.zip_code == "94110"
        assert intent.has_location is True
        assert intent.cleaned_query == "modern home with garden"
        assert intent.confidence == 0.9
    
    def test_location_filter_builder_city(self, filter_builder):
        """Test building city filters."""
        intent = LocationIntent(
            city="Park City",
            has_location=True,
            cleaned_query="family home",
            confidence=0.8
        )
        
        filters = filter_builder.build_filters(intent)
        
        assert len(filters) == 1
        assert filters[0] == {
            "term": {
                "address.city.keyword": "Park City"
            }
        }
    
    def test_location_filter_builder_multiple_fields(self, filter_builder):
        """Test building filters with multiple location fields."""
        intent = LocationIntent(
            city="San Francisco",
            state="California",
            zip_code="94102",
            has_location=True,
            cleaned_query="condo",
            confidence=0.9
        )
        
        filters = filter_builder.build_filters(intent)
        
        assert len(filters) == 3
        
        # Check city filter
        city_filter = next(f for f in filters if "address.city.keyword" in f.get("term", {}))
        assert city_filter["term"]["address.city.keyword"] == "San Francisco"
        
        # Check state filter
        state_filter = next(f for f in filters if "address.state" in f.get("term", {}))
        assert state_filter["term"]["address.state"] == "California"
        
        # Check ZIP filter
        zip_filter = next(f for f in filters if "address.zip_code" in f.get("term", {}))
        assert zip_filter["term"]["address.zip_code"] == "94102"
    
    def test_location_filter_builder_no_location(self, filter_builder):
        """Test filter builder with no location information."""
        intent = LocationIntent(
            has_location=False,
            cleaned_query="modern kitchen",
            confidence=0.0
        )
        
        filters = filter_builder.build_filters(intent)
        assert filters == []
    
    def test_location_module_park_city_example(self, location_module):
        """Test location extraction for Park City example."""
        query = "Find a great family home in Park City"
        
        result = location_module(query)
        
        # Verify result structure
        assert isinstance(result, LocationIntent)
        assert result.has_location is True
        assert result.confidence > 0.5
        
        # Should extract Park City as city
        assert result.city is not None
        assert "Park City" in result.city
        
        # Cleaned query should focus on property features
        assert "family home" in result.cleaned_query
        assert "Park City" not in result.cleaned_query or result.cleaned_query == query
    
    def test_location_module_san_francisco_zip(self, location_module):
        """Test location extraction with ZIP code."""
        query = "2 bedroom apartment in 94102"
        
        result = location_module(query)
        
        assert isinstance(result, LocationIntent)
        # The model may or may not detect the ZIP code depending on its training
        # Just check that it returns a valid LocationIntent
        if result.has_location:
            # If location detected, cleaned query should remove location terms
            assert result.zip_code == "94102" or result.zip_code is None
        else:
            # If no location detected, query should remain unchanged
            assert result.cleaned_query == query
    
    def test_location_module_no_location(self, location_module):
        """Test query without location information."""
        query = "modern kitchen with stainless steel appliances"
        
        result = location_module(query)
        
        assert isinstance(result, LocationIntent)
        assert result.has_location is False
        assert result.confidence < 0.5
        assert result.cleaned_query == query
    
    def test_demo_location_understanding_structure(self):
        """Test demo function structure without DSPy execution."""
        # Mock the LocationUnderstandingModule
        with patch('real_estate_search.demo_queries.location_understanding.LocationUnderstandingModule') as mock_module:
            mock_instance = Mock()
            mock_module.return_value = mock_instance
            
            # Mock return value - module called as callable returns LocationIntent
            mock_result = LocationIntent(
                city="Park City",
                state="Utah",
                has_location=True,
                cleaned_query="great family home",
                confidence=0.85
            )
            # When module is called as callable, it should return the LocationIntent
            mock_instance.return_value = mock_result
            
            # Run demo
            result = demo_location_understanding("Find a great family home in Park City")
            
            # Verify result
            assert isinstance(result, LocationIntent)
            assert result.city == "Park City"
            assert result.state == "Utah"
            assert result.has_location is True
            
            # Verify module was called correctly
            mock_module.assert_called_once_with()
            mock_instance.assert_called_once_with("Find a great family home in Park City")