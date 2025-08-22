"""
Simple integration tests for MCP server components.
Tests the core functionality without complex client setup.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from fastmcp import FastMCP
from main import settings
from models import (
    Property, PropertyType, Address, GeoLocation,
    PropertySearchParams, SearchMode
)
from services import SearchEngine, LocationService, WikipediaEnrichmentService


async def test_search_service():
    """Test search engine service directly."""
    # Mock Elasticsearch
    mock_es = AsyncMock()
    mock_es.search = AsyncMock(return_value={
        "hits": {
            "total": {"value": 2},
            "hits": [
                {
                    "_id": "test-1",
                    "_score": 0.95,
                    "_source": {
                        "id": "test-1",
                        "listing_id": "MLS123",
                        "property_type": "single_family",
                        "price": 500000,
                        "bedrooms": 3,
                        "bathrooms": 2.5,
                        "square_feet": 2000,
                        "address": {
                            "street": "123 Main St",
                            "city": "Austin",
                            "state": "TX",
                            "zip_code": "78701"
                        },
                        "description": "Beautiful home with modern kitchen",
                        "features": ["garage", "pool"]
                    }
                },
                {
                    "_id": "test-2",
                    "_score": 0.85,
                    "_source": {
                        "id": "test-2",
                        "listing_id": "MLS456",
                        "property_type": "condo",
                        "price": 350000,
                        "bedrooms": 2,
                        "bathrooms": 2,
                        "square_feet": 1500,
                        "address": {
                            "street": "456 Oak Ave",
                            "city": "Austin",
                            "state": "TX",
                            "zip_code": "78702"
                        },
                        "description": "Modern condo in downtown",
                        "features": ["balcony", "gym"]
                    }
                }
            ]
        },
        "took": 25
    })
    
    # Create search engine
    search_engine = SearchEngine(mock_es)
    
    # Test search
    params = PropertySearchParams(
        query="modern kitchen",
        location="Austin",
        max_results=10
    )
    
    results = await search_engine.search(params)
    
    assert results.total == 2
    assert len(results.properties) == 2
    assert results.properties[0].price == 500000
    assert results.properties[0].address.city == "Austin"
    print("✓ Search service works")


async def test_location_service():
    """Test location service directly."""
    location_service = LocationService()
    
    # Test geocoding
    location = await location_service.geocode_address("123 Main St, Austin, TX")
    assert location is not None
    assert -90 <= location.lat <= 90
    assert -180 <= location.lon <= 180
    
    # Test POI discovery
    pois = await location_service.find_nearby_pois(location, radius_miles=2.0)
    assert len(pois) > 0
    assert pois[0].category is not None
    
    # Test walkability
    score = await location_service.calculate_walkability_score(location)
    assert 0 <= score <= 100
    
    print("✓ Location service works")


async def test_enrichment_service():
    """Test enrichment service directly."""
    enrichment_service = WikipediaEnrichmentService()
    
    # Create test property
    prop = Property(
        id="test-prop",
        listing_id="MLS789",
        property_type=PropertyType.single_family,
        price=450000,
        bedrooms=3,
        bathrooms=2.5,
        address=Address(
            street="789 Elm St",
            city="Austin",
            state="TX",
            zip_code="78703",
            location=GeoLocation(lat=30.27, lon=-97.74)
        )
    )
    
    # Test enrichment
    enrichment = await enrichment_service.enrich_property(prop)
    
    assert enrichment.property_id == "test-prop"
    assert enrichment.has_enrichment()
    assert enrichment.wikipedia_context is not None
    assert len(enrichment.nearby_pois) > 0
    assert enrichment.neighborhood_context is not None
    
    print("✓ Enrichment service works")


def test_configuration():
    """Test configuration loading."""
    assert settings.server.name == "real-estate-search"
    assert settings.server.version == "1.0.0"
    assert settings.elasticsearch.host == "localhost"
    assert settings.elasticsearch.port == 9200
    assert settings.elasticsearch.index_name == "properties_demo"
    assert settings.is_demo or settings.environment == "demo"
    print("✓ Configuration loads correctly")


def test_mcp_server_creation():
    """Test that MCP server can be created."""
    server = FastMCP("test-server")
    
    # Define function first, then decorate
    def test_tool_impl(value: int) -> dict:
        """Test tool."""
        return {"result": value * 2}
    
    # Register as tool
    server.tool(test_tool_impl)
    
    # Test the original function
    result = test_tool_impl(21)
    assert result["result"] == 42
    
    print("✓ MCP server creation works")


async def run_all_tests():
    """Run all integration tests."""
    print("Running integration tests...\n")
    
    # Test configuration
    test_configuration()
    
    # Test MCP server
    test_mcp_server_creation()
    
    # Test async services
    await test_search_service()
    await test_location_service()
    await test_enrichment_service()
    
    print("\n✅ All integration tests passed!")


if __name__ == "__main__":
    asyncio.run(run_all_tests())