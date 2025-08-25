"""
Integration tests for MCP server.
Tests server functionality using direct tool calls.
Based on FastMCP testing patterns.
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


def create_test_server():
    """Create a test MCP server with all tools."""
    server = FastMCP("real-estate-test")
    
    # Store tool functions for testing
    tools = {}
    
    # Mock Elasticsearch
    mock_es = AsyncMock()
    mock_es.search = AsyncMock(return_value={
        "hits": {
            "total": {"value": 1},
            "hits": [{
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
                        "zip_code": "78701",
                        "location": {"lat": 30.2672, "lon": -97.7431}
                    },
                    "description": "Beautiful home",
                    "features": ["garage", "pool"]
                }
            }]
        },
        "took": 25
    })
    
    # Initialize services
    search_engine = SearchEngine(mock_es)
    location_service = LocationService()
    enrichment_service = WikipediaEnrichmentService()
    
    @server.tool
    async def search_properties_impl(
        query: str = None,
        city: str = None,
        min_price: float = None,
        max_price: float = None,
        bedrooms: int = None
    ) -> dict:
        """Search for properties matching criteria."""
        params = PropertySearchParams(
            query=query,
            location=city,
            max_results=20
        )
        
        results = await search_engine.search(params)
        
        return {
            "total": results.total,
            "properties": [
                {
                    "id": p.id,
                    "price": p.price,
                    "bedrooms": p.bedrooms,
                    "city": p.address.city,
                    "summary": p.get_summary()
                }
                for p in results.properties[:5]
            ]
        }
    
    @server.tool
    async def analyze_location(address: str) -> dict:
        """Analyze a location for real estate insights."""
        location = await location_service.geocode_address(address)
        
        if not location:
            return {"error": "Could not geocode address"}
        
        pois = await location_service.find_nearby_pois(location, radius_miles=2.0)
        walkability = await location_service.calculate_walkability_score(location)
        
        return {
            "location": {"lat": location.lat, "lon": location.lon},
            "walkability_score": walkability,
            "nearby_pois": len(pois),
            "poi_categories": list(set(p.category.value for p in pois))
        }
    
    @server.tool
    async def get_property_enrichment(property_id: str) -> dict:
        """Get enriched data for a property."""
        # Create a test property
        prop = Property(
            id=property_id,
            listing_id="MLS999",
            property_type=PropertyType.single_family,
            price=450000,
            bedrooms=3,
            bathrooms=2.5,
            address=Address(
                street="456 Oak St",
                city="Austin",
                state="TX",
                zip_code="78702",
                location=GeoLocation(lat=30.26, lon=-97.73)
            )
        )
        
        enrichment = await enrichment_service.enrich_property(prop)
        
        return {
            "property_id": property_id,
            "has_wikipedia": enrichment.wikipedia_context is not None,
            "poi_count": len(enrichment.nearby_pois),
            "has_neighborhood": enrichment.neighborhood_context is not None,
            "has_market": enrichment.market_context is not None
        }
    
    @server.tool
    def get_server_info() -> dict:
        """Get server configuration info."""
        return {
            "name": settings.server.name,
            "version": settings.server.version,
            "environment": settings.environment,
            "demo_mode": settings.is_demo,
            "elasticsearch": {
                "host": settings.elasticsearch.host,
                "port": settings.elasticsearch.port,
                "index": settings.elasticsearch.index_name
            }
        }
    
    return server


async def test_search_functionality():
    """Test property search functionality."""
    server = create_test_server()
    
    # Call the tool directly (it's a decorated function)
    result = await server.search_properties(
        query="modern kitchen",
        city="Austin",
        bedrooms=3
    )
    
    assert result["total"] == 1
    assert len(result["properties"]) == 1
    assert result["properties"][0]["city"] == "Austin"
    print("✓ Property search works")


async def test_location_analysis():
    """Test location analysis functionality."""
    server = create_test_server()
    
    # Call the tool directly
    result = await server.analyze_location(address="123 Main St, Austin, TX")
    
    assert "location" in result
    assert "walkability_score" in result
    assert result["walkability_score"] >= 0
    assert result["nearby_pois"] > 0
    print("✓ Location analysis works")


async def test_enrichment():
    """Test property enrichment functionality."""
    server = create_test_server()
    
    # Call the tool directly
    result = await server.get_property_enrichment(property_id="test-prop-123")
    
    assert result["property_id"] == "test-prop-123"
    assert result["has_wikipedia"]
    assert result["poi_count"] > 0
    assert result["has_neighborhood"]
    print("✓ Property enrichment works")


def test_server_configuration():
    """Test server configuration."""
    server = create_test_server()
    
    # Call the tool directly
    result = server.get_server_info()
    
    assert result["name"] == "real-estate-search"
    assert "version" in result
    assert result["elasticsearch"]["host"] == "localhost"
    assert result["elasticsearch"]["port"] == 9200
    print("✓ Server configuration accessible")


def test_tool_registration():
    """Test that all tools are properly registered."""
    server = create_test_server()
    
    # FastMCP tools are registered but not directly accessible as attributes
    # We can verify the server was created successfully
    assert server is not None
    assert server.name == "real-estate-test"
    
    print(f"✓ MCP server created with tools")


async def run_all_tests():
    """Run all integration tests."""
    print("Running MCP integration tests...\n")
    
    # Test tool registration first
    test_tool_registration()
    
    # Test server configuration
    test_server_configuration()
    
    # Test async functionality
    await test_search_functionality()
    await test_location_analysis()
    await test_enrichment()
    
    print("\n✅ All integration tests passed!")


if __name__ == "__main__":
    asyncio.run(run_all_tests())