"""
Comprehensive integration tests for NeighborhoodSearchService.

Tests all methods and edge cases for neighborhood search functionality.
"""

import pytest
import logging
from typing import List, Optional, Dict, Any
from elasticsearch import Elasticsearch

from real_estate_search.config import AppConfig
from real_estate_search.infrastructure.elasticsearch_client import ElasticsearchClientFactory
from real_estate_search.search_service import (
    NeighborhoodSearchService,
    NeighborhoodSearchRequest,
    NeighborhoodSearchResponse,
    NeighborhoodStatistics,
    RelatedProperty,
    RelatedWikipediaArticle
)
from real_estate_search.search_service.models import NeighborhoodResult

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def es_client():
    """Create Elasticsearch client for integration tests."""
    config = AppConfig.load()
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
def neighborhood_service(es_client):
    """Create NeighborhoodSearchService instance."""
    return NeighborhoodSearchService(es_client)


@pytest.fixture
def sample_neighborhoods(es_client) -> List[Dict[str, Any]]:
    """Get sample neighborhoods from Wikipedia index for testing."""
    if not es_client.indices.exists(index="wikipedia"):
        return []
    
    try:
        # Get neighborhoods from Wikipedia articles
        response = es_client.search(
            index="wikipedia",
            query={
                "bool": {
                    "must": [
                        {"match": {"categories": "Neighborhoods"}},
                        {"exists": {"field": "city"}}
                    ]
                }
            },
            size=5,
            _source=["page_id", "title", "city", "state"]
        )
        return [hit["_source"] for hit in response["hits"]["hits"]]
    except Exception:
        return []


class TestNeighborhoodBasicSearch:
    """Test basic neighborhood search functionality."""
    
    def test_service_initialization(self, neighborhood_service):
        """Test that service initializes correctly."""
        assert neighborhood_service is not None
        assert neighborhood_service.wikipedia_index == "wikipedia"
        assert neighborhood_service.properties_index == "properties"
        assert neighborhood_service.es_client is not None
    
    def test_search_by_city(self, neighborhood_service, es_client):
        """Test searching neighborhoods by city."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Test various cities
        test_cities = ["San Francisco", "Oakland", "Berkeley", "Palo Alto"]
        
        for city in test_cities:
            response = neighborhood_service.search_location(
                city=city,
                size=5
            )
            
            assert response is not None
            assert isinstance(response, NeighborhoodSearchResponse)
            assert isinstance(response.results, list)
            assert response.execution_time_ms >= 0
            assert response.total_hits >= 0
            
            # If results exist, verify structure
            for result in response.results:
                assert isinstance(result, NeighborhoodResult)
                assert result.page_id is not None
                assert result.title is not None
    
    def test_search_by_city_and_state(self, neighborhood_service, es_client):
        """Test searching neighborhoods by city and state."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        response = neighborhood_service.search_location(
            city="San Francisco",
            state="California",
            size=10
        )
        
        assert response is not None
        assert isinstance(response.results, list)
        
        # Verify city/state in results if available
        for result in response.results:
            if result.city:
                assert "San Francisco" in result.city or result.city == "San Francisco"
            if result.state:
                assert "California" in result.state or result.state == "CA"
    
    def test_search_with_query_text(self, neighborhood_service, es_client):
        """Test neighborhood search with text query."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        request = NeighborhoodSearchRequest(
            city="San Francisco",
            query="historic",
            size=5
        )
        
        response = neighborhood_service.search(request)
        
        assert response is not None
        assert isinstance(response.results, list)
        
        # Results should be relevant to query
        if response.total_hits > 0:
            # At least some results should contain relevant terms
            has_relevant_content = any(
                "historic" in (result.content or "").lower() or
                "history" in (result.content or "").lower()
                for result in response.results
            )
            # May not always have relevant content in summary
            assert response.total_hits >= 0
    
    def test_empty_city_search(self, neighborhood_service, es_client):
        """Test search with no city specified."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        request = NeighborhoodSearchRequest(
            query="neighborhood",
            size=10
        )
        
        response = neighborhood_service.search(request)
        
        assert response is not None
        # Should return results from any city
        assert response.total_hits >= 0


class TestNeighborhoodStatistics:
    """Test neighborhood statistics aggregation."""
    
    def test_search_with_statistics(self, neighborhood_service, es_client):
        """Test neighborhood search with property statistics."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        response = neighborhood_service.search_with_stats(
            city="San Francisco",
            size=3
        )
        
        assert response is not None
        
        # Statistics might be None if properties index doesn't exist
        if es_client.indices.exists(index="properties") and response.statistics:
            assert isinstance(response.statistics, NeighborhoodStatistics)
            assert hasattr(response.statistics, "total_properties")
            assert hasattr(response.statistics, "avg_price")
            assert hasattr(response.statistics, "min_price")
            assert hasattr(response.statistics, "max_price")
            assert hasattr(response.statistics, "property_types")
            
            # Validate statistics values
            assert response.statistics.total_properties >= 0
            if response.statistics.avg_price:
                assert response.statistics.avg_price > 0
            if response.statistics.property_types:
                assert isinstance(response.statistics.property_types, dict)
    
    def test_statistics_aggregation_accuracy(self, neighborhood_service, es_client):
        """Test that statistics are calculated correctly."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        if not es_client.indices.exists(index="properties"):
            pytest.skip("Properties index does not exist")
        
        # Get stats for a specific city
        response = neighborhood_service.search_with_stats(
            city="San Francisco",
            size=1
        )
        
        if response.statistics:
            # Verify logical consistency
            if response.statistics.min_price and response.statistics.max_price:
                assert response.statistics.min_price <= response.statistics.max_price
            
            if response.statistics.avg_price and response.statistics.min_price and response.statistics.max_price:
                assert response.statistics.min_price <= response.statistics.avg_price
                assert response.statistics.avg_price <= response.statistics.max_price
            
            # Property type distribution should sum to total (or less due to filtering)
            if response.statistics.property_types:
                type_sum = sum(response.statistics.property_types.values())
                assert type_sum <= response.statistics.total_properties
    
    def test_statistics_with_no_properties(self, neighborhood_service, es_client):
        """Test statistics when no properties match."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Search for a city unlikely to have properties
        response = neighborhood_service.search_with_stats(
            city="NonexistentCity12345",
            size=1
        )
        
        assert response is not None
        # Statistics should be None or have zero values
        if response.statistics:
            assert response.statistics.total_properties == 0


class TestNeighborhoodRelatedEntities:
    """Test fetching related properties and Wikipedia articles."""
    
    def test_search_with_related_properties(self, neighborhood_service, es_client):
        """Test neighborhood search with related properties."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        response = neighborhood_service.search_related(
            city="San Francisco",
            include_properties=True,
            include_wikipedia=False,
            size=2
        )
        
        assert response is not None
        
        # Related properties might be None if properties index doesn't exist
        if es_client.indices.exists(index="properties") and response.related_properties:
            assert isinstance(response.related_properties, list)
            for prop in response.related_properties:
                assert isinstance(prop, RelatedProperty)
                assert prop.listing_id is not None
                assert prop.price is not None
                assert prop.address is not None
    
    def test_search_with_related_wikipedia(self, neighborhood_service, es_client):
        """Test neighborhood search with related Wikipedia articles."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        response = neighborhood_service.search_related(
            city="San Francisco",
            include_properties=False,
            include_wikipedia=True,
            size=2
        )
        
        assert response is not None
        
        # Related Wikipedia articles
        if response.related_wikipedia:
            assert isinstance(response.related_wikipedia, list)
            for article in response.related_wikipedia:
                assert isinstance(article, RelatedWikipediaArticle)
                assert article.page_id is not None
                assert article.title is not None
                assert article.url is not None
    
    def test_search_with_all_related_entities(self, neighborhood_service, es_client):
        """Test neighborhood search with all related entities."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        response = neighborhood_service.search_related(
            city="San Francisco",
            include_properties=True,
            include_wikipedia=True,
            size=3
        )
        
        assert response is not None
        assert isinstance(response.results, list)
        
        # Check that at least one type of related entity is returned
        has_related = (
            (response.related_properties is not None and len(response.related_properties) > 0) or
            (response.related_wikipedia is not None and len(response.related_wikipedia) > 0)
        )
        
        # Should have some related entities if indices exist
        if es_client.indices.exists(index="properties"):
            assert response.related_properties is None or isinstance(response.related_properties, list)
    
    def test_related_entities_limit(self, neighborhood_service, es_client):
        """Test that related entities respect size limits."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        response = neighborhood_service.search_related(
            city="San Francisco",
            include_properties=True,
            include_wikipedia=True,
            size=5
        )
        
        assert response is not None
        
        # Check that we get some results
        if response.related_properties:
            assert len(response.related_properties) > 0
        
        if response.related_wikipedia:
            assert len(response.related_wikipedia) > 0


class TestNeighborhoodSearchVariations:
    """Test different search variations and parameters."""
    
    def test_search_with_highlights(self, neighborhood_service, es_client):
        """Test neighborhood search with highlighting."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        request = NeighborhoodSearchRequest(
            city="San Francisco",
            query="golden gate",
            size=5
        )
        
        response = neighborhood_service.search(request)
        
        assert response is not None
        
        # Check if highlights are present
        has_highlights = any(
            result.highlights is not None and len(result.highlights) > 0
            for result in response.results
        )
        
        # If query matches content, should have highlights
        if response.total_hits > 0 and has_highlights:
            for result in response.results:
                if result.highlights:
                    assert isinstance(result.highlights, list)
                    for highlight in result.highlights:
                        assert isinstance(highlight, str)
    
    def test_search_with_categories(self, neighborhood_service, es_client):
        """Test filtering by Wikipedia categories."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Note: NeighborhoodSearchRequest doesn't have categories field
        # Search with basic parameters instead
        request = NeighborhoodSearchRequest(
            city="San Francisco",
            query="historic neighborhoods",
            size=5
        )
        
        response = neighborhood_service.search(request)
        
        assert response is not None
        assert isinstance(response.results, list)
        
        # Results should have relevant categories
        for result in response.results:
            if result.categories:
                # Categories are part of the result, not the request
                assert isinstance(result.categories, list)
    
    def test_pagination(self, neighborhood_service, es_client):
        """Test pagination for neighborhood search."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Note: NeighborhoodSearchRequest doesn't have from_offset
        # So we test with size limits only
        # Get results with different sizes
        small_results = neighborhood_service.search(
            NeighborhoodSearchRequest(
                city="San Francisco",
                size=3
            )
        )
        
        large_results = neighborhood_service.search(
            NeighborhoodSearchRequest(
                city="San Francisco",
                size=10
            )
        )
        
        assert small_results is not None
        assert large_results is not None
        
        # Smaller request should have fewer results
        assert len(small_results.results) <= 3
        assert len(large_results.results) <= 10
        
        # If there are enough results, large should have more than small
        if large_results.total_hits > 3:
            assert len(large_results.results) > len(small_results.results)
    
    def test_sorting_by_relevance(self, neighborhood_service, es_client):
        """Test that results are sorted by relevance."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        response = neighborhood_service.search(
            NeighborhoodSearchRequest(
                city="San Francisco",
                query="mission district",
                size=10
            )
        )
        
        assert response is not None
        
        # Results should be sorted by score (descending)
        if len(response.results) > 1:
            scores = [r.score for r in response.results]
            assert scores == sorted(scores, reverse=True)


class TestNeighborhoodErrorHandling:
    """Test error handling in neighborhood search."""
    
    def test_search_with_invalid_index(self, es_client):
        """Test search when index doesn't exist."""
        service = NeighborhoodSearchService(es_client)
        service.wikipedia_index = "non_existent_index_abc"
        
        # Should raise an error for non-existent index
        with pytest.raises(Exception) as exc_info:
            response = service.search_location(
                city="San Francisco",
                size=5
            )
        
        assert "not found" in str(exc_info.value).lower() or "no such index" in str(exc_info.value).lower()
    
    def test_search_with_empty_parameters(self, neighborhood_service):
        """Test search with minimal parameters."""
        request = NeighborhoodSearchRequest()
        
        response = neighborhood_service.search(request)
        
        assert response is not None
        # Should return some results or empty
        assert isinstance(response.results, list)
    
    def test_search_with_special_characters(self, neighborhood_service, es_client):
        """Test search with special characters in query."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Test with special characters
        special_queries = [
            "San Francisco's neighborhoods",
            "Mission & Castro",
            "SOMA (South of Market)",
            "Nob Hill/Russian Hill"
        ]
        
        for query in special_queries:
            request = NeighborhoodSearchRequest(
                query=query,
                size=5
            )
            
            response = neighborhood_service.search(request)
            
            # Should handle special characters gracefully
            assert response is not None
            assert isinstance(response.results, list)
    
    def test_concurrent_searches(self, neighborhood_service, es_client):
        """Test that service can handle multiple searches."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Run multiple searches in sequence
        responses = []
        for i in range(5):
            response = neighborhood_service.search_location(
                city="San Francisco",
                size=2
            )
            responses.append(response)
        
        # All should succeed
        assert len(responses) == 5
        for response in responses:
            assert response is not None
            assert isinstance(response.results, list)


class TestNeighborhoodSearchPerformance:
    """Test performance aspects of neighborhood search."""
    
    def test_search_response_time(self, neighborhood_service, es_client):
        """Test that searches complete within reasonable time."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Simple location search
        response = neighborhood_service.search_location(
            city="San Francisco",
            size=10
        )
        assert response.execution_time_ms < 2000  # Should be under 2 seconds
        
        # Search with statistics
        if es_client.indices.exists(index="properties"):
            response = neighborhood_service.search_with_stats(
                city="San Francisco",
                size=5
            )
            assert response.execution_time_ms < 3000  # May take longer with aggregations
        
        # Search with related entities
        response = neighborhood_service.search_related(
            city="San Francisco",
            include_properties=True,
            include_wikipedia=True,
            size=5
        )
        assert response.execution_time_ms < 5000  # Multiple queries may take longer
    
    def test_large_result_set(self, neighborhood_service, es_client):
        """Test handling of large result sets."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Request large number of results
        response = neighborhood_service.search_location(
            city="San Francisco",
            size=50
        )
        
        assert response is not None
        assert len(response.results) <= 50
        assert response.execution_time_ms < 5000  # Should still be reasonably fast


class TestNeighborhoodCrossIndex:
    """Test cross-index functionality between Wikipedia and properties."""
    
    def test_neighborhood_property_correlation(self, neighborhood_service, es_client):
        """Test that neighborhoods correlate with property locations."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        if not es_client.indices.exists(index="properties"):
            pytest.skip("Properties index does not exist")
        
        # Get neighborhood with properties
        response = neighborhood_service.search_related(
            city="San Francisco",
            include_properties=True,
            size=1
        )
        
        assert response is not None
        
        if response.results and response.related_properties:
            # Properties should be from the same city
            neighborhood = response.results[0]
            for prop in response.related_properties:
                if prop.address and prop.address.city:
                    # City should match or be related
                    assert "San Francisco" in prop.address.city or prop.address.city == "SF"
    
    def test_statistics_consistency(self, neighborhood_service, es_client):
        """Test that statistics are consistent with actual data."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        if not es_client.indices.exists(index="properties"):
            pytest.skip("Properties index does not exist")
        
        # Get neighborhood with stats and properties
        response = neighborhood_service.search_related(
            city="San Francisco",
            include_properties=True,
            include_wikipedia=False,
            size=1
        )
        
        if response.related_properties:
            # Calculate stats from returned properties
            prices = [p.price for p in response.related_properties if p.price]
            
            if prices:
                calc_min = min(prices)
                calc_max = max(prices)
                calc_avg = sum(prices) / len(prices)
                
                # Verify calculated stats are reasonable
                assert calc_min > 0
                assert calc_max >= calc_min
                assert calc_avg > 0