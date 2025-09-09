"""
Integration tests for the search service layer.

These tests verify that the search services work correctly with
a real Elasticsearch instance and actual data.
"""

import pytest
import os
from typing import Optional
from elasticsearch import Elasticsearch
from pathlib import Path

# Import config first to load .env file
from real_estate_search.config import AppConfig
from real_estate_search.infrastructure.elasticsearch_client import ElasticsearchClientFactory

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


@pytest.fixture(scope="module")
def es_client():
    """Create Elasticsearch client for integration tests using proper configuration."""
    # Load configuration (which loads .env file)
    config = AppConfig.load()
    
    # Create client using the factory
    factory = ElasticsearchClientFactory(config.elasticsearch)
    client = factory.create_client()
    
    # Verify connection
    try:
        if not client.ping():
            pytest.skip("Elasticsearch is not available")
    except Exception as e:
        pytest.skip(f"Cannot connect to Elasticsearch: {str(e)}")
    
    return client


@pytest.fixture(scope="module")
def property_service(es_client):
    """Create PropertySearchService instance."""
    return PropertySearchService(es_client)


@pytest.fixture(scope="module")
def wikipedia_service(es_client):
    """Create WikipediaSearchService instance."""
    return WikipediaSearchService(es_client)


@pytest.fixture(scope="module")
def neighborhood_service(es_client):
    """Create NeighborhoodSearchService instance."""
    return NeighborhoodSearchService(es_client)


class TestPropertySearchServiceIntegration:
    """Integration tests for PropertySearchService."""
    
    def test_service_initialization(self, property_service):
        """Test that service initializes correctly."""
        assert property_service is not None
        assert property_service.index_name == "properties"
        assert property_service.es_client is not None
    
    def test_basic_text_search(self, property_service, es_client):
        """Test basic text search functionality."""
        # Check if index exists
        if not es_client.indices.exists(index="properties"):
            pytest.skip("Properties index does not exist")
        
        # Perform search
        response = property_service.search_text(
            query_text="modern home",
            size=5
        )
        
        # Verify response structure
        assert response is not None
        assert hasattr(response, "results")
        assert hasattr(response, "total_hits")
        assert hasattr(response, "execution_time_ms")
        assert isinstance(response.results, list)
        assert response.execution_time_ms >= 0
    
    def test_filtered_search(self, property_service, es_client):
        """Test filtered search with property criteria."""
        if not es_client.indices.exists(index="properties"):
            pytest.skip("Properties index does not exist")
        
        # Create filter
        filters = {
            "property_types": [PropertyType.SINGLE_FAMILY, PropertyType.CONDO],
            "min_price": 200000,
            "max_price": 800000,
            "min_bedrooms": 2
        }
        
        # Perform filtered search
        response = property_service.search_filtered(
            query_text="home",
            filters=filters,
            size=10
        )
        
        # Verify response
        assert response is not None
        assert response.applied_filters is not None
        assert response.applied_filters.min_price == 200000
        assert response.applied_filters.max_price == 800000
    
    def test_geo_distance_search(self, property_service, es_client):
        """Test geo-distance search."""
        if not es_client.indices.exists(index="properties"):
            pytest.skip("Properties index does not exist")
        
        # Search near San Francisco coordinates
        response = property_service.search_geo(
            lat=37.7749,
            lon=-122.4194,
            distance_km=10,
            query_text=None,
            size=5
        )
        
        # Verify response
        assert response is not None
        assert isinstance(response.results, list)
        
        # Check distance is populated for geo searches
        for result in response.results:
            if result.distance_km is not None:
                assert result.distance_km >= 0
    
    def test_search_with_request_model(self, property_service, es_client):
        """Test search using PropertySearchRequest model."""
        if not es_client.indices.exists(index="properties"):
            pytest.skip("Properties index does not exist")
        
        # Create request
        request = PropertySearchRequest(
            query="family home",
            filters=PropertyFilter(
                min_bedrooms=3,
                max_bedrooms=5
            ),
            size=3,
            include_highlights=True
        )
        
        # Perform search
        response = property_service.search(request)
        
        # Verify response
        assert response is not None
        assert len(response.results) <= 3
    
    def test_empty_search(self, property_service, es_client):
        """Test search with no query (match all)."""
        if not es_client.indices.exists(index="properties"):
            pytest.skip("Properties index does not exist")
        
        # Search without query
        request = PropertySearchRequest(size=1)
        response = property_service.search(request)
        
        # Should return results (match all)
        assert response is not None
        assert response.total_hits >= 0


class TestWikipediaSearchServiceIntegration:
    """Integration tests for WikipediaSearchService."""
    
    def test_service_initialization(self, wikipedia_service):
        """Test that service initializes correctly."""
        assert wikipedia_service is not None
        assert wikipedia_service.full_text_index == "wikipedia"
        assert wikipedia_service.chunks_index_prefix == "wiki_chunks"
        assert wikipedia_service.summaries_index_prefix == "wiki_summaries"
    
    def test_fulltext_search(self, wikipedia_service, es_client):
        """Test full-text search across Wikipedia articles."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Perform search
        response = wikipedia_service.search_fulltext(
            query="San Francisco",
            size=5
        )
        
        # Verify response
        assert response is not None
        assert response.search_type == WikipediaSearchType.FULL_TEXT
        assert isinstance(response.results, list)
        assert response.execution_time_ms >= 0
    
    def test_category_filtering(self, wikipedia_service, es_client):
        """Test search with category filtering."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Search with categories
        response = wikipedia_service.search_by_category(
            categories=["Cities", "California"],
            query="history",
            size=3
        )
        
        # Verify response
        assert response is not None
        assert response.applied_categories == ["Cities", "California"]
    
    def test_search_with_highlights(self, wikipedia_service, es_client):
        """Test search with highlighting enabled."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Create request with highlights
        request = WikipediaSearchRequest(
            query="Golden Gate",
            search_type=WikipediaSearchType.FULL_TEXT,
            include_highlights=True,
            highlight_fragment_size=200,
            size=2
        )
        
        # Perform search
        response = wikipedia_service.search(request)
        
        # Verify response
        assert response is not None
        
        # Check if highlights are present when available
        for result in response.results:
            if result.highlights:
                assert isinstance(result.highlights, list)
                for highlight in result.highlights:
                    assert len(highlight) <= 300  # Account for markup
    
    def test_search_types(self, wikipedia_service, es_client):
        """Test different search types."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Test full-text search
        response = wikipedia_service.search(
            WikipediaSearchRequest(
                query="bridge",
                search_type=WikipediaSearchType.FULL_TEXT,
                size=1
            )
        )
        assert response.search_type == WikipediaSearchType.FULL_TEXT
        
        # Note: Chunks and summaries indices might not exist in test environment
        # These would need separate index setup


class TestNeighborhoodSearchServiceIntegration:
    """Integration tests for NeighborhoodSearchService."""
    
    def test_service_initialization(self, neighborhood_service):
        """Test that service initializes correctly."""
        assert neighborhood_service is not None
        assert neighborhood_service.wikipedia_index == "wikipedia"
        assert neighborhood_service.properties_index == "properties"
    
    def test_location_search(self, neighborhood_service, es_client):
        """Test location-based neighborhood search."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Search by location
        response = neighborhood_service.search_location(
            city="San Francisco",
            state="California",
            size=5
        )
        
        # Verify response
        assert response is not None
        assert isinstance(response.results, list)
        assert response.execution_time_ms >= 0
    
    def test_search_with_statistics(self, neighborhood_service, es_client):
        """Test neighborhood search with aggregated statistics."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Search with statistics
        response = neighborhood_service.search_with_stats(
            city="San Francisco",
            size=3
        )
        
        # Verify response structure
        assert response is not None
        
        # Statistics might be None if properties index doesn't exist
        if response.statistics:
            assert hasattr(response.statistics, "total_properties")
            assert hasattr(response.statistics, "avg_price")
            assert hasattr(response.statistics, "property_types")
    
    def test_search_with_related_entities(self, neighborhood_service, es_client):
        """Test neighborhood search with related entities."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Search with related entities
        response = neighborhood_service.search_related(
            city="San Francisco",
            include_properties=True,
            include_wikipedia=True,
            size=2
        )
        
        # Verify response
        assert response is not None
        
        # Related entities might be None if indices don't exist
        if response.related_properties:
            assert isinstance(response.related_properties, list)
            for prop in response.related_properties:
                assert hasattr(prop, "listing_id")
                assert hasattr(prop, "price")
        
        if response.related_wikipedia:
            assert isinstance(response.related_wikipedia, list)
            for article in response.related_wikipedia:
                assert hasattr(article, "page_id")
                assert hasattr(article, "title")
    
    def test_search_request_model(self, neighborhood_service, es_client):
        """Test search using NeighborhoodSearchRequest model."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Create request
        request = NeighborhoodSearchRequest(
            city="San Francisco",
            query="historic",
            include_statistics=False,
            size=3
        )
        
        # Perform search
        response = neighborhood_service.search(request)
        
        # Verify response
        assert response is not None
        assert len(response.results) <= 3


class TestCrossServiceIntegration:
    """Test interactions between different search services."""
    
    def test_all_services_use_same_client(
        self,
        es_client,
        property_service,
        wikipedia_service,
        neighborhood_service
    ):
        """Verify all services can use the same Elasticsearch client."""
        assert property_service.es_client == es_client
        assert wikipedia_service.es_client == es_client
        assert neighborhood_service.es_client == es_client
    
    def test_services_are_independent(
        self,
        property_service,
        wikipedia_service,
        neighborhood_service
    ):
        """Verify services are independent of each other."""
        # Each service should have its own index configuration
        assert property_service.index_name == "properties"
        assert wikipedia_service.full_text_index == "wikipedia"
        assert neighborhood_service.wikipedia_index == "wikipedia"
        
        # Services should not share state
        assert property_service != wikipedia_service
        assert wikipedia_service != neighborhood_service
        assert property_service != neighborhood_service
    
    def test_error_handling_consistency(
        self,
        property_service,
        wikipedia_service,
        neighborhood_service
    ):
        """Test that all services handle errors consistently."""
        # Test with invalid index names (temporarily change them)
        original_property_index = property_service.index_name
        original_wiki_index = wikipedia_service.full_text_index
        
        try:
            # Set non-existent indices
            property_service.index_name = "non_existent_index_123"
            wikipedia_service.full_text_index = "non_existent_index_456"
            
            # All should handle gracefully (not crash)
            try:
                property_response = property_service.search_text("test")
                # If index doesn't exist, should get empty results or error
            except Exception as e:
                assert "non_existent_index" in str(e).lower() or "not found" in str(e).lower()
            
            try:
                wiki_response = wikipedia_service.search_fulltext("test")
            except Exception as e:
                assert "non_existent_index" in str(e).lower() or "not found" in str(e).lower()
        
        finally:
            # Restore original indices
            property_service.index_name = original_property_index
            wikipedia_service.full_text_index = original_wiki_index


class TestSearchServicePerformance:
    """Performance-related integration tests."""
    
    def test_search_response_times(
        self,
        property_service,
        wikipedia_service,
        neighborhood_service,
        es_client
    ):
        """Verify search response times are reasonable."""
        # Skip if indices don't exist
        if not es_client.indices.exists(index="properties"):
            pytest.skip("Properties index does not exist")
        
        # Property search
        property_response = property_service.search_text("test", size=1)
        assert property_response.execution_time_ms < 5000  # Should be under 5 seconds
        
        if es_client.indices.exists(index="wikipedia"):
            # Wikipedia search
            wiki_response = wikipedia_service.search_fulltext("test", size=1)
            assert wiki_response.execution_time_ms < 5000
            
            # Neighborhood search
            neighborhood_response = neighborhood_service.search_location(
                city="San Francisco",
                size=1
            )
            assert neighborhood_response.execution_time_ms < 5000
    
    def test_pagination_support(self, property_service, es_client):
        """Test that pagination works correctly."""
        if not es_client.indices.exists(index="properties"):
            pytest.skip("Properties index does not exist")
        
        # First page
        page1 = property_service.search(
            PropertySearchRequest(
                query="home",
                size=2,
                from_offset=0
            )
        )
        
        # Second page
        page2 = property_service.search(
            PropertySearchRequest(
                query="home",
                size=2,
                from_offset=2
            )
        )
        
        # Verify pagination
        assert page1 is not None
        assert page2 is not None
        
        # If there are enough results, pages should be different
        if page1.total_hits > 2:
            if page1.results and page2.results:
                # Results should be different
                page1_ids = {r.listing_id for r in page1.results}
                page2_ids = {r.listing_id for r in page2.results}
                assert page1_ids != page2_ids  # Different results on different pages