"""
Tests for neighborhood search service.
"""

import pytest
from unittest.mock import Mock
from ..elasticsearch_compat import Elasticsearch

from ..neighborhoods import NeighborhoodSearchService
from ..models import (
    NeighborhoodSearchRequest,
    NeighborhoodSearchResponse,
    NeighborhoodStatistics,
    RelatedProperty,
    RelatedWikipediaArticle
)


class TestNeighborhoodSearchService:
    """Test cases for NeighborhoodSearchService."""
    
    @pytest.fixture
    def mock_es_client(self):
        """Create a mock Elasticsearch client."""
        return Mock(spec=Elasticsearch)
    
    @pytest.fixture
    def service(self, mock_es_client):
        """Create a NeighborhoodSearchService instance with mock client."""
        return NeighborhoodSearchService(mock_es_client)
    
    @pytest.fixture
    def sample_neighborhood_response(self):
        """Sample Elasticsearch response for neighborhoods."""
        return {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_id": "page-001",
                        "_score": 0.95,
                        "_source": {
                            "page_id": "page-001",
                            "title": "Nob Hill, San Francisco",
                            "summary": "Nob Hill is a neighborhood in San Francisco",
                            "categories": ["Neighborhoods", "San Francisco"],
                            "url": "https://en.wikipedia.org/wiki/Nob_Hill"
                        }
                    },
                    {
                        "_id": "page-002",
                        "_score": 0.85,
                        "_source": {
                            "page_id": "page-002",
                            "title": "Mission District, San Francisco",
                            "summary": "The Mission District is a vibrant neighborhood",
                            "categories": ["Neighborhoods", "San Francisco"],
                            "url": "https://en.wikipedia.org/wiki/Mission_District"
                        }
                    }
                ]
            },
            "execution_time_ms": 40
        }
    
    @pytest.fixture
    def sample_property_response(self):
        """Sample property search response for related data."""
        return {
            "hits": {
                "total": {"value": 10},
                "hits": [
                    {
                        "_source": {
                            "listing_id": "prop-001",
                            "address": {
                                "street": "123 Main St",
                                "city": "San Francisco",
                                "state": "CA"
                            },
                            "price": 800000,
                            "property_type": "condo"
                        }
                    },
                    {
                        "_source": {
                            "listing_id": "prop-002",
                            "address": {
                                "street": "456 Oak Ave",
                                "city": "San Francisco",
                                "state": "CA"
                            },
                            "price": 1200000,
                            "property_type": "single_family"
                        }
                    }
                ]
            },
            "aggregations": {
                "total_properties": {"value": 10},
                "avg_price": {"value": 950000},
                "avg_bedrooms": {"value": 2.5},
                "avg_square_feet": {"value": 1500},
                "property_types": {
                    "buckets": [
                        {"key": "condo", "doc_count": 6},
                        {"key": "single_family", "doc_count": 4}
                    ]
                }
            }
        }
    
    def test_search_location(self, service, mock_es_client, sample_neighborhood_response):
        """Test location-based neighborhood search."""
        mock_es_client.search.return_value = sample_neighborhood_response
        
        response = service.search_location(
            city="San Francisco",
            state="California",
            size=10
        )
        
        assert isinstance(response, NeighborhoodSearchResponse)
        assert response.total_hits == 2
        assert len(response.results) == 2
        assert response.results[0].name == "Nob Hill, San Francisco"
        assert response.results[0].city in ["San Francisco", "Unknown"]
        
        # Verify query structure
        call_args = mock_es_client.search.call_args
        assert call_args[1]["index"] == "wikipedia"
        query_body = call_args[1]["body"]
        assert "categories" in str(query_body)
        assert "Neighborhoods" in str(query_body)
    
    def test_search_with_stats(
        self,
        service,
        mock_es_client,
        sample_neighborhood_response,
        sample_property_response
    ):
        """Test neighborhood search with statistics."""
        # Setup mock responses
        mock_es_client.search.side_effect = [
            sample_neighborhood_response,
            sample_property_response
        ]
        
        response = service.search_with_stats(
            city="San Francisco",
            size=10
        )
        
        assert isinstance(response, NeighborhoodSearchResponse)
        assert response.statistics is not None
        assert response.statistics.total_properties == 10
        assert response.statistics.avg_price == 950000
        assert response.statistics.avg_bedrooms == 2.5
        assert response.statistics.avg_square_feet == 1500
        assert "condo" in response.statistics.property_types
        assert response.statistics.property_types["condo"] == 6
        
        # Verify two searches were made
        assert mock_es_client.search.call_count == 2
    
    def test_search_related(
        self,
        service,
        mock_es_client,
        sample_neighborhood_response,
        sample_property_response
    ):
        """Test neighborhood search with related entities."""
        # Add Wikipedia response for related articles
        wiki_response = {
            "hits": {
                "total": {"value": 3},
                "hits": [
                    {
                        "_id": "page-003",
                        "_score": 0.75,
                        "_source": {
                            "page_id": "page-003",
                            "title": "Golden Gate Bridge",
                            "summary": "The Golden Gate Bridge is an iconic landmark in San Francisco"
                        }
                    }
                ]
            }
        }
        
        # Setup mock responses
        mock_es_client.search.side_effect = [
            sample_neighborhood_response,
            sample_property_response,
            wiki_response
        ]
        
        response = service.search_related(
            city="San Francisco",
            include_properties=True,
            include_wikipedia=True,
            size=10
        )
        
        assert isinstance(response, NeighborhoodSearchResponse)
        
        # Check related properties
        assert response.related_properties is not None
        assert len(response.related_properties) == 2
        assert response.related_properties[0].listing_id == "prop-001"
        assert response.related_properties[0].price == 800000
        
        # Check related Wikipedia articles
        assert response.related_wikipedia is not None
        assert len(response.related_wikipedia) == 1
        assert response.related_wikipedia[0].title == "Golden Gate Bridge"
        
        # Verify three searches were made
        assert mock_es_client.search.call_count == 3
    
    def test_search_with_query(self, service, mock_es_client, sample_neighborhood_response):
        """Test neighborhood search with free text query."""
        mock_es_client.search.return_value = sample_neighborhood_response
        
        request = NeighborhoodSearchRequest(
            query="historic neighborhoods",
            city="San Francisco",
            size=10
        )
        
        response = service.search(request)
        
        assert isinstance(response, NeighborhoodSearchResponse)
        
        # Verify multi_match query was included
        call_args = mock_es_client.search.call_args
        query_body = call_args[1]["body"]
        assert "multi_match" in str(query_body)
        assert "historic neighborhoods" in str(query_body)
    
    def test_search_no_criteria(self, service, mock_es_client, sample_neighborhood_response):
        """Test neighborhood search with no specific criteria."""
        mock_es_client.search.return_value = sample_neighborhood_response
        
        request = NeighborhoodSearchRequest(size=10)
        
        response = service.search(request)
        
        assert isinstance(response, NeighborhoodSearchResponse)
        
        # Verify match_all query was used
        call_args = mock_es_client.search.call_args
        query_body = call_args[1]["body"]
        assert "match_all" in str(query_body)
    
    def test_extract_city(self, service):
        """Test city extraction from Wikipedia source."""
        source = {"title": "Nob Hill, San Francisco"}
        city = service._extract_city(source)
        assert city == "San Francisco"
        
        source = {"title": "Mission District"}
        city = service._extract_city(source)
        assert city is None
    
    def test_extract_state(self, service):
        """Test state extraction from Wikipedia source."""
        source = {
            "title": "Nob Hill",
            "summary": "A neighborhood in San Francisco, California"
        }
        state = service._extract_state(source)
        assert state == "California"
        
        source = {
            "title": "Some Place",
            "summary": "A place somewhere"
        }
        state = service._extract_state(source)
        assert state is None
    
    def test_search_error_handling(self, service, mock_es_client):
        """Test error handling during search."""
        mock_es_client.search.side_effect = Exception("Elasticsearch error")
        
        with pytest.raises(Exception) as exc_info:
            service.search_location(city="San Francisco")
        
        assert "Elasticsearch error" in str(exc_info.value)
    
    def test_related_data_error_handling(
        self,
        service,
        mock_es_client,
        sample_neighborhood_response
    ):
        """Test error handling when fetching related data fails."""
        # First search succeeds, second fails
        mock_es_client.search.side_effect = [
            sample_neighborhood_response,
            Exception("Property search failed")
        ]
        
        response = service.search_with_stats(city="San Francisco")
        
        # Should still return neighborhood results
        assert isinstance(response, NeighborhoodSearchResponse)
        assert response.total_hits == 2
        # But no statistics due to error
        assert response.statistics is None