"""
Tests for property search service.
"""

import pytest
from unittest.mock import Mock
from ..elasticsearch_compat import Elasticsearch

from ..properties import PropertySearchService
from ..models import (
    PropertySearchRequest,
    PropertySearchResponse,
    PropertyFilter,
    PropertyType,
    GeoLocation
)


class TestPropertySearchService:
    """Test cases for PropertySearchService."""
    
    @pytest.fixture
    def mock_es_client(self):
        """Create a mock Elasticsearch client."""
        return Mock(spec=Elasticsearch)
    
    @pytest.fixture
    def service(self, mock_es_client):
        """Create a PropertySearchService instance with mock client."""
        return PropertySearchService(mock_es_client)
    
    @pytest.fixture
    def sample_es_response(self):
        """Sample Elasticsearch response for testing."""
        return {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_id": "prop-001",
                        "_score": 0.95,
                        "_source": {
                            "listing_id": "prop-001",
                            "property_type": "single_family",
                            "price": 500000,
                            "bedrooms": 3,
                            "bathrooms": 2,
                            "square_feet": 1800,
                            "address": {
                                "street": "123 Main St",
                                "city": "San Francisco",
                                "state": "CA",
                                "zip_code": "94102"
                            },
                            "description": "Beautiful single family home",
                            "features": ["garage", "garden"]
                        }
                    },
                    {
                        "_id": "prop-002",
                        "_score": 0.85,
                        "_source": {
                            "listing_id": "prop-002",
                            "property_type": "condo",
                            "price": 350000,
                            "bedrooms": 2,
                            "bathrooms": 1,
                            "square_feet": 1200,
                            "address": {
                                "street": "456 Oak Ave",
                                "city": "San Francisco",
                                "state": "CA",
                                "zip_code": "94103"
                            },
                            "description": "Modern condo in downtown",
                            "features": ["gym", "pool"]
                        }
                    }
                ]
            },
            "execution_time_ms": 50
        }
    
    def test_search_text(self, service, mock_es_client, sample_es_response):
        """Test basic text search."""
        mock_es_client.search.return_value = sample_es_response
        
        response = service.search_text("single family home", size=10)
        
        assert isinstance(response, PropertySearchResponse)
        assert response.total_hits == 2
        assert len(response.results) == 2
        assert response.results[0].listing_id == "prop-001"
        assert response.results[0].property_type == "single_family"
        
        # Verify Elasticsearch was called
        mock_es_client.search.assert_called_once()
        call_args = mock_es_client.search.call_args
        assert call_args[1]["index"] == "properties"
        assert "multi_match" in str(call_args[1]["body"])
    
    def test_search_filtered(self, service, mock_es_client, sample_es_response):
        """Test filtered search."""
        mock_es_client.search.return_value = sample_es_response
        
        filters = {
            "property_types": [PropertyType.SINGLE_FAMILY],
            "min_price": 400000,
            "max_price": 600000,
            "min_bedrooms": 3
        }
        
        response = service.search_filtered(
            query_text="home",
            filters=filters,
            size=10
        )
        
        assert isinstance(response, PropertySearchResponse)
        assert response.total_hits == 2
        assert response.applied_filters is not None
        assert response.applied_filters.min_price == 400000
        
        # Verify filter query was built
        call_args = mock_es_client.search.call_args
        query_body = call_args[1]["body"]
        assert "bool" in query_body["query"]
        assert "filter" in query_body["query"]["bool"]
    
    def test_search_geo(self, service, mock_es_client):
        """Test geo-distance search."""
        # Add sort values for distance
        geo_response = {
            "hits": {
                "total": {"value": 1},
                "hits": [{
                    "_id": "prop-001",
                    "_score": 0.95,
                    "_source": {
                        "listing_id": "prop-001",
                        "property_type": "single_family",
                        "price": 500000,
                        "bedrooms": 3,
                        "bathrooms": 2,
                        "square_feet": 1800,
                        "address": {
                            "street": "123 Main St",
                            "city": "San Francisco",
                            "state": "CA",
                            "zip_code": "94102"
                        },
                        "description": "Beautiful home",
                        "features": []
                    },
                    "sort": [2.5]  # Distance in km
                }]
            },
            "execution_time_ms": 30
        }
        
        mock_es_client.search.return_value = geo_response
        
        response = service.search_geo(
            lat=37.7749,
            lon=-122.4194,
            distance_km=5,
            query_text="family home",
            size=10
        )
        
        assert isinstance(response, PropertySearchResponse)
        assert response.total_hits == 1
        assert response.results[0].distance_km == 2.5
        
        # Verify geo query was built
        call_args = mock_es_client.search.call_args
        query_body = call_args[1]["body"]
        assert "geo_distance" in str(query_body)
        assert "sort" in query_body
    
    def test_search_similar(self, service, mock_es_client, sample_es_response):
        """Test semantic similarity search."""
        # Mock getting reference property with embedding
        mock_es_client.get.return_value = {
            "_source": {
                "embedding": [0.1, 0.2, 0.3, 0.4, 0.5]
            }
        }
        mock_es_client.search.return_value = sample_es_response
        
        response = service.search_similar(
            reference_property_id="prop-ref",
            size=10
        )
        
        assert isinstance(response, PropertySearchResponse)
        assert response.total_hits == 2
        
        # Verify KNN query was built
        call_args = mock_es_client.search.call_args
        query_body = call_args[1]["body"]
        assert "knn" in query_body
        assert query_body["knn"]["field"] == "embedding"
    
    def test_search_similar_no_embedding(self, service, mock_es_client):
        """Test similarity search when reference has no embedding."""
        # Mock reference property without embedding
        mock_es_client.get.return_value = {
            "_source": {}
        }
        
        with pytest.raises(ValueError) as exc_info:
            service.search_similar("prop-ref", size=10)
        
        assert "no embedding" in str(exc_info.value).lower()
    
    def test_search_with_highlights(self, service, mock_es_client):
        """Test search with highlighting enabled."""
        response_with_highlights = {
            "hits": {
                "total": {"value": 1},
                "hits": [{
                    "_id": "prop-001",
                    "_score": 0.95,
                    "_source": {
                        "listing_id": "prop-001",
                        "property_type": "single_family",
                        "price": 500000,
                        "bedrooms": 3,
                        "bathrooms": 2,
                        "square_feet": 1800,
                        "address": {
                            "street": "123 Main St",
                            "city": "San Francisco",
                            "state": "CA",
                            "zip_code": "94102"
                        },
                        "description": "Beautiful home",
                        "features": ["garage"]
                    },
                    "highlight": {
                        "description": ["<em>Beautiful</em> home"],
                        "features": ["<em>garage</em>"]
                    }
                }]
            },
            "execution_time_ms": 25
        }
        
        mock_es_client.search.return_value = response_with_highlights
        
        request = PropertySearchRequest(
            query="beautiful garage",
            size=10,
            include_highlights=True
        )
        
        response = service.search(request)
        
        assert response.results[0].highlights is not None
        assert "description" in response.results[0].highlights
        assert "<em>Beautiful</em>" in response.results[0].highlights["description"][0]
    
    def test_search_with_pagination(self, service, mock_es_client, sample_es_response):
        """Test search with pagination."""
        mock_es_client.search.return_value = sample_es_response
        
        request = PropertySearchRequest(
            query="home",
            size=5,
            from_offset=10
        )
        
        response = service.search(request)
        
        assert isinstance(response, PropertySearchResponse)
        
        # Verify pagination parameters were passed
        call_args = mock_es_client.search.call_args
        assert call_args[1]["body"]["size"] == 5
        assert call_args[1]["body"]["from"] == 10
    
    def test_search_error_handling(self, service, mock_es_client):
        """Test error handling during search."""
        mock_es_client.search.side_effect = Exception("Elasticsearch error")
        
        with pytest.raises(Exception) as exc_info:
            service.search_text("test query")
        
        assert "Elasticsearch error" in str(exc_info.value)