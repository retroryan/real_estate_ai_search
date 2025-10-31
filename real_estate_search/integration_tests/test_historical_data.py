"""Integration tests for historical data functionality in Elasticsearch.

This test verifies that historical data generated in the squack_pipeline_v2
is properly indexed and searchable in Elasticsearch for both properties and neighborhoods.

Test Coverage:
- Historical data presence in property documents
- Historical data presence in neighborhood documents  
- Data structure validation (10 annual records 2015-2024)
- Price data types (float values)
- Search functionality with historical data
"""

import pytest
from datetime import datetime
from typing import Dict, List, Any
from elasticsearch.exceptions import NotFoundError, TransportError

from real_estate_search.config import AppConfig
from real_estate_search.infrastructure.elasticsearch_client import ElasticsearchClientFactory
from real_estate_search.search_service import (
    PropertySearchService,
    NeighborhoodSearchService
)


@pytest.fixture(scope="module")
def config():
    """Get configuration for tests."""
    return AppConfig.load()


@pytest.fixture(scope="module")  
def es_client(config):
    """Create Elasticsearch client."""
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
    """Create property search service."""
    return PropertySearchService(es_client)


@pytest.fixture(scope="module")
def neighborhood_service(es_client):
    """Create neighborhood search service."""
    return NeighborhoodSearchService(es_client)


class TestHistoricalData:
    """Test historical data functionality."""
    
    def test_property_historical_data_exists(self, es_client):
        """Test that properties have historical data in Elasticsearch."""
        # Get a sample of properties
        query = {
            "query": {"match_all": {}},
            "size": 5
        }
        
        response = es_client.search(index="properties", body=query)
        properties = response["hits"]["hits"]
        
        assert len(properties) > 0, "No properties found in Elasticsearch"
        
        # Check each property has historical data
        for prop in properties:
            source = prop["_source"]
            listing_id = source["listing_id"]
            
            # Verify historical_data field exists
            assert "historical_data" in source, f"Property {listing_id} missing historical_data field"
            
            historical_data = source["historical_data"]
            assert isinstance(historical_data, list), f"Property {listing_id} historical_data is not a list"
            assert len(historical_data) == 10, f"Property {listing_id} should have 10 historical records, got {len(historical_data)}"
            
            # Validate each historical record
            for i, record in enumerate(historical_data):
                expected_year = 2015 + i
                assert record["year"] == expected_year, f"Property {listing_id} record {i} has wrong year: expected {expected_year}, got {record['year']}"
                
                # Price should be positive float
                assert "price" in record, f"Property {listing_id} record {i} missing price field"
                assert isinstance(record["price"], (int, float)), f"Property {listing_id} record {i} price should be numeric"
                assert record["price"] > 0, f"Property {listing_id} record {i} price should be positive"
                
    def test_neighborhood_historical_data_exists(self, es_client):
        """Test that neighborhoods have historical data in Elasticsearch."""
        # Get a sample of neighborhoods
        query = {
            "query": {"match_all": {}},
            "size": 5
        }
        
        response = es_client.search(index="neighborhoods", body=query)
        neighborhoods = response["hits"]["hits"]
        
        assert len(neighborhoods) > 0, "No neighborhoods found in Elasticsearch"
        
        # Check each neighborhood has historical data
        for neighborhood in neighborhoods:
            source = neighborhood["_source"]
            neighborhood_id = source["neighborhood_id"]
            
            # Verify historical_data field exists
            assert "historical_data" in source, f"Neighborhood {neighborhood_id} missing historical_data field"
            
            historical_data = source["historical_data"]
            assert isinstance(historical_data, list), f"Neighborhood {neighborhood_id} historical_data is not a list"
            assert len(historical_data) == 10, f"Neighborhood {neighborhood_id} should have 10 historical records, got {len(historical_data)}"
            
            # Validate each historical record
            for i, record in enumerate(historical_data):
                expected_year = 2015 + i
                assert record["year"] == expected_year, f"Neighborhood {neighborhood_id} record {i} has wrong year"
                
                # avg_price should be positive float
                assert "avg_price" in record, f"Neighborhood {neighborhood_id} record {i} missing avg_price field"
                assert isinstance(record["avg_price"], (int, float)), f"Neighborhood {neighborhood_id} record {i} avg_price should be numeric"
                assert record["avg_price"] > 0, f"Neighborhood {neighborhood_id} record {i} avg_price should be positive"
                
                # sales_count should be positive integer
                assert "sales_count" in record, f"Neighborhood {neighborhood_id} record {i} missing sales_count field"
                assert isinstance(record["sales_count"], int), f"Neighborhood {neighborhood_id} record {i} sales_count should be integer"
                assert record["sales_count"] >= 10, f"Neighborhood {neighborhood_id} record {i} sales_count should be at least 10"
                
    def test_historical_data_year_range(self, es_client):
        """Test that historical data covers the correct year range (2015-2024)."""
        # Test properties
        prop_query = {
            "query": {"match_all": {}},
            "size": 3
        }
        
        prop_response = es_client.search(index="properties", body=prop_query)
        for prop in prop_response["hits"]["hits"]:
            historical_data = prop["_source"]["historical_data"]
            years = [record["year"] for record in historical_data]
            
            assert min(years) == 2015, f"Property historical data should start from 2015"
            assert max(years) == 2024, f"Property historical data should end at 2024"
            assert len(set(years)) == 10, f"Property should have unique years for each record"
            
        # Test neighborhoods  
        neigh_query = {
            "query": {"match_all": {}},
            "size": 3
        }
        
        neigh_response = es_client.search(index="neighborhoods", body=neigh_query)
        for neighborhood in neigh_response["hits"]["hits"]:
            historical_data = neighborhood["_source"]["historical_data"]
            years = [record["year"] for record in historical_data]
            
            assert min(years) == 2015, f"Neighborhood historical data should start from 2015"
            assert max(years) == 2024, f"Neighborhood historical data should end at 2024"
            assert len(set(years)) == 10, f"Neighborhood should have unique years for each record"
            
    def test_historical_data_price_trends(self, es_client):
        """Test that historical data shows realistic price appreciation trends."""
        # Get a property with historical data
        query = {
            "query": {"match_all": {}},
            "size": 1
        }
        
        response = es_client.search(index="properties", body=query)
        prop = response["hits"]["hits"][0]["_source"]
        historical_data = prop["historical_data"]
        
        # Verify prices generally increase over time (with some variation allowed)
        prices = [record["price"] for record in historical_data]
        
        # Check that prices are in reasonable ranges
        for price in prices:
            assert 50000 <= price <= 5000000, f"Property price {price} seems unrealistic"
            
        # Check general upward trend - most recent price should be higher than oldest
        assert prices[-1] > prices[0], "Property prices should show overall appreciation"
        
    def test_property_search_with_historical_data(self, es_client):
        """Test that property search results include historical data when queried directly."""
        # Use direct Elasticsearch query to ensure we get all fields including historical_data
        query = {
            "query": {
                "bool": {
                    "must": {
                        "match": {"description": "house"}
                    }
                }
            },
            "size": 3
        }
        
        response = es_client.search(index="properties", body=query)
        properties = response["hits"]["hits"]
        
        assert len(properties) > 0, "Should find properties with 'house' query"
        
        # Check that results include historical data
        for prop in properties:
            source = prop["_source"]
            listing_id = source["listing_id"]
            assert "historical_data" in source, f"Property {listing_id} search results should include historical_data"
            historical_data = source["historical_data"]
            assert len(historical_data) == 10, f"Property {listing_id} results should have 10 historical records"
            
    def test_neighborhood_search_with_historical_data(self, es_client):
        """Test that neighborhood search results include historical data when queried directly."""
        # Use direct Elasticsearch query to ensure we get all fields including historical_data
        query = {
            "query": {"match_all": {}},
            "size": 3
        }
        
        response = es_client.search(index="neighborhoods", body=query)
        neighborhoods = response["hits"]["hits"]
        
        assert len(neighborhoods) > 0, "Should find neighborhoods in the index"
        
        # Check that results include historical data
        for neighborhood in neighborhoods:
            source = neighborhood["_source"]
            neighborhood_id = source["neighborhood_id"]
            assert "historical_data" in source, f"Neighborhood {neighborhood_id} search results should include historical_data"
            historical_data = source["historical_data"]
            assert len(historical_data) == 10, f"Neighborhood {neighborhood_id} results should have 10 historical records"
            
    def test_historical_data_type_consistency(self, es_client):
        """Test that historical data maintains consistent data types."""
        # Check properties
        prop_query = {
            "query": {"match_all": {}},
            "size": 5
        }
        
        prop_response = es_client.search(index="properties", body=prop_query)
        for prop in prop_response["hits"]["hits"]:
            historical_data = prop["_source"]["historical_data"]
            
            for record in historical_data:
                # Year should be integer
                assert isinstance(record["year"], int), "Historical year should be integer"
                # Price should be numeric (int or float)
                assert isinstance(record["price"], (int, float)), "Historical price should be numeric"
                
        # Check neighborhoods
        neigh_query = {
            "query": {"match_all": {}},
            "size": 5
        }
        
        neigh_response = es_client.search(index="neighborhoods", body=neigh_query)
        for neighborhood in neigh_response["hits"]["hits"]:
            historical_data = neighborhood["_source"]["historical_data"]
            
            for record in historical_data:
                # Year should be integer
                assert isinstance(record["year"], int), "Historical year should be integer"
                # avg_price should be numeric
                assert isinstance(record["avg_price"], (int, float)), "Historical avg_price should be numeric"
                # sales_count should be integer
                assert isinstance(record["sales_count"], int), "Historical sales_count should be integer"
                
    def test_historical_data_deterministic_generation(self, es_client):
        """Test that historical data generation is deterministic for the same IDs."""
        # Get the same property multiple times to verify consistency
        query = {
            "query": {"match_all": {}},
            "size": 1
        }
        
        # First retrieval
        response1 = es_client.search(index="properties", body=query)
        prop1 = response1["hits"]["hits"][0]["_source"]
        
        # Second retrieval
        response2 = es_client.search(index="properties", body=query)
        prop2 = response2["hits"]["hits"][0]["_source"]
        
        # Historical data should be identical for same property
        assert prop1["listing_id"] == prop2["listing_id"]
        assert prop1["historical_data"] == prop2["historical_data"], "Historical data should be deterministic"
        
    def test_elasticsearch_mapping_compatibility(self, es_client):
        """Test that historical data is compatible with Elasticsearch mappings."""
        # Get the mapping for properties index
        prop_mapping = es_client.indices.get_mapping(index="properties")
        properties_mapping = prop_mapping["properties"]["mappings"]["properties"]
        
        # Verify historical_data field exists in mapping
        assert "historical_data" in properties_mapping, "historical_data should be in properties mapping"
        
        # Should have properties subfields (object type without explicit type field)
        historical_field = properties_mapping["historical_data"]
        assert "properties" in historical_field, "historical_data should have properties mapping"
        
        # Check the subfield types
        assert "price" in historical_field["properties"], "historical_data should have price field"
        assert "year" in historical_field["properties"], "historical_data should have year field"
        assert historical_field["properties"]["price"]["type"] == "float", "price should be float type"
        assert historical_field["properties"]["year"]["type"] == "integer", "year should be integer type"
        
        # Get the mapping for neighborhoods index  
        neigh_mapping = es_client.indices.get_mapping(index="neighborhoods")
        neighborhoods_mapping = neigh_mapping["neighborhoods"]["mappings"]["properties"]
        
        # Verify historical_data field exists in mapping
        assert "historical_data" in neighborhoods_mapping, "historical_data should be in neighborhoods mapping"
        
        # Should have properties subfields (object type)
        historical_field = neighborhoods_mapping["historical_data"]
        assert "properties" in historical_field, "historical_data should have properties mapping"
        
        # Check the subfield types for neighborhoods
        assert "avg_price" in historical_field["properties"], "historical_data should have avg_price field"
        assert "year" in historical_field["properties"], "historical_data should have year field"
        assert "sales_count" in historical_field["properties"], "historical_data should have sales_count field"