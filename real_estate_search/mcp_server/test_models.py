"""
FastMCP testing for data models.
Tests all Pydantic models using MCP tools.
Based on https://gofastmcp.com/deployment/testing
"""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path
from fastmcp import FastMCP
try:
    from fastmcp import Client
except ImportError:
    # Fallback for older FastMCP versions
    from mcp import Client

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from models import (
    # Property models
    PropertyType, GeoLocation, Address, Property, PropertyHit,
    # Search models
    SearchMode, SortOrder, GeoDistanceUnit, PriceRange, SearchFilters,
    PropertySearchParams, GeoSearchParams, SearchResults,
    # Enrichment models
    POICategory, WikipediaContext, POIInfo, NeighborhoodContext,
    # Analysis models
    InvestmentGrade, MarketPosition, InvestmentMetrics,
    PropertyAnalysis, AffordabilityAnalysis
)


@pytest.fixture
def model_test_server():
    """Create MCP server with model testing tools."""
    server = FastMCP("model-test-server")
    
    @server.tool
    def test_property_creation(
        street: str,
        city: str,
        state: str,
        zip_code: str,
        price: float,
        bedrooms: int
    ) -> dict:
        """Test creating a property model."""
        try:
            addr = Address(
                street=street,
                city=city,
                state=state,
                zip_code=zip_code,
                location=GeoLocation(lat=30.2672, lon=-97.7431)
            )
            
            prop = Property(
                id="test-1",
                listing_id="MLS123",
                property_type=PropertyType.single_family,
                price=price,
                bedrooms=bedrooms,
                bathrooms=2.5,
                address=addr,
                features=["garage", "pool"]
            )
            
            return {
                "success": True,
                "property_id": prop.id,
                "display_address": prop.get_display_address(),
                "summary": prop.get_summary()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @server.tool
    def test_search_filters(
        min_price: float,
        max_price: float,
        min_bedrooms: int
    ) -> dict:
        """Test search filter models."""
        try:
            price_range = PriceRange(
                min_price=min_price,
                max_price=max_price
            )
            
            filters = SearchFilters(
                price_range=price_range,
                min_bedrooms=min_bedrooms,
                cities=["Austin", "Dallas"]
            )
            
            query = filters.to_elasticsearch_query()
            
            return {
                "success": True,
                "has_filters": len(query.get("filter", [])) > 0,
                "filter_count": len(query.get("filter", []))
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @server.tool
    def test_enrichment_models(location_name: str) -> dict:
        """Test enrichment model creation."""
        try:
            wiki = WikipediaContext(
                wikipedia_title=f"{location_name}, Texas",
                wikipedia_url=f"https://en.wikipedia.org/wiki/{location_name},_Texas",
                summary=f"Information about {location_name}",
                confidence_score=0.9
            )
            
            poi = POIInfo(
                name="Central Park",
                category=POICategory.recreation,
                distance_miles=1.5
            )
            
            return {
                "success": True,
                "wiki_title": wiki.wikipedia_title,
                "wiki_confidence": wiki.confidence_score,
                "poi_name": poi.name,
                "poi_distance": poi.get_display_distance()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @server.tool
    def test_analysis_models(
        property_price: float,
        annual_income: float,
        down_payment: float
    ) -> dict:
        """Test analysis model calculations."""
        try:
            # Create affordability analysis
            loan_amount = property_price - down_payment
            monthly_payment = (loan_amount * 0.065 / 12) / (1 - (1 + 0.065/12) ** -360)
            income_ratio = (monthly_payment * 12) / annual_income
            
            afford = AffordabilityAnalysis(
                property_id="test-1",
                property_price=property_price,
                annual_income=annual_income,
                down_payment=down_payment,
                down_payment_percent=(down_payment / property_price) * 100,
                loan_amount=loan_amount,
                interest_rate=6.5,
                monthly_payment=monthly_payment,
                property_tax_monthly=property_price * 0.001,
                insurance_monthly=property_price * 0.0003,
                total_monthly=monthly_payment + property_price * 0.0013,
                income_ratio=income_ratio,
                affordable=income_ratio < 0.28,
                affordability_score=max(0, min(100, (1 - income_ratio) * 100)),
                max_affordable_price=annual_income * 4,
                additional_down_needed=0,
                income_needed=annual_income
            )
            
            return {
                "success": True,
                "affordable": afford.affordable,
                "income_ratio": round(afford.income_ratio, 3),
                "affordability_score": round(afford.affordability_score, 1),
                "summary": afford.get_affordability_summary()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    return server


@pytest.mark.asyncio
async def test_property_models_via_mcp(model_test_server):
    """Test property model creation through MCP tools."""
    async with Client(model_test_server) as client:
        # Test valid property creation
        result = await client.call_tool("test_property_creation", {
            "street": "123 Main St",
            "city": "Austin",
            "state": "tx",  # Should be uppercased
            "zip_code": "78701",
            "price": 500000,
            "bedrooms": 3
        })
        
        assert result.data["success"]
        assert "Austin, TX" in result.data["display_address"]
        assert "$500,000" in result.data["summary"]
        
        # Test invalid zip code
        result = await client.call_tool("test_property_creation", {
            "street": "456 Oak St",
            "city": "Dallas",
            "state": "TX",
            "zip_code": "invalid",
            "price": 400000,
            "bedrooms": 2
        })
        
        assert not result.data["success"]
        assert "error" in result.data


@pytest.mark.asyncio
async def test_search_models_via_mcp(model_test_server):
    """Test search models through MCP tools."""
    async with Client(model_test_server) as client:
        # Test valid filters
        result = await client.call_tool("test_search_filters", {
            "min_price": 200000,
            "max_price": 500000,
            "min_bedrooms": 2
        })
        
        assert result.data["success"]
        assert result.data["has_filters"]
        assert result.data["filter_count"] > 0
        
        # Test invalid price range (max < min)
        result = await client.call_tool("test_search_filters", {
            "min_price": 500000,
            "max_price": 200000,
            "min_bedrooms": 2
        })
        
        assert not result.data["success"]
        assert "must be greater than min_price" in result.data["error"]


@pytest.mark.asyncio
async def test_enrichment_models_via_mcp(model_test_server):
    """Test enrichment models through MCP tools."""
    async with Client(model_test_server) as client:
        result = await client.call_tool("test_enrichment_models", {
            "location_name": "Austin"
        })
        
        assert result.data["success"]
        assert result.data["wiki_title"] == "Austin, Texas"
        assert result.data["wiki_confidence"] == 0.9
        assert result.data["poi_name"] == "Central Park"
        assert "1.5 miles" in result.data["poi_distance"]


@pytest.mark.asyncio
async def test_analysis_models_via_mcp(model_test_server):
    """Test analysis models through MCP tools."""
    async with Client(model_test_server) as client:
        # Test affordable scenario
        result = await client.call_tool("test_analysis_models", {
            "property_price": 400000,
            "annual_income": 120000,
            "down_payment": 80000
        })
        
        assert result.data["success"]
        assert result.data["affordable"]
        assert result.data["income_ratio"] < 0.28
        assert "Affordable" in result.data["summary"]
        
        # Test unaffordable scenario
        result = await client.call_tool("test_analysis_models", {
            "property_price": 800000,
            "annual_income": 80000,
            "down_payment": 40000
        })
        
        assert result.data["success"]
        assert not result.data["affordable"]
        assert result.data["income_ratio"] > 0.28


@pytest.mark.asyncio
async def test_model_validation():
    """Test model validation rules via MCP."""
    server = FastMCP("validation-test")
    
    @server.tool
    def validate_geo_location(lat: float, lon: float) -> dict:
        """Test GeoLocation validation."""
        try:
            loc = GeoLocation(lat=lat, lon=lon)
            return {"valid": True, "lat": loc.lat, "lon": loc.lon}
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    @server.tool
    def validate_property_type(type_string: str) -> dict:
        """Test PropertyType enum validation."""
        try:
            prop_type = PropertyType(type_string)
            return {"valid": True, "type": prop_type.value}
        except Exception:
            return {"valid": False, "allowed": [t.value for t in PropertyType]}
    
    async with Client(server) as client:
        # Test valid coordinates
        result = await client.call_tool("validate_geo_location", {
            "lat": 30.2672,
            "lon": -97.7431
        })
        assert result.data["valid"]
        
        # Test invalid latitude
        result = await client.call_tool("validate_geo_location", {
            "lat": 91,  # > 90
            "lon": 0
        })
        assert not result.data["valid"]
        
        # Test valid property type
        result = await client.call_tool("validate_property_type", {
            "type_string": "condo"
        })
        assert result.data["valid"]
        
        # Test invalid property type
        result = await client.call_tool("validate_property_type", {
            "type_string": "castle"
        })
        assert not result.data["valid"]
        assert "single_family" in result.data["allowed"]


@pytest.mark.asyncio
async def test_model_serialization():
    """Test model serialization through MCP."""
    server = FastMCP("serialization-test")
    
    @server.tool
    def serialize_property() -> dict:
        """Test property serialization."""
        prop = Property(
            id="test-1",
            listing_id="MLS123",
            property_type=PropertyType.condo,
            price=350000,
            bedrooms=2,
            bathrooms=2,
            address=Address(
                street="789 Park Ave",
                city="Houston",
                state="TX",
                zip_code="77001"
            )
        )
        
        # Test different serialization modes
        return {
            "json_mode": prop.model_dump(mode='json'),
            "python_mode": prop.model_dump(mode='python'),
            "has_datetime": isinstance(prop.last_updated, datetime)
        }
    
    async with Client(server) as client:
        result = await client.call_tool("serialize_property", {})
        
        assert "json_mode" in result.data
        assert "python_mode" in result.data
        assert result.data["has_datetime"]
        
        # Check JSON serialization worked
        json_data = result.data["json_mode"]
        assert json_data["id"] == "test-1"
        assert json_data["price"] == 350000


def test_pydantic_only():
    """Ensure all models use Pydantic and no Marshmallow."""
    from pydantic import BaseModel
    
    # List of all model classes
    model_classes = [
        GeoLocation, Address, Property, PropertyHit,
        PriceRange, SearchFilters, PropertySearchParams,
        WikipediaContext, POIInfo, NeighborhoodContext,
        MarketPosition, InvestmentMetrics, PropertyAnalysis,
        AffordabilityAnalysis
    ]
    
    for model_class in model_classes:
        assert issubclass(model_class, BaseModel), f"{model_class.__name__} not Pydantic"
    
    # Check no marshmallow imports in models directory
    import os
    models_dir = Path(__file__).parent / "models"
    
    for filename in os.listdir(models_dir):
        if filename.endswith(".py"):
            filepath = models_dir / filename
            with open(filepath) as f:
                lines = f.readlines()
            
            for line in lines:
                if not line.strip().startswith("#"):
                    assert "marshmallow" not in line.lower(), f"Marshmallow in {filename}"


if __name__ == "__main__":
    print("Running FastMCP model tests...")
    
    # Create test server
    server = model_test_server()
    
    # Run async tests
    asyncio.run(test_property_models_via_mcp(server))
    print("✓ Property models")
    
    asyncio.run(test_search_models_via_mcp(server))
    print("✓ Search models")
    
    asyncio.run(test_enrichment_models_via_mcp(server))
    print("✓ Enrichment models")
    
    asyncio.run(test_analysis_models_via_mcp(server))
    print("✓ Analysis models")
    
    asyncio.run(test_model_validation())
    print("✓ Model validation")
    
    asyncio.run(test_model_serialization())
    print("✓ Model serialization")
    
    # Run sync tests
    test_pydantic_only()
    print("✓ Pydantic-only verification")
    
    print("\n✅ All model tests passed!")