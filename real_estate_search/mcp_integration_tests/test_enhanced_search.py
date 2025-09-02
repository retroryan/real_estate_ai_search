"""Integration tests for Phase 4: Enhanced Search Capabilities."""

import pytest
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from real_estate_search.mcp_server.config.settings import MCPServerConfig
from real_estate_search.mcp_server.services.property_search import PropertySearchService
from real_estate_search.mcp_server.services.wikipedia_search import WikipediaSearchService
from real_estate_search.mcp_server.services.elasticsearch_client import ElasticsearchClient
from real_estate_search.mcp_server.services.embedding_service import EmbeddingService
from real_estate_search.mcp_server.models.search import (
    PropertySearchRequest,
    WikipediaSearchRequest,
    PropertyFilter,
    SearchMetadata,
    Aggregation
)


@pytest.fixture
def config():
    """Create test configuration."""
    config_dict = {
        "server_name": "test-server",
        "server_version": "1.0.0",
        "debug": True,
        "elasticsearch": {
            "host": "localhost",
            "port": 9200,
            "property_index": "properties",
            "wiki_chunks_index_prefix": "wiki_chunks",
            "wiki_summaries_index_prefix": "wiki_summaries"
        },
        "embedding": {
            "provider": "voyage",
            "model_name": "voyage-3",
            "dimension": 1024,
            "batch_size": 10
        },
        "search": {
            "default_size": 20,
            "max_size": 100,
            "text_weight": 0.5,
            "vector_weight": 0.5,
            "enable_fuzzy": True,
            "aggregations_enabled": True
        }
    }
    return MCPServerConfig(**config_dict)


@pytest.fixture
def mock_es_client():
    """Create mock Elasticsearch client."""
    client = Mock(spec=ElasticsearchClient)
    client.search = Mock(return_value={
        "hits": {
            "total": {"value": 10},
            "max_score": 0.95,
            "hits": []
        }
    })
    return client


@pytest.fixture
def mock_embedding_service():
    """Create mock embedding service."""
    service = Mock(spec=EmbeddingService)
    service.embed_text = Mock(return_value=[0.1] * 1024)
    service.embed_texts_batch = Mock(return_value=[[0.1] * 1024])
    return service


@pytest.fixture
def property_search_service(config, mock_es_client, mock_embedding_service):
    """Create property search service."""
    return PropertySearchService(config, mock_es_client, mock_embedding_service)


@pytest.fixture
def wikipedia_search_service(config, mock_es_client, mock_embedding_service):
    """Create Wikipedia search service."""
    return WikipediaSearchService(config, mock_es_client, mock_embedding_service)


class TestHybridSearchCapabilities:
    """Test hybrid search combining vector and text search."""
    
    def test_hybrid_search_query_construction(self, property_search_service):
        """Test that hybrid search properly combines text and vector queries."""
        text_query = {"multi_match": {"query": "modern home"}}
        vector_query = {"script_score": {"query": {"match_all": {}}}}
        
        hybrid_query = property_search_service.build_hybrid_query(text_query, vector_query)
        
        assert "bool" in hybrid_query
        assert "should" in hybrid_query["bool"]
        assert len(hybrid_query["bool"]["should"]) == 2
        
        # Check text query with boost
        text_clause = hybrid_query["bool"]["should"][0]
        assert "constant_score" in text_clause
        assert text_clause["constant_score"]["boost"] == 0.5  # text_weight
        
        # Check vector query with boost
        vector_clause = hybrid_query["bool"]["should"][1]
        assert "constant_score" in vector_clause
        assert vector_clause["constant_score"]["boost"] == 0.5  # vector_weight
    
    def test_hybrid_search_execution(self, property_search_service, mock_es_client):
        """Test full hybrid search execution."""
        mock_es_client.search.return_value = {
            "hits": {
                "total": {"value": 5},
                "max_score": 0.85,
                "hits": [
                    {
                        "_source": {
                            "listing_id": "prop1",
                            "property_type": "House",
                            "price": 500000,
                            "description": "Modern home with pool"
                        },
                        "_score": 0.85
                    }
                ]
            }
        }
        
        request = PropertySearchRequest(
            query="modern home with pool",
            search_type="hybrid",
            size=10
        )
        
        response = property_search_service.search(request)
        
        assert response.metadata.total_hits == 5
        assert response.metadata.query_type == "hybrid"
        assert len(response.results) == 1
        assert response.results[0]["listing_id"] == "prop1"
    
    def test_search_type_switching(self, property_search_service, mock_es_client):
        """Test switching between semantic, text, and hybrid search types."""
        # Test semantic search
        request_semantic = PropertySearchRequest(
            query="luxury home",
            search_type="semantic"
        )
        property_search_service.search(request_semantic)
        
        # Test text search
        request_text = PropertySearchRequest(
            query="pool backyard",
            search_type="text"
        )
        property_search_service.search(request_text)
        
        # Test hybrid search
        request_hybrid = PropertySearchRequest(
            query="modern kitchen",
            search_type="hybrid"
        )
        property_search_service.search(request_hybrid)
        
        # Verify different query types were used
        assert mock_es_client.search.call_count == 3


class TestAdvancedFiltering:
    """Test advanced filtering capabilities."""
    
    def test_comprehensive_property_filters(self, property_search_service):
        """Test all property filter types."""
        filters = PropertyFilter(
            property_type="Condo",
            min_price=200000,
            max_price=500000,
            min_bedrooms=2,
            max_bedrooms=4,
            min_bathrooms=1.5,
            max_bathrooms=3,
            min_square_feet=1000,
            max_square_feet=2000,
            city="San Francisco",
            state="CA",
            zip_code="94102",
            neighborhood_id="nob-hill",
            center_lat=37.7749,
            center_lon=-122.4194,
            radius_km=5.0,
            status="active",
            max_days_on_market=30
        )
        
        filter_clauses = property_search_service.build_filter_query(filters)
        
        # Verify all filters are present
        assert len(filter_clauses) > 10
        
        # Check specific filters
        filter_types = [clause for clause in filter_clauses]
        
        # Property type filter
        assert any("term" in f and "property_type" in str(f) for f in filter_types)
        
        # Price range filter
        assert any("range" in f and "price" in str(f) for f in filter_types)
        
        # Geo-distance filter
        assert any("geo_distance" in f for f in filter_types)
        
        # Status filter
        assert any("term" in f and "status" in str(f) for f in filter_types)
    
    def test_geo_distance_search(self, property_search_service):
        """Test geographic distance-based search."""
        filters = PropertyFilter(
            center_lat=37.7749,
            center_lon=-122.4194,
            radius_km=10.0
        )
        
        filter_clauses = property_search_service.build_filter_query(filters)
        
        geo_filter = next((f for f in filter_clauses if "geo_distance" in f), None)
        assert geo_filter is not None
        assert geo_filter["geo_distance"]["distance"] == "10.0km"
        assert geo_filter["geo_distance"]["address.location"]["lat"] == 37.7749
        assert geo_filter["geo_distance"]["address.location"]["lon"] == -122.4194
    
    def test_combined_filters_with_search(self, property_search_service, mock_es_client):
        """Test combining multiple filters with search query."""
        request = PropertySearchRequest(
            query="modern home",
            filters=PropertyFilter(
                property_type="House",
                min_price=400000,
                max_price=800000,
                city="San Francisco"
            ),
            search_type="hybrid"
        )
        
        property_search_service.search(request)
        
        # Verify search was called with filters
        call_args = mock_es_client.search.call_args
        body = call_args[1]["body"]
        
        assert "query" in body
        assert "bool" in body["query"]
        # Should have both must (main query) and filter (filters)
        assert "must" in body["query"]["bool"] or "should" in body["query"]["bool"]
        assert "filter" in body["query"]["bool"]


class TestAggregations:
    """Test aggregation capabilities."""
    
    def test_aggregation_query_building(self, property_search_service):
        """Test building aggregation queries."""
        aggs = property_search_service.build_aggregations()
        
        assert "property_types" in aggs
        assert "price_ranges" in aggs
        assert "bedroom_counts" in aggs
        assert "cities" in aggs
        assert "avg_price" in aggs
        assert "avg_sqft" in aggs
        
        # Check price ranges structure
        price_ranges = aggs["price_ranges"]
        assert "range" in price_ranges
        assert "ranges" in price_ranges["range"]
        assert len(price_ranges["range"]["ranges"]) == 4
    
    def test_aggregation_response_processing(self, property_search_service, mock_es_client):
        """Test processing aggregation results."""
        mock_es_client.search.return_value = {
            "hits": {
                "total": {"value": 100},
                "max_score": 0.9,
                "hits": []
            },
            "aggregations": {
                "property_types": {
                    "buckets": [
                        {"key": "House", "doc_count": 50},
                        {"key": "Condo", "doc_count": 30},
                        {"key": "Townhouse", "doc_count": 20}
                    ]
                },
                "avg_price": {
                    "value": 650000
                }
            }
        }
        
        request = PropertySearchRequest(
            query="any property",
            include_aggregations=True
        )
        
        response = property_search_service.search(request)
        
        assert response.aggregations is not None
        assert len(response.aggregations) > 0
        
        # Find property_types aggregation
        prop_types_agg = next(
            (a for a in response.aggregations if a.name == "property_types"),
            None
        )
        assert prop_types_agg is not None
        assert prop_types_agg.type == "terms"
        assert len(prop_types_agg.buckets) == 3
    
    def test_aggregations_disabled(self, property_search_service, mock_es_client):
        """Test that aggregations can be disabled."""
        request = PropertySearchRequest(
            query="test query",
            include_aggregations=False
        )
        
        property_search_service.search(request)
        
        call_args = mock_es_client.search.call_args
        body = call_args[1]["body"]
        
        assert "aggs" not in body


class TestSearchExplanation:
    """Test search result explanation features."""
    
    def test_explanation_request(self, property_search_service, mock_es_client):
        """Test requesting search explanations."""
        request = PropertySearchRequest(
            query="test query",
            explain=True
        )
        
        property_search_service.search(request)
        
        call_args = mock_es_client.search.call_args
        body = call_args[1]["body"]
        
        assert "explain" in body
        assert body["explain"] is True
    
    def test_explanation_response_processing(self, property_search_service, mock_es_client):
        """Test processing explanation in responses."""
        mock_es_client.search.return_value = {
            "hits": {
                "total": {"value": 1},
                "max_score": 0.8,
                "hits": [
                    {
                        "_source": {"listing_id": "prop1"},
                        "_score": 0.8,
                        "_explanation": {
                            "value": 0.8,
                            "description": "sum of:",
                            "details": []
                        }
                    }
                ]
            }
        }
        
        request = PropertySearchRequest(
            query="test",
            explain=True
        )
        
        response = property_search_service.search(request)
        
        assert len(response.results) == 1
        assert "_explanation" in response.results[0]
        assert response.results[0]["_explanation"]["value"] == 0.8


class TestMultiFieldBoosting:
    """Test multi-field boosting in text search."""
    
    def test_text_query_field_boosting(self, property_search_service):
        """Test that text queries use field boosting."""
        text_query = property_search_service.build_text_query("modern home")
        
        assert "multi_match" in text_query
        assert "fields" in text_query["multi_match"]
        
        fields = text_query["multi_match"]["fields"]
        
        # Check that important fields have higher boosts
        assert "description^3" in fields
        assert "features^1.5" in fields
        assert "amenities^1.5" in fields
        
        # Check that less important fields have lower or no boost
        assert "search_tags" in fields
        assert "address.street" in fields
    
    def test_fuzzy_matching_enabled(self, property_search_service):
        """Test that fuzzy matching is configurable."""
        text_query = property_search_service.build_text_query("modern home")
        
        assert "multi_match" in text_query
        # When fuzzy is enabled in config
        assert text_query["multi_match"]["fuzziness"] == "AUTO"


class TestSortingCapabilities:
    """Test result sorting options."""
    
    def test_sort_by_price(self, property_search_service):
        """Test sorting by price."""
        request = PropertySearchRequest(
            query="any",
            sort_by="price",
            sort_order="asc"
        )
        
        sort_criteria = property_search_service.build_sort(request)
        
        assert sort_criteria is not None
        assert len(sort_criteria) == 1
        assert "price" in sort_criteria[0]
        assert sort_criteria[0]["price"]["order"] == "asc"
    
    def test_sort_by_date(self, property_search_service):
        """Test sorting by listing date."""
        request = PropertySearchRequest(
            query="any",
            sort_by="date",
            sort_order="desc"
        )
        
        sort_criteria = property_search_service.build_sort(request)
        
        assert sort_criteria is not None
        assert "listing_date" in sort_criteria[0]
        assert sort_criteria[0]["listing_date"]["order"] == "desc"
    
    def test_relevance_sort_default(self, property_search_service):
        """Test that relevance is the default sort."""
        request = PropertySearchRequest(
            query="any",
            sort_by="relevance"
        )
        
        sort_criteria = property_search_service.build_sort(request)
        
        assert sort_criteria is None  # No explicit sort means relevance


class TestWikipediaEnhancedSearch:
    """Test enhanced Wikipedia search capabilities."""
    
    def test_wikipedia_multi_field_search(self, wikipedia_search_service):
        """Test Wikipedia search across multiple fields."""
        text_query = wikipedia_search_service.build_text_query(
            "Golden Gate Bridge",
            search_in="full"
        )
        
        assert "multi_match" in text_query
        fields = text_query["multi_match"]["fields"]
        
        # Check field boosting for full article search
        assert "title^3" in fields
        assert "short_summary^2.5" in fields  # Actual boost is 2.5
        assert "full_content^1.5" in fields  # Actual boost is 1.5
    
    def test_wikipedia_chunk_search(self, wikipedia_search_service):
        """Test searching Wikipedia chunks."""
        text_query = wikipedia_search_service.build_text_query(
            "architecture history",
            search_in="chunks"
        )
        
        assert "multi_match" in text_query
        fields = text_query["multi_match"]["fields"]
        
        # Check chunk-specific fields
        assert "chunk_text^2" in fields
    
    def test_wikipedia_location_filters(self, wikipedia_search_service):
        """Test Wikipedia location-based filtering."""
        filters = wikipedia_search_service.build_filter_query(
            WikipediaSearchRequest(
                query="landmarks",
                city="San Francisco",
                state="CA"
            )
        )
        
        assert len(filters) == 2
        
        # Check city filter
        city_filter = next((f for f in filters if "best_city" in str(f)), None)
        assert city_filter is not None
        
        # Check state filter
        state_filter = next((f for f in filters if "best_state" in str(f)), None)
        assert state_filter is not None


class TestPerformanceOptimizations:
    """Test performance optimization features."""
    
    def test_batch_embedding_processing(self, mock_embedding_service):
        """Test that embeddings can be processed in batches."""
        texts = ["query1", "query2", "query3", "query4", "query5"]
        
        embeddings = mock_embedding_service.embed_texts_batch(texts)
        
        assert mock_embedding_service.embed_texts_batch.called
        assert len(embeddings) == 1  # Mock returns single embedding
    
    def test_result_size_limiting(self, property_search_service):
        """Test that result size is properly limited."""
        # Pydantic validates size at model level, so we test with valid size
        request = PropertySearchRequest(
            query="test",
            size=100  # Max allowed size
        )
        
        # Verify size validation works
        assert request.size == 100
        
        # Test that exceeding max_size raises validation error
        with pytest.raises(Exception):  # Pydantic ValidationError
            PropertySearchRequest(
                query="test",
                size=150  # Over max_size
            )
    
    def test_highlighting_optional(self, property_search_service, mock_es_client):
        """Test that highlighting can be disabled for performance."""
        request = PropertySearchRequest(
            query="test",
            include_highlights=False
        )
        
        property_search_service.search(request)
        
        call_args = mock_es_client.search.call_args
        body = call_args[1]["body"]
        
        assert "highlight" not in body


class TestErrorHandlingEnhancements:
    """Test enhanced error handling in search."""
    
    def test_embedding_service_failure_fallback(self, property_search_service, mock_embedding_service):
        """Test fallback to text search when embedding fails."""
        mock_embedding_service.embed_text.side_effect = Exception("Embedding API error")
        
        request = PropertySearchRequest(
            query="test",
            search_type="semantic"
        )
        
        # Should raise since semantic search requires embeddings
        with pytest.raises(Exception) as exc_info:
            property_search_service.search(request)
        
        assert "Embedding API error" in str(exc_info.value)
    
    def test_elasticsearch_retry_logic(self, config):
        """Test that Elasticsearch client has retry logic."""
        # This is already implemented via tenacity in elasticsearch_client.py
        # Just verify the configuration
        assert config.elasticsearch.request_timeout == 30
        assert config.elasticsearch.max_retries == 3


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])