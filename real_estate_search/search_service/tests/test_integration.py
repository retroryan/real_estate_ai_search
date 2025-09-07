"""
Integration tests for search service layer.
"""

import pytest
from unittest.mock import Mock
from elasticsearch import Elasticsearch

from ..base import BaseSearchService
from ..properties import PropertySearchService
from ..wikipedia import WikipediaSearchService
from ..neighborhoods import NeighborhoodSearchService
from ..models import (
    PropertySearchRequest,
    WikipediaSearchRequest,
    NeighborhoodSearchRequest,
    PropertyFilter,
    PropertyType,
    GeoLocation,
    WikipediaSearchType
)


class TestSearchServiceIntegration:
    """Integration tests for all search services."""
    
    @pytest.fixture
    def mock_es_client(self):
        """Create a mock Elasticsearch client."""
        return Mock(spec=Elasticsearch)
    
    def test_all_services_initialize(self, mock_es_client):
        """Test that all services can be initialized."""
        base_service = BaseSearchService(mock_es_client)
        property_service = PropertySearchService(mock_es_client)
        wiki_service = WikipediaSearchService(mock_es_client)
        neighborhood_service = NeighborhoodSearchService(mock_es_client)
        
        assert base_service.es_client == mock_es_client
        assert property_service.es_client == mock_es_client
        assert wiki_service.es_client == mock_es_client
        assert neighborhood_service.es_client == mock_es_client
    
    def test_property_service_methods(self, mock_es_client):
        """Test all PropertySearchService methods are callable."""
        service = PropertySearchService(mock_es_client)
        
        # Mock search response
        mock_es_client.search.return_value = {
            "hits": {"total": {"value": 0}, "hits": []},
            "execution_time_ms": 10
        }
        
        # Test all search methods
        response = service.search_text("test query")
        assert response.total_hits == 0
        
        response = service.search_filtered(
            query_text="test",
            filters={"min_price": 100000}
        )
        assert response.total_hits == 0
        
        response = service.search_geo(
            lat=37.0, lon=-122.0, distance_km=10
        )
        assert response.total_hits == 0
        
        # Test similarity search (needs mock document)
        mock_es_client.get.return_value = {
            "_source": {"embedding": [0.1, 0.2, 0.3]}
        }
        response = service.search_similar("ref-id")
        assert response.total_hits == 0
    
    def test_wikipedia_service_methods(self, mock_es_client):
        """Test all WikipediaSearchService methods are callable."""
        service = WikipediaSearchService(mock_es_client)
        
        # Mock search response
        mock_es_client.search.return_value = {
            "hits": {"total": {"value": 0}, "hits": []},
            "execution_time_ms": 10
        }
        
        # Test all search methods
        response = service.search_fulltext("test query")
        assert response.total_hits == 0
        assert response.search_type == WikipediaSearchType.FULL_TEXT
        
        response = service.search_chunks("test query")
        assert response.total_hits == 0
        assert response.search_type == WikipediaSearchType.CHUNKS
        
        response = service.search_summaries("test query")
        assert response.total_hits == 0
        assert response.search_type == WikipediaSearchType.SUMMARIES
        
        response = service.search_by_category(["Test Category"])
        assert response.total_hits == 0
    
    def test_neighborhood_service_methods(self, mock_es_client):
        """Test all NeighborhoodSearchService methods are callable."""
        service = NeighborhoodSearchService(mock_es_client)
        
        # Mock search response
        mock_es_client.search.return_value = {
            "hits": {"total": {"value": 0}, "hits": []},
            "execution_time_ms": 10
        }
        
        # Test all search methods
        response = service.search_location(city="San Francisco")
        assert response.total_hits == 0
        
        response = service.search_with_stats(city="San Francisco")
        assert response.total_hits == 0
        
        response = service.search_related(
            city="San Francisco",
            include_properties=True,
            include_wikipedia=True
        )
        assert response.total_hits == 0
    
    def test_request_validation(self):
        """Test that request models validate properly."""
        # Valid property request
        prop_request = PropertySearchRequest(
            query="test",
            size=10,
            filters=PropertyFilter(min_price=100000)
        )
        assert prop_request.size == 10
        assert prop_request.filters.min_price == 100000
        
        # Valid Wikipedia request
        wiki_request = WikipediaSearchRequest(
            query="test",
            search_type=WikipediaSearchType.FULL_TEXT,
            size=5
        )
        assert wiki_request.size == 5
        assert wiki_request.search_type == WikipediaSearchType.FULL_TEXT
        
        # Valid neighborhood request
        neighborhood_request = NeighborhoodSearchRequest(
            city="San Francisco",
            state="California",
            include_statistics=True
        )
        assert neighborhood_request.city == "San Francisco"
        assert neighborhood_request.include_statistics is True
    
    def test_error_handling_consistency(self, mock_es_client):
        """Test that all services handle errors consistently."""
        # Setup error
        mock_es_client.search.side_effect = Exception("Test error")
        
        # Test each service
        property_service = PropertySearchService(mock_es_client)
        wiki_service = WikipediaSearchService(mock_es_client)
        neighborhood_service = NeighborhoodSearchService(mock_es_client)
        
        with pytest.raises(Exception) as exc:
            property_service.search_text("test")
        assert "Test error" in str(exc.value)
        
        with pytest.raises(Exception) as exc:
            wiki_service.search_fulltext("test")
        assert "Test error" in str(exc.value)
        
        with pytest.raises(Exception) as exc:
            neighborhood_service.search_location(city="test")
        assert "Test error" in str(exc.value)