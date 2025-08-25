"""
FastMCP testing for async services.
Tests all services using MCP in-memory client pattern.
Based on https://gofastmcp.com/deployment/testing
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from fastmcp import FastMCP
try:
    from fastmcp import Client
except ImportError:
    # Fallback for older FastMCP versions
    from mcp import Client

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from services import (
    SearchEngine, PropertyIndexer, WikipediaEnrichmentService,
    MarketAnalysisService, LocationService
)
from models import (
    Property, PropertyType, Address, GeoLocation,
    PropertySearchParams, SearchMode, SearchFilters
)


@pytest.fixture
def services_test_server():
    """Create MCP server with service testing tools."""
    server = FastMCP("services-test-server")
    
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
    
    mock_es.get = AsyncMock(return_value={
        "found": True,
        "_id": "test-1",
        "_source": {
            "id": "test-1",
            "listing_id": "MLS123",
            "property_type": "single_family",
            "price": 500000,
            "bedrooms": 3,
            "bathrooms": 2.5,
            "address": {
                "street": "123 Main St",
                "city": "Austin",
                "state": "TX",
                "zip_code": "78701"
            }
        }
    })
    
    mock_es.indices = AsyncMock()
    mock_es.indices.exists = AsyncMock(return_value=True)
    mock_es.indices.create = AsyncMock(return_value={"acknowledged": True})
    mock_es.indices.refresh = AsyncMock(return_value={"_shards": {"successful": 1}})
    mock_es.count = AsyncMock(return_value={"count": 100})
    
    # Initialize services
    search_engine = SearchEngine(mock_es)
    indexer = PropertyIndexer(mock_es)
    enrichment = WikipediaEnrichmentService()
    market_analysis = MarketAnalysisService(mock_es)
    location = LocationService()
    
    @server.tool
    async def search_properties(
        query: str,
        city: str,
        max_results: int = 10
    ) -> dict:
        """Test property search functionality."""
        params = PropertySearchParams(
            query=query,
            location=city,
            max_results=max_results
        )
        
        results = await search_engine.search(params)
        
        return {
            "total": results.total,
            "count": len(results.properties),
            "first_property": results.properties[0].id if results.properties else None
        }
    
    @server.tool
    async def geo_search(
        lat: float,
        lon: float,
        radius: float
    ) -> dict:
        """Test geographic search."""
        from models import GeoSearchParams, GeoDistanceUnit
        
        params = GeoSearchParams(
            center=GeoLocation(lat=lat, lon=lon),
            radius=radius,
            unit=GeoDistanceUnit.miles
        )
        
        results = await search_engine.geo_search(params)
        
        return {
            "total": results.total,
            "count": len(results.properties)
        }
    
    @server.tool
    async def enrich_property(property_id: str) -> dict:
        """Test property enrichment."""
        # Create test property
        prop = Property(
            id=property_id,
            listing_id="MLS999",
            property_type=PropertyType.condo,
            price=400000,
            bedrooms=2,
            bathrooms=2,
            address=Address(
                street="456 Oak St",
                city="Austin",
                state="TX",
                zip_code="78702",
                location=GeoLocation(lat=30.26, lon=-97.73)
            )
        )
        
        enrichment_bundle = await enrichment.enrich_property(prop)
        
        return {
            "has_enrichment": enrichment_bundle.has_enrichment(),
            "has_wikipedia": enrichment_bundle.wikipedia_context is not None,
            "has_pois": len(enrichment_bundle.nearby_pois) > 0,
            "has_neighborhood": enrichment_bundle.neighborhood_context is not None,
            "poi_count": len(enrichment_bundle.nearby_pois)
        }
    
    @server.tool
    async def analyze_market_position(
        property_price: float,
        city: str
    ) -> dict:
        """Test market position analysis."""
        # Create test property
        prop = Property(
            id="market-test",
            listing_id="MLS888",
            property_type=PropertyType.single_family,
            price=property_price,
            bedrooms=3,
            bathrooms=2,
            square_feet=2000,
            address=Address(
                street="789 Elm St",
                city=city,
                state="TX",
                zip_code="78703"
            )
        )
        
        position = await market_analysis.analyze_market_position(prop)
        
        return {
            "price_percentile": position.price_percentile,
            "competitive_properties": position.competitive_properties,
            "recommendation": position.pricing_recommendation,
            "days_estimate": position.days_on_market_estimate
        }
    
    @server.tool
    async def calculate_investment_metrics(
        property_price: float
    ) -> dict:
        """Test investment metrics calculation."""
        prop = Property(
            id="invest-test",
            listing_id="MLS777",
            property_type=PropertyType.condo,
            price=property_price,
            bedrooms=2,
            bathrooms=2,
            square_feet=1500,
            address=Address(
                street="321 Pine St",
                city="Dallas",
                state="TX",
                zip_code="75201"
            )
        )
        
        metrics = await market_analysis.calculate_investment_metrics(prop)
        
        return {
            "estimated_rent": metrics.estimated_rent,
            "gross_yield": round(metrics.gross_yield, 2),
            "cap_rate": round(metrics.cap_rate, 2),
            "investment_grade": metrics.investment_grade.value,
            "investment_score": metrics.investment_score
        }
    
    @server.tool
    async def geocode_address(address: str) -> dict:
        """Test geocoding service."""
        location = await location.geocode_address(address)
        
        if location:
            return {
                "success": True,
                "lat": round(location.lat, 4),
                "lon": round(location.lon, 4)
            }
        return {"success": False}
    
    @server.tool
    async def find_nearby_pois(
        lat: float,
        lon: float,
        radius: float
    ) -> dict:
        """Test POI discovery."""
        center = GeoLocation(lat=lat, lon=lon)
        pois = await location.find_nearby_pois(center, radius_miles=radius)
        
        return {
            "count": len(pois),
            "categories": list(set(poi.category.value for poi in pois)),
            "nearest": pois[0].name if pois else None
        }
    
    @server.tool
    async def calculate_walkability(lat: float, lon: float) -> dict:
        """Test walkability calculation."""
        center = GeoLocation(lat=lat, lon=lon)
        score = await location.calculate_walkability_score(center)
        
        return {
            "score": score,
            "category": "Very Walkable" if score >= 70 else "Somewhat Walkable" if score >= 50 else "Car-Dependent"
        }
    
    return server


@pytest.mark.asyncio
async def test_search_engine_via_mcp(services_test_server):
    """Test SearchEngine through MCP tools."""
    async with Client(services_test_server) as client:
        # Test standard search
        result = await client.call_tool("search_properties", {
            "query": "modern kitchen",
            "city": "Austin",
            "max_results": 20
        })
        
        assert result.data["total"] == 1
        assert result.data["count"] == 1
        assert result.data["first_property"] == "test-1"
        
        # Test geo search
        result = await client.call_tool("geo_search", {
            "lat": 30.2672,
            "lon": -97.7431,
            "radius": 5.0
        })
        
        assert result.data["total"] == 1
        assert result.data["count"] == 1


@pytest.mark.asyncio
async def test_enrichment_service_via_mcp(services_test_server):
    """Test WikipediaEnrichmentService through MCP tools."""
    async with Client(services_test_server) as client:
        result = await client.call_tool("enrich_property", {
            "property_id": "enrich-test-1"
        })
        
        assert result.data["has_enrichment"]
        assert result.data["has_wikipedia"]
        assert result.data["has_pois"]
        assert result.data["has_neighborhood"]
        assert result.data["poi_count"] > 0


@pytest.mark.asyncio
async def test_market_analysis_via_mcp(services_test_server):
    """Test MarketAnalysisService through MCP tools."""
    async with Client(services_test_server) as client:
        # Test market position
        result = await client.call_tool("analyze_market_position", {
            "property_price": 450000,
            "city": "Austin"
        })
        
        assert 0 <= result.data["price_percentile"] <= 100
        assert result.data["competitive_properties"] >= 0
        assert result.data["recommendation"] is not None
        assert result.data["days_estimate"] > 0
        
        # Test investment metrics
        result = await client.call_tool("calculate_investment_metrics", {
            "property_price": 350000
        })
        
        assert result.data["estimated_rent"] > 0
        assert result.data["gross_yield"] > 0
        assert result.data["cap_rate"] > 0
        assert result.data["investment_grade"] in ["A+", "A", "B+", "B", "C", "D", "F"]
        assert 0 <= result.data["investment_score"] <= 100


@pytest.mark.asyncio
async def test_location_service_via_mcp(services_test_server):
    """Test LocationService through MCP tools."""
    async with Client(services_test_server) as client:
        # Test geocoding
        result = await client.call_tool("geocode_address", {
            "address": "123 Main St, Austin, TX"
        })
        
        assert result.data["success"]
        assert -90 <= result.data["lat"] <= 90
        assert -180 <= result.data["lon"] <= 180
        
        # Test POI discovery
        result = await client.call_tool("find_nearby_pois", {
            "lat": 30.2672,
            "lon": -97.7431,
            "radius": 2.0
        })
        
        assert result.data["count"] > 0
        assert len(result.data["categories"]) > 0
        assert result.data["nearest"] is not None
        
        # Test walkability
        result = await client.call_tool("calculate_walkability", {
            "lat": 30.2672,
            "lon": -97.7431
        })
        
        assert 0 <= result.data["score"] <= 100
        assert result.data["category"] in ["Very Walkable", "Somewhat Walkable", "Car-Dependent"]


@pytest.mark.asyncio
async def test_service_error_handling():
    """Test error handling in services via MCP."""
    server = FastMCP("error-test-server")
    
    @server.tool
    async def test_search_error() -> dict:
        """Test search engine error handling."""
        mock_es = AsyncMock()
        mock_es.search = AsyncMock(side_effect=Exception("ES connection failed"))
        
        engine = SearchEngine(mock_es)
        
        try:
            params = PropertySearchParams(query="test")
            await engine.search(params)
            return {"error_caught": False}
        except Exception as e:
            return {"error_caught": True, "error": str(e)}
    
    async with Client(server) as client:
        result = await client.call_tool("test_search_error", {})
        assert result.data["error_caught"]
        assert "ES connection failed" in result.data["error"]


@pytest.mark.asyncio
async def test_service_concurrency():
    """Test concurrent service operations via MCP."""
    server = FastMCP("concurrency-test")
    
    @server.tool
    async def concurrent_operations() -> dict:
        """Test running multiple services concurrently."""
        location_service = LocationService()
        enrichment_service = WikipediaEnrichmentService()
        
        # Run multiple operations concurrently
        import asyncio
        tasks = [
            location_service.geocode_address("Austin, TX"),
            location_service.geocode_address("Dallas, TX"),
            location_service.geocode_address("Houston, TX"),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "completed": len([r for r in results if not isinstance(r, Exception)]),
            "failed": len([r for r in results if isinstance(r, Exception)]),
            "total": len(results)
        }
    
    async with Client(server) as client:
        result = await client.call_tool("concurrent_operations", {})
        assert result.data["completed"] == 3
        assert result.data["failed"] == 0
        assert result.data["total"] == 3


def test_all_services_async():
    """Verify all service methods are async."""
    import inspect
    
    services = [
        SearchEngine,
        PropertyIndexer,
        WikipediaEnrichmentService,
        MarketAnalysisService,
        LocationService
    ]
    
    for service_class in services:
        methods = inspect.getmembers(service_class, predicate=inspect.isfunction)
        
        for name, method in methods:
            if not name.startswith('_') and name != 'calculate_distance':
                assert inspect.iscoroutinefunction(method), \
                    f"{service_class.__name__}.{name} is not async"


if __name__ == "__main__":
    print("Running FastMCP service tests...")
    
    # Create test server
    server = services_test_server()
    
    # Run async tests
    asyncio.run(test_search_engine_via_mcp(server))
    print("✓ SearchEngine service")
    
    asyncio.run(test_enrichment_service_via_mcp(server))
    print("✓ WikipediaEnrichmentService")
    
    asyncio.run(test_market_analysis_via_mcp(server))
    print("✓ MarketAnalysisService")
    
    asyncio.run(test_location_service_via_mcp(server))
    print("✓ LocationService")
    
    asyncio.run(test_service_error_handling())
    print("✓ Service error handling")
    
    asyncio.run(test_service_concurrency())
    print("✓ Service concurrency")
    
    # Run sync tests
    test_all_services_async()
    print("✓ All services async")
    
    print("\n✅ All service tests passed!")