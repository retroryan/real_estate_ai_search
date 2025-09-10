"""
Integration tests for aggregation demo queries.

Tests the refactored aggregation module to ensure all functionality
works correctly with Elasticsearch.
"""

import pytest
from unittest.mock import Mock, MagicMock
from elasticsearch import Elasticsearch

from real_estate_search.demo_queries.aggregation import (
    demo_neighborhood_stats,
    demo_price_distribution
)
from real_estate_search.demo_queries.aggregation.models import (
    NeighborhoodStats,
    PriceRangeStats,
    PropertyTypeStats,
    GlobalStats,
    PropertyTypeCount
)
from real_estate_search.demo_queries.aggregation.query_builder import AggregationQueryBuilder
from real_estate_search.demo_queries.aggregation.result_processor import AggregationResultProcessor


class TestAggregationModels:
    """Test Pydantic models for aggregation results."""
    
    def test_neighborhood_stats_model(self):
        """Test NeighborhoodStats model creation and validation."""
        property_types = [
            PropertyTypeCount(type="condo", count=10),
            PropertyTypeCount(type="single-family", count=5)
        ]
        
        stats = NeighborhoodStats(
            neighborhood_id="test-neighborhood",
            property_count=15,
            avg_price=500000.50,
            min_price=200000,
            max_price=800000,
            avg_bedrooms=3.5,
            avg_square_feet=2000,
            price_per_sqft=250.25,
            property_types=property_types
        )
        
        assert stats.neighborhood_id == "test-neighborhood"
        assert stats.property_count == 15
        assert stats.avg_price == 500000.50
        assert len(stats.property_types) == 2
        assert stats.property_types[0].type == "condo"
        assert stats.property_types[0].count == 10
    
    def test_price_range_stats_model(self):
        """Test PriceRangeStats model creation and validation."""
        stats = PriceRangeStats(
            price_range="$100,000 - $200,000",
            range_start=100000,
            range_end=200000,
            count=25,
            property_types={"condo": 15, "single-family": 10},
            avg_price=150000.0
        )
        
        assert stats.price_range == "$100,000 - $200,000"
        assert stats.range_start == 100000
        assert stats.range_end == 200000
        assert stats.count == 25
        assert stats.property_types["condo"] == 15
        assert stats.avg_price == 150000.0
    
    def test_global_stats_model(self):
        """Test GlobalStats model creation and validation."""
        stats = GlobalStats(
            total_properties=100,
            overall_avg_price=500000.0
        )
        
        assert stats.total_properties == 100
        assert stats.overall_avg_price == 500000.0


class TestQueryBuilder:
    """Test query building functionality."""
    
    def test_build_neighborhood_stats_query(self):
        """Test neighborhood statistics query construction."""
        query = AggregationQueryBuilder.build_neighborhood_stats_query(size=10)
        
        # Verify query structure
        assert query["size"] == 0  # No documents returned
        assert "aggs" in query
        assert "by_neighborhood" in query["aggs"]
        assert "total_properties" in query["aggs"]
        assert "overall_avg_price" in query["aggs"]
        
        # Verify neighborhood aggregation
        neighborhood_agg = query["aggs"]["by_neighborhood"]
        assert neighborhood_agg["terms"]["field"] == "neighborhood_id"
        assert neighborhood_agg["terms"]["size"] == 10
        
        # Verify sub-aggregations
        assert "property_count" in neighborhood_agg["aggs"]
        assert "avg_price" in neighborhood_agg["aggs"]
        assert "property_types" in neighborhood_agg["aggs"]
    
    def test_build_price_distribution_query(self):
        """Test price distribution query construction."""
        query = AggregationQueryBuilder.build_price_distribution_query(
            interval=50000,
            min_price=100000,
            max_price=500000
        )
        
        # Verify query structure
        assert query["size"] == 5  # Top 5 properties
        assert "sort" in query
        assert "query" in query
        assert "aggs" in query
        
        # Verify range query
        assert query["query"]["range"]["price"]["gte"] == 100000
        assert query["query"]["range"]["price"]["lte"] == 500000
        
        # Verify histogram aggregation
        assert "price_histogram" in query["aggs"]
        histogram = query["aggs"]["price_histogram"]["histogram"]
        assert histogram["field"] == "price"
        assert histogram["interval"] == 50000
        
        # Verify percentiles aggregation
        assert "price_percentiles" in query["aggs"]
        assert "by_property_type_stats" in query["aggs"]


class TestResultProcessor:
    """Test result processing functionality."""
    
    def test_process_neighborhood_aggregations(self):
        """Test processing of neighborhood aggregation results."""
        # Mock Elasticsearch response
        response = {
            "aggregations": {
                "by_neighborhood": {
                    "buckets": [
                        {
                            "key": "neighborhood-1",
                            "doc_count": 20,
                            "property_count": {"value": 20},
                            "avg_price": {"value": 500000},
                            "min_price": {"value": 200000},
                            "max_price": {"value": 800000},
                            "avg_bedrooms": {"value": 3.5},
                            "avg_square_feet": {"value": 2000},
                            "price_per_sqft": {"value": 250},
                            "property_types": {
                                "buckets": [
                                    {"key": "condo", "doc_count": 10},
                                    {"key": "single-family", "doc_count": 10}
                                ]
                            }
                        }
                    ]
                }
            }
        }
        
        processor = AggregationResultProcessor()
        results = processor.process_neighborhood_aggregations(response)
        
        assert len(results) == 1
        assert isinstance(results[0], NeighborhoodStats)
        assert results[0].neighborhood_id == "neighborhood-1"
        assert results[0].property_count == 20
        assert results[0].avg_price == 500000
        assert len(results[0].property_types) == 2
    
    def test_process_price_distribution(self):
        """Test processing of price distribution results."""
        # Mock Elasticsearch response
        response = {
            "aggregations": {
                "price_histogram": {
                    "buckets": [
                        {
                            "key": 100000,
                            "doc_count": 15,
                            "by_property_type": {
                                "buckets": [
                                    {"key": "condo", "doc_count": 10},
                                    {"key": "single-family", "doc_count": 5}
                                ]
                            },
                            "stats": {"avg": 125000}
                        },
                        {
                            "key": 200000,
                            "doc_count": 20,
                            "by_property_type": {
                                "buckets": [
                                    {"key": "condo", "doc_count": 12},
                                    {"key": "single-family", "doc_count": 8}
                                ]
                            },
                            "stats": {"avg": 225000}
                        }
                    ]
                }
            }
        }
        
        processor = AggregationResultProcessor()
        results = processor.process_price_distribution(response, interval=100000)
        
        assert len(results) == 2
        assert isinstance(results[0], PriceRangeStats)
        assert results[0].range_start == 100000
        assert results[0].range_end == 200000
        assert results[0].count == 15
        assert results[0].property_types["condo"] == 10
        assert results[0].avg_price == 125000
    
    def test_extract_global_stats(self):
        """Test extraction of global statistics."""
        response = {
            "aggregations": {
                "total_properties": {"value": 500},
                "overall_avg_price": {"value": 450000.50}
            }
        }
        
        processor = AggregationResultProcessor()
        stats = processor.extract_global_stats(response)
        
        assert isinstance(stats, GlobalStats)
        assert stats.total_properties == 500
        assert stats.overall_avg_price == 450000.50


class TestDemoFunctions:
    """Test the main demo functions."""
    
    @pytest.fixture
    def mock_es_client(self):
        """Create a mock Elasticsearch client."""
        client = Mock(spec=Elasticsearch)
        return client
    
    def test_demo_neighborhood_stats(self, mock_es_client):
        """Test demo_neighborhood_stats function."""
        # Mock Elasticsearch response
        mock_response = {
            "took": 10,
            "hits": {"total": {"value": 100}},
            "aggregations": {
                "by_neighborhood": {
                    "buckets": [
                        {
                            "key": "test-neighborhood",
                            "doc_count": 20,
                            "property_count": {"value": 20},
                            "avg_price": {"value": 500000},
                            "min_price": {"value": 200000},
                            "max_price": {"value": 800000},
                            "avg_bedrooms": {"value": 3.5},
                            "avg_square_feet": {"value": 2000},
                            "price_per_sqft": {"value": 250},
                            "property_types": {
                                "buckets": []
                            }
                        }
                    ]
                },
                "total_properties": {"value": 100},
                "overall_avg_price": {"value": 450000}
            }
        }
        
        mock_es_client.search.return_value = mock_response
        
        # Execute demo function
        result = demo_neighborhood_stats(mock_es_client, size=10)
        
        # Verify result
        assert result.query_name == "Demo 4: Neighborhood Statistics Aggregation"
        assert result.execution_time_ms == 10
        assert result.total_hits == 100
        assert result.returned_hits == 0
        assert "by_neighborhood" in result.aggregations
        
        # Verify Elasticsearch was called correctly
        mock_es_client.search.assert_called_once()
        call_args = mock_es_client.search.call_args
        assert call_args[1]["index"] == "properties"
        assert "aggs" in call_args[1]["body"]
    
    def test_demo_price_distribution(self, mock_es_client):
        """Test demo_price_distribution function."""
        # Mock Elasticsearch response with properly formatted address
        mock_response = {
            "took": 15,
            "hits": {
                "total": {"value": 200},
                "hits": [
                    {
                        "_source": {
                            "listing_id": "prop-1",
                            "address": {
                                "street": "123 Main St",
                                "city": "San Francisco",
                                "state": "CA",
                                "zip": "94102"
                            },
                            "price": 500000,
                            "bedrooms": 3,
                            "bathrooms": 2,
                            "square_feet": 2000,
                            "property_type": "single-family",
                            "description": "Test property",
                            "year_built": 2000,
                            "lot_size": 5000,
                            "garage_spaces": 2,
                            "amenities": [],
                            "neighborhood_id": "test-neighborhood",
                            "price_per_sqft": 250.0,
                            "walk_score": 80,
                            "transit_score": 70,
                            "bike_score": 75,
                            "elementary_school": "Test Elementary",
                            "middle_school": "Test Middle",
                            "high_school": "Test High",
                            "elementary_rating": 8,
                            "middle_rating": 7,
                            "high_rating": 8,
                            "elementary_distance": 0.5,
                            "middle_distance": 1.0,
                            "high_distance": 1.5,
                            "nearby_parks": [],
                            "nearby_groceries": [],
                            "nearby_restaurants": [],
                            "location": {"lat": 37.7749, "lon": -122.4194}
                        }
                    }
                ]
            },
            "aggregations": {
                "price_histogram": {
                    "buckets": [
                        {
                            "key": 200000,
                            "doc_count": 50,
                            "by_property_type": {"buckets": []},
                            "stats": {"avg": 225000}
                        }
                    ]
                },
                "price_percentiles": {
                    "values": {
                        "25.0": 250000,
                        "50.0": 450000,
                        "75.0": 650000
                    }
                },
                "by_property_type_stats": {
                    "buckets": []
                }
            }
        }
        
        mock_es_client.search.return_value = mock_response
        
        # Execute demo function
        result = demo_price_distribution(
            mock_es_client,
            interval=100000,
            min_price=0,
            max_price=1000000
        )
        
        # Verify result
        assert result.query_name == "Demo 5: Price Distribution Analysis"
        assert result.execution_time_ms == 15
        assert result.total_hits == 200
        assert result.returned_hits == 1
        assert len(result.top_properties) == 1
        assert "price_histogram" in result.aggregations
        
        # Verify Elasticsearch was called correctly
        mock_es_client.search.assert_called_once()
        call_args = mock_es_client.search.call_args
        assert call_args[1]["index"] == "properties"
        assert "query" in call_args[1]["body"]
        assert "aggs" in call_args[1]["body"]


class TestErrorHandling:
    """Test error handling in the aggregation module."""
    
    def test_result_processor_handles_missing_data(self):
        """Test that result processor handles missing data gracefully."""
        processor = AggregationResultProcessor()
        
        # Test with empty response
        results = processor.process_neighborhood_aggregations({})
        assert results == []
        
        # Test with missing aggregations
        results = processor.process_price_distribution({})
        assert results == []
        
        # Test with None values - should handle gracefully
        response = {
            "aggregations": {
                "by_neighborhood": {
                    "buckets": [
                        {
                            "key": "test",
                            "property_count": {"value": 0},  # Use 0 instead of None
                            "avg_price": {"value": None},
                            "min_price": {"value": None},
                            "max_price": {"value": None},
                            "avg_bedrooms": {"value": None},
                            "avg_square_feet": {"value": None},
                            "price_per_sqft": {"value": None},
                            "property_types": {"buckets": []}
                        }
                    ]
                }
            }
        }
        results = processor.process_neighborhood_aggregations(response)
        assert len(results) == 1
        assert results[0].avg_price == 0  # Should default to 0
        assert results[0].property_count == 0
    
    def test_demo_functions_handle_errors(self):
        """Test that demo functions handle Elasticsearch errors gracefully."""
        mock_es_client = Mock(spec=Elasticsearch)
        mock_es_client.search.side_effect = Exception("Elasticsearch error")
        
        # Test neighborhood stats with error
        result = demo_neighborhood_stats(mock_es_client)
        assert result.total_hits == 0
        assert result.execution_time_ms == 0
        assert "Error occurred" in result.query_description
        
        # Test price distribution with error
        result = demo_price_distribution(mock_es_client)
        assert result.total_hits == 0
        assert result.execution_time_ms == 0
        assert "Error occurred" in result.query_description


if __name__ == "__main__":
    pytest.main([__file__, "-v"])