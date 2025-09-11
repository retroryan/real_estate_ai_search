"""
Integration tests for property search demos.

Tests the refactored property module to ensure all demo functions
work correctly with the new modular structure.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from elasticsearch import Elasticsearch

from real_estate_search.demo_queries.property import (
    demo_basic_property_search,
    demo_filtered_property_search,
    demo_geo_distance_search,
    demo_price_range_search,
    PropertyQueryBuilder,
    PropertySearchExecutor,
    PropertyDisplayService,
    PropertyDemoRunner
)
from real_estate_search.models.results import PropertySearchResult, AggregationSearchResult


@pytest.fixture
def mock_es_client():
    """Create a mock Elasticsearch client."""
    mock = Mock(spec=Elasticsearch)
    
    # Mock search response for basic search
    mock.search.return_value = {
        "hits": {
            "total": {"value": 5, "relation": "eq"},
            "max_score": 8.5,
            "hits": [
                {
                    "_index": "properties",
                    "_id": "1",
                    "_score": 8.5,
                    "_source": {
                        "listing_id": "prop-001",
                        "property_type": "single-family",
                        "price": 850000,
                        "bedrooms": 4,
                        "bathrooms": 3.5,
                        "square_feet": 3200,
                        "year_built": 2015,
                        "address": {
                            "street": "123 Modern Lane",
                            "city": "San Francisco",
                            "state": "CA",
                            "zip": "94110"
                        },
                        "description": "Modern home with pool and stunning views",
                        "features": ["pool", "garage", "garden"]
                    }
                },
                {
                    "_index": "properties",
                    "_id": "2",
                    "_score": 7.2,
                    "_source": {
                        "listing_id": "prop-002",
                        "property_type": "condo",
                        "price": 650000,
                        "bedrooms": 2,
                        "bathrooms": 2,
                        "square_feet": 1400,
                        "year_built": 2018,
                        "address": {
                            "street": "456 Urban Ave",
                            "city": "San Francisco",
                            "state": "CA",
                            "zip": "94103"
                        },
                        "description": "Modern condo with pool access",
                        "features": ["pool", "gym", "concierge"]
                    }
                }
            ]
        },
        "aggregations": {
            "price_stats": {
                "count": 5,
                "min": 400000,
                "max": 850000,
                "avg": 625000,
                "sum": 3125000
            },
            "property_types": {
                "buckets": [
                    {"key": "single-family", "doc_count": 3},
                    {"key": "condo", "doc_count": 2}
                ]
            },
            "price_histogram": {
                "buckets": [
                    {"key": 400000, "doc_count": 1},
                    {"key": 500000, "doc_count": 1},
                    {"key": 600000, "doc_count": 1},
                    {"key": 700000, "doc_count": 1},
                    {"key": 800000, "doc_count": 1}
                ]
            },
            "bedroom_stats": {
                "count": 5,
                "min": 2,
                "max": 4,
                "avg": 3,
                "sum": 15
            }
        }
    }
    
    return mock


class TestPropertyQueryBuilder:
    """Test the PropertyQueryBuilder class."""
    
    def test_basic_search_query(self):
        """Test basic search query construction."""
        request = PropertyQueryBuilder.basic_search("modern home with pool")
        
        assert request.index == ["properties"]
        assert "multi_match" in request.query
        assert request.query["multi_match"]["query"] == "modern home with pool"
        assert "description^2" in request.query["multi_match"]["fields"]
        assert request.size == 10
        assert request.highlight is not None
    
    def test_filtered_search_query(self):
        """Test filtered search query construction."""
        request = PropertyQueryBuilder.filtered_search(
            property_type="single-family",
            min_price=300000,
            max_price=800000,
            min_bedrooms=3,
            min_bathrooms=2
        )
        
        assert request.index == ["properties"]
        assert "bool" in request.query
        assert "filter" in request.query["bool"]
        filters = request.query["bool"]["filter"]
        
        # Check that all filters are present
        filter_types = [list(f.keys())[0] for f in filters]
        assert "term" in filter_types  # property type
        assert "range" in filter_types  # price range
    
    def test_geo_search_query(self):
        """Test geo-distance search query construction."""
        request = PropertyQueryBuilder.geo_search(
            center_lat=37.7749,
            center_lon=-122.4194,
            radius_km=5.0,
            max_price=1000000
        )
        
        assert request.index == ["properties"]
        assert "bool" in request.query
        assert "filter" in request.query["bool"]
        
        # Check for geo_distance filter
        filters = request.query["bool"]["filter"]
        geo_filters = [f for f in filters if "geo_distance" in f]
        assert len(geo_filters) == 1
        assert geo_filters[0]["geo_distance"]["distance"] == "5.0km"
    
    def test_price_range_with_stats(self):
        """Test price range query with aggregations."""
        request = PropertyQueryBuilder.price_range_with_stats(
            min_price=400000,
            max_price=800000,
            include_stats=True
        )
        
        assert request.index == ["properties"]
        assert "range" in request.query
        assert request.query["range"]["price"]["gte"] == 400000
        assert request.query["range"]["price"]["lte"] == 800000
        
        # Check aggregations
        assert request.aggs is not None
        assert "price_stats" in request.aggs
        assert "price_histogram" in request.aggs
        assert "property_types" in request.aggs
        assert "bedroom_stats" in request.aggs


class TestPropertySearchExecutor:
    """Test the PropertySearchExecutor class."""
    
    def test_executor_initialization(self, mock_es_client):
        """Test executor can be initialized with ES client."""
        executor = PropertySearchExecutor(es_client=mock_es_client)
        assert executor.es_client == mock_es_client
    
    def test_execute_search(self, mock_es_client):
        """Test search execution."""
        executor = PropertySearchExecutor(es_client=mock_es_client)
        request = PropertyQueryBuilder.basic_search("test query")
        
        response, exec_time = executor.execute(request)
        
        assert response is not None
        assert exec_time >= 0  # Changed from > 0 to >= 0 as mock execution may be instant
        assert response.total_hits == 5
        assert len(response.hits) == 2
    
    def test_process_results(self, mock_es_client):
        """Test result processing."""
        executor = PropertySearchExecutor(es_client=mock_es_client)
        request = PropertyQueryBuilder.basic_search("test query")
        response, _ = executor.execute(request)
        
        results = executor.process_results(response)
        
        assert len(results) == 2
        assert results[0].listing_id == "prop-001"
        assert results[0].property_type == "single-family"
        assert results[0].price == 850000
        assert results[1].listing_id == "prop-002"


class TestPropertyDemoRunner:
    """Test the PropertyDemoRunner class."""
    
    @patch('real_estate_search.demo_queries.property.display_service.Console')
    def test_demo_runner_initialization(self, mock_console, mock_es_client):
        """Test demo runner initialization."""
        runner = PropertyDemoRunner(es_client=mock_es_client)
        
        assert runner.es_client == mock_es_client
        assert runner.executor is not None
        assert runner.display_service is not None
    
    @patch('real_estate_search.demo_queries.property.display_service.Console')
    def test_run_basic_search(self, mock_console, mock_es_client):
        """Test running basic search demo."""
        runner = PropertyDemoRunner(es_client=mock_es_client)
        result = runner.run_basic_search("modern home with pool")
        
        assert isinstance(result, PropertySearchResult)
        assert result.total_hits == 5
        assert len(result.results) == 2
        assert result.query_name == "Basic Property Search: 'modern home with pool'"
    
    @patch('real_estate_search.demo_queries.property.display_service.Console')
    def test_run_filtered_search(self, mock_console, mock_es_client):
        """Test running filtered search demo."""
        runner = PropertyDemoRunner(es_client=mock_es_client)
        result = runner.run_filtered_search(
            property_type="single-family",
            min_price=300000,
            max_price=800000
        )
        
        assert isinstance(result, PropertySearchResult)
        assert result.query_name == "Filtered Property Search"
    
    @patch('real_estate_search.demo_queries.property.display_service.Console')
    def test_run_price_range_search(self, mock_console, mock_es_client):
        """Test running price range search with aggregations."""
        runner = PropertyDemoRunner(es_client=mock_es_client)
        result = runner.run_price_range_search(
            min_price=400000,
            max_price=800000
        )
        
        assert isinstance(result, AggregationSearchResult)
        assert result.aggregations is not None
        assert "price_stats" in result.aggregations


class TestDemoFunctions:
    """Test the public demo functions."""
    
    @patch('real_estate_search.demo_queries.property.display_service.Console')
    def test_demo_basic_property_search(self, mock_console, mock_es_client):
        """Test demo_basic_property_search function."""
        result = demo_basic_property_search(
            mock_es_client,
            "family home with pool"
        )
        
        assert isinstance(result, PropertySearchResult)
        assert result.total_hits == 5
        mock_es_client.search.assert_called_once()
    
    @patch('real_estate_search.demo_queries.property.display_service.Console')
    def test_demo_filtered_property_search(self, mock_console, mock_es_client):
        """Test demo_filtered_property_search function."""
        result = demo_filtered_property_search(
            mock_es_client,
            property_type="single-family",
            min_price=300000,
            max_price=800000
        )
        
        assert isinstance(result, PropertySearchResult)
        mock_es_client.search.assert_called_once()
    
    @patch('real_estate_search.demo_queries.property.display_service.Console')
    def test_demo_geo_distance_search(self, mock_console, mock_es_client):
        """Test demo_geo_distance_search function."""
        result = demo_geo_distance_search(
            mock_es_client,
            center_lat=37.7749,
            center_lon=-122.4194,
            radius_km=5.0
        )
        
        assert isinstance(result, PropertySearchResult)
        mock_es_client.search.assert_called_once()
    
    @patch('real_estate_search.demo_queries.property.display_service.Console')
    def test_demo_price_range_search(self, mock_console, mock_es_client):
        """Test demo_price_range_search function."""
        result = demo_price_range_search(
            mock_es_client,
            min_price=400000,
            max_price=800000
        )
        
        assert isinstance(result, AggregationSearchResult)
        assert result.aggregations is not None
        mock_es_client.search.assert_called_once()


class TestModuleSeparation:
    """Test that modules are properly separated."""
    
    def test_query_builder_no_es_dependency(self):
        """Test QueryBuilder has no Elasticsearch dependency."""
        # Should be able to use QueryBuilder without ES client
        request = PropertyQueryBuilder.basic_search("test")
        assert request is not None
    
    def test_display_service_independence(self):
        """Test DisplayService is independent of query logic."""
        display = PropertyDisplayService()
        # Should be able to create display service without other dependencies
        assert display is not None
        assert display.console is not None
    
    @patch('real_estate_search.demo_queries.property.display_service.Console')
    def test_clean_separation_of_concerns(self, mock_console, mock_es_client):
        """Test that each module has single responsibility."""
        # Query builder only builds queries
        query = PropertyQueryBuilder.basic_search("test")
        assert "multi_match" in query.query
        
        # Executor only executes and processes
        executor = PropertySearchExecutor(es_client=mock_es_client)
        response, _ = executor.execute(query)
        assert response is not None
        
        # Display service only displays
        display = PropertyDisplayService()
        assert display.console is not None