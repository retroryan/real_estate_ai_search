"""
Mock-based integration tests for the search service layer.

These tests verify the search services work correctly without
requiring a real Elasticsearch instance.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from real_estate_search.search_service import (
    PropertySearchService,
    WikipediaSearchService,
    NeighborhoodSearchService,
    PropertySearchRequest,
    WikipediaSearchRequest,
    NeighborhoodSearchRequest,
    PropertyFilter,
    PropertyType,
    GeoLocation,
    WikipediaSearchType
)


@pytest.fixture
def mock_es_client():
    """Create a mock Elasticsearch client."""
    client = Mock()
    client.ping.return_value = True
    client.indices.exists.return_value = True
    return client


@pytest.fixture
def sample_property_response():
    """Sample Elasticsearch response for properties."""
    return {
        "hits": {
            "total": {"value": 100},
            "hits": [
                {
                    "_id": "prop-001",
                    "_score": 0.95,
                    "_source": {
                        "listing_id": "prop-001",
                        "property_type": "single_family",
                        "price": 750000,
                        "bedrooms": 4,
                        "bathrooms": 2.5,
                        "square_feet": 2200,
                        "address": {
                            "street": "123 Main St",
                            "city": "San Francisco",
                            "state": "CA",
                            "zip_code": "94102"
                        },
                        "description": "Beautiful single family home with modern amenities",
                        "features": ["garage", "garden", "pool"],
                        "location": {"lat": 37.7749, "lon": -122.4194}
                    }
                },
                {
                    "_id": "prop-002",
                    "_score": 0.87,
                    "_source": {
                        "listing_id": "prop-002",
                        "property_type": "condo",
                        "price": 550000,
                        "bedrooms": 2,
                        "bathrooms": 2,
                        "square_feet": 1200,
                        "address": {
                            "street": "456 Oak Ave",
                            "city": "San Francisco",
                            "state": "CA",
                            "zip_code": "94103"
                        },
                        "description": "Modern condo in downtown",
                        "features": ["gym", "concierge"],
                        "location": {"lat": 37.7739, "lon": -122.4185}
                    }
                }
            ]
        },
        "execution_time_ms": 45
    }


@pytest.fixture
def sample_wikipedia_response():
    """Sample Elasticsearch response for Wikipedia."""
    return {
        "hits": {
            "total": {"value": 50},
            "hits": [
                {
                    "_id": "wiki-001",
                    "_score": 0.92,
                    "_source": {
                        "page_id": "wiki-001",
                        "title": "San Francisco",
                        "url": "https://en.wikipedia.org/wiki/San_Francisco",
                        "summary": "San Francisco is a city in Northern California",
                        "categories": ["Cities in California", "San Francisco Bay Area"],
                        "content_length": 75000,
                        "full_content": "San Francisco, officially the City and County of San Francisco..."
                    },
                    "highlight": {
                        "full_content": [
                            "<em>San Francisco</em> is known for its landmarks...",
                            "The <em>San Francisco</em> Bay Area is home to..."
                        ]
                    }
                },
                {
                    "_id": "wiki-002",
                    "_score": 0.85,
                    "_source": {
                        "page_id": "wiki-002",
                        "title": "Golden Gate Bridge",
                        "url": "https://en.wikipedia.org/wiki/Golden_Gate_Bridge",
                        "summary": "The Golden Gate Bridge is a suspension bridge",
                        "categories": ["Bridges in California", "Landmarks"],
                        "content_length": 45000
                    }
                }
            ]
        },
        "execution_time_ms": 32
    }


class TestPropertySearchServiceMock:
    """Mock-based tests for PropertySearchService."""
    
    def test_text_search_execution(self, mock_es_client, sample_property_response):
        """Test that text search executes correctly."""
        mock_es_client.search.return_value = sample_property_response
        
        service = PropertySearchService(mock_es_client)
        response = service.search_text("modern home", size=10)
        
        # Verify service called Elasticsearch correctly
        mock_es_client.search.assert_called_once()
        call_args = mock_es_client.search.call_args
        
        # Check index
        assert call_args.kwargs["index"] == "properties"
        
        # Check query structure
        body = call_args.kwargs["body"]
        assert "query" in body
        assert "multi_match" in str(body["query"])
        
        # Verify response
        assert response.total_hits == 100
        assert len(response.results) == 2
        assert response.results[0].listing_id == "prop-001"
        assert response.results[0].price == 750000
    
    def test_filtered_search_with_criteria(self, mock_es_client, sample_property_response):
        """Test filtered search with multiple criteria."""
        mock_es_client.search.return_value = sample_property_response
        
        service = PropertySearchService(mock_es_client)
        
        filters = {
            "property_types": [PropertyType.SINGLE_FAMILY, PropertyType.CONDO],
            "min_price": 500000,
            "max_price": 1000000,
            "min_bedrooms": 2,
            "max_bedrooms": 5
        }
        
        response = service.search_filtered(
            query_text="home",
            filters=filters,
            size=20
        )
        
        # Verify filters were applied
        call_args = mock_es_client.search.call_args
        body = call_args.kwargs["body"]
        
        # Check that bool query with filters was created
        assert "query" in body
        assert "bool" in body["query"]
        
        # Verify response
        assert response.applied_filters is not None
        assert response.applied_filters.min_price == 500000
        assert response.applied_filters.max_price == 1000000
    
    def test_geo_distance_search(self, mock_es_client, sample_property_response):
        """Test geo-distance search functionality."""
        # Add distance to results
        geo_response = {
            **sample_property_response,
            "hits": {
                **sample_property_response["hits"],
                "hits": [
                    {
                        **hit,
                        "sort": [1.5]  # Distance in km
                    }
                    for hit in sample_property_response["hits"]["hits"]
                ]
            }
        }
        
        mock_es_client.search.return_value = geo_response
        
        service = PropertySearchService(mock_es_client)
        response = service.search_geo(
            lat=37.7749,
            lon=-122.4194,
            distance_km=5,
            query_text="family home"
        )
        
        # Verify geo query was built
        call_args = mock_es_client.search.call_args
        body = call_args.kwargs["body"]
        
        # Check for geo_distance filter
        assert "query" in body
        assert "geo_distance" in str(body)
        assert "sort" in body
        
        # Verify distance in response
        assert response.results[0].distance_km == 1.5
    
    def test_semantic_similarity_search(self, mock_es_client, sample_property_response):
        """Test semantic similarity search using embeddings."""
        # Mock getting reference property with embedding
        mock_es_client.get.return_value = {
            "_source": {
                "embedding": [0.1, 0.2, 0.3, 0.4, 0.5]
            }
        }
        mock_es_client.search.return_value = sample_property_response
        
        service = PropertySearchService(mock_es_client)
        response = service.search_similar(
            reference_property_id="prop-ref",
            size=5
        )
        
        # Verify KNN query was used
        call_args = mock_es_client.search.call_args
        body = call_args.kwargs["body"]
        
        assert "knn" in body
        assert body["knn"]["field"] == "embedding"
        assert "query_vector" in body["knn"]
        
        # Verify response
        assert len(response.results) == 2


class TestWikipediaSearchServiceMock:
    """Mock-based tests for WikipediaSearchService."""
    
    def test_fulltext_search(self, mock_es_client, sample_wikipedia_response):
        """Test full-text search across Wikipedia articles."""
        mock_es_client.search.return_value = sample_wikipedia_response
        
        service = WikipediaSearchService(mock_es_client)
        response = service.search_fulltext(
            query="San Francisco history",
            size=10
        )
        
        # Verify correct index was used
        call_args = mock_es_client.search.call_args
        assert call_args.kwargs["index"] == "wikipedia"
        
        # Verify query structure
        body = call_args.kwargs["body"]
        assert "query" in body
        assert "multi_match" in str(body)
        
        # Verify response
        assert response.search_type == WikipediaSearchType.FULL_TEXT
        assert response.total_hits == 50
        assert len(response.results) == 2
        assert response.results[0].page_id == "wiki-001"
    
    def test_search_with_categories(self, mock_es_client, sample_wikipedia_response):
        """Test search with category filtering."""
        mock_es_client.search.return_value = sample_wikipedia_response
        
        service = WikipediaSearchService(mock_es_client)
        response = service.search_by_category(
            categories=["Cities in California", "Landmarks"],
            query="bridge",
            size=5
        )
        
        # Verify category filter was applied
        call_args = mock_es_client.search.call_args
        body = call_args.kwargs["body"]
        
        assert "filter" in str(body)
        assert "categories" in str(body)
        
        # Verify response
        assert response.applied_categories == ["Cities in California", "Landmarks"]
    
    def test_search_with_highlights(self, mock_es_client, sample_wikipedia_response):
        """Test search with highlighting enabled."""
        mock_es_client.search.return_value = sample_wikipedia_response
        
        service = WikipediaSearchService(mock_es_client)
        request = WikipediaSearchRequest(
            query="San Francisco",
            include_highlights=True,
            highlight_fragment_size=200
        )
        
        response = service.search(request)
        
        # Verify highlight configuration
        call_args = mock_es_client.search.call_args
        body = call_args.kwargs["body"]
        
        assert "highlight" in body
        assert "fields" in body["highlight"]
        
        # Verify highlights in response
        assert response.results[0].highlights is not None
        assert len(response.results[0].highlights) == 2
        assert "<em>San Francisco</em>" in response.results[0].highlights[0]
    
    def test_chunk_search(self, mock_es_client, sample_wikipedia_response):
        """Test chunk-based search."""
        mock_es_client.search.return_value = sample_wikipedia_response
        
        service = WikipediaSearchService(mock_es_client)
        response = service.search_chunks(
            query="Golden Gate",
            size=10
        )
        
        # Verify correct index pattern
        call_args = mock_es_client.search.call_args
        assert call_args.kwargs["index"] == "wiki_chunks_*"
        
        # Verify search type
        assert response.search_type == WikipediaSearchType.CHUNKS


class TestNeighborhoodSearchServiceMock:
    """Mock-based tests for NeighborhoodSearchService."""
    
    def test_location_search(self, mock_es_client, sample_wikipedia_response):
        """Test location-based neighborhood search."""
        mock_es_client.search.return_value = sample_wikipedia_response
        
        service = NeighborhoodSearchService(mock_es_client)
        response = service.search_location(
            city="San Francisco",
            state="California",
            size=10
        )
        
        # Verify query includes location criteria
        call_args = mock_es_client.search.call_args
        body = call_args.kwargs["body"]
        
        assert "San Francisco" in str(body)
        assert "California" in str(body)
        
        # Verify response
        assert len(response.results) == 2
    
    def test_search_with_statistics(self, mock_es_client, sample_wikipedia_response, sample_property_response):
        """Test neighborhood search with aggregated statistics."""
        # Add aggregations to property response
        property_response_with_aggs = {
            **sample_property_response,
            "aggregations": {
                "total_properties": {"value": 25},
                "avg_price": {"value": 650000},
                "avg_bedrooms": {"value": 3.2},
                "avg_square_feet": {"value": 1800},
                "property_types": {
                    "buckets": [
                        {"key": "single_family", "doc_count": 15},
                        {"key": "condo", "doc_count": 10}
                    ]
                }
            }
        }
        
        # First call returns neighborhoods, second returns properties with stats
        mock_es_client.search.side_effect = [
            sample_wikipedia_response,
            property_response_with_aggs
        ]
        
        service = NeighborhoodSearchService(mock_es_client)
        response = service.search_with_stats(
            city="San Francisco",
            size=5
        )
        
        # Verify two searches were made
        assert mock_es_client.search.call_count == 2
        
        # Verify statistics in response
        assert response.statistics is not None
        assert response.statistics.total_properties == 25
        assert response.statistics.avg_price == 650000
        assert response.statistics.property_types["single_family"] == 15
    
    def test_search_with_related_entities(
        self,
        mock_es_client,
        sample_wikipedia_response,
        sample_property_response
    ):
        """Test neighborhood search with related entities."""
        # Setup multiple search responses
        mock_es_client.search.side_effect = [
            sample_wikipedia_response,  # Main neighborhood search
            sample_property_response,   # Related properties
            sample_wikipedia_response    # Related Wikipedia articles
        ]
        
        service = NeighborhoodSearchService(mock_es_client)
        response = service.search_related(
            city="San Francisco",
            include_properties=True,
            include_wikipedia=True,
            size=3
        )
        
        # Verify multiple searches were made
        assert mock_es_client.search.call_count == 3
        
        # Verify related entities in response
        assert response.related_properties is not None
        assert len(response.related_properties) == 2
        assert response.related_properties[0].listing_id == "prop-001"
        
        assert response.related_wikipedia is not None
        assert len(response.related_wikipedia) == 2
        assert response.related_wikipedia[0].page_id == "wiki-001"


class TestSearchServiceIntegration:
    """Test integration between services."""
    
    def test_services_share_client(self, mock_es_client):
        """Test that all services can share the same client."""
        property_service = PropertySearchService(mock_es_client)
        wiki_service = WikipediaSearchService(mock_es_client)
        neighborhood_service = NeighborhoodSearchService(mock_es_client)
        
        # All should use the same client
        assert property_service.es_client == mock_es_client
        assert wiki_service.es_client == mock_es_client
        assert neighborhood_service.es_client == mock_es_client
    
    def test_request_validation(self):
        """Test that request models validate properly."""
        # Valid requests should work
        prop_request = PropertySearchRequest(
            query="test",
            size=10,
            filters=PropertyFilter(min_price=100000)
        )
        assert prop_request.size == 10
        
        # Invalid requests should fail
        with pytest.raises(ValueError):
            PropertySearchRequest(size=0)  # Size must be >= 1
        
        with pytest.raises(ValueError):
            PropertySearchRequest(size=101)  # Size must be <= 100
        
        with pytest.raises(ValueError):
            WikipediaSearchRequest(
                query="test",
                highlight_fragment_size=30  # Must be >= 50
            )
    
    def test_error_handling(self, mock_es_client):
        """Test that services handle errors gracefully."""
        from elasticsearch.exceptions import TransportError
        
        # Setup error
        mock_es_client.search.side_effect = TransportError("Connection failed")
        
        # All services should handle the error
        property_service = PropertySearchService(mock_es_client)
        with pytest.raises(TransportError):
            property_service.search_text("test")
        
        wiki_service = WikipediaSearchService(mock_es_client)
        with pytest.raises(TransportError):
            wiki_service.search_fulltext("test")
        
        neighborhood_service = NeighborhoodSearchService(mock_es_client)
        with pytest.raises(TransportError):
            neighborhood_service.search_location(city="test")