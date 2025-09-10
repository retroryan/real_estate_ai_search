"""
Integration test for location understanding functionality.

Tests the DSPy-based location extraction from natural language queries
following the wiki_summary pattern.
"""

import pytest
import logging
from unittest.mock import Mock, patch

from real_estate_search.hybrid import (
    LocationUnderstandingModule,
    LocationIntent
)
from real_estate_search.hybrid.location import LocationFilterBuilder
from real_estate_search.demo_queries.location_understanding import demo_location_understanding

# Set up logging for test visibility
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestLocationUnderstandingIntegration:
    """Integration tests for location understanding functionality."""
    
    
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
            "match": {
                "address.city": "Park City"
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
        city_filter = next(f for f in filters if "address.city" in f.get("match", {}))
        assert city_filter["match"]["address.city"] == "San Francisco"
        
        # Check state filter (should be converted to abbreviation)
        state_filter = next(f for f in filters if "address.state" in f.get("term", {}))
        assert state_filter["term"]["address.state"] == "CA"  # California converted to CA
        
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
            from elasticsearch import Elasticsearch
            mock_es_client = Mock(spec=Elasticsearch)
            result = demo_location_understanding(mock_es_client)
            
            # Verify result is LocationExtractionResult
            from real_estate_search.demo_queries.result_models import LocationExtractionResult
            assert isinstance(result, LocationExtractionResult)
            assert result.total_hits == 6  # 6 test queries
            assert result.returned_hits == 6
            
            # Verify module was called correctly
            mock_module.assert_called_once_with()
            # Module should be called 6 times (once for each test query)
            assert mock_instance.call_count == 6