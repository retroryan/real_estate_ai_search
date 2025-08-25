"""
Test MCP tools implementation.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from fastmcp import FastMCP
from models import (
    Property, PropertyType, Address, GeoLocation,
    PropertySearchParams, SearchResults
)
from services import SearchEngine


async def test_tool_registration():
    """Test that all tools are properly registered."""
    from main import mcp
    
    # FastMCP stores tools internally
    # We can test by checking the server exists
    assert mcp is not None
    assert mcp.name == "real-estate-search"
    
    print("✓ MCP server with tools created")


async def test_search_properties_tool():
    """Test search properties tool directly."""
    from tools.property_tools import search_properties_tool
    from main import resources
    
    # Mock the search engine
    mock_es = AsyncMock()
    mock_es.search = AsyncMock(return_value={
        "hits": {
            "total": {"value": 2},
            "hits": [
                {
                    "_id": "prop-1",
                    "_score": 0.95,
                    "_source": {
                        "id": "prop-1",
                        "listing_id": "MLS001",
                        "property_type": "single_family",
                        "price": 450000,
                        "bedrooms": 3,
                        "bathrooms": 2.5,
                        "square_feet": 2000,
                        "address": {
                            "street": "123 Main St",
                            "city": "Austin",
                            "state": "TX",
                            "zip_code": "78701"
                        },
                        "description": "Beautiful home"
                    }
                },
                {
                    "_id": "prop-2",
                    "_score": 0.85,
                    "_source": {
                        "id": "prop-2",
                        "listing_id": "MLS002",
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
                        "description": "Modern condo"
                    }
                }
            ]
        },
        "took": 25
    })
    
    # Set up resources
    resources.es = mock_es
    resources.search_engine = SearchEngine(mock_es)
    
    # Test the tool
    result = await search_properties_tool(
        query="modern",
        location="Austin",
        min_price=300000,
        max_price=500000,
        max_results=10
    )
    
    assert result["success"]
    assert result["total"] == 2
    assert result["returned"] == 2
    assert len(result["properties"]) == 2
    assert result["properties"][0]["id"] == "prop-1"
    assert result["properties"][0]["price"] == 450000
    
    print("✓ search_properties tool works")


async def test_neighborhood_analysis_tool():
    """Test neighborhood analysis tool."""
    from tools.neighborhood_tools import analyze_neighborhood_tool
    from main import resources
    from services import LocationService, WikipediaEnrichmentService
    
    # Set up services
    resources.location_service = LocationService()
    resources.enrichment_service = WikipediaEnrichmentService()
    
    # Test the tool
    result = await analyze_neighborhood_tool(
        location="Austin, TX",
        radius_miles=2.0
    )
    
    assert result["success"]
    assert "location" in result
    assert "walkability" in result
    assert "amenities" in result
    assert result["walkability"]["score"] >= 0
    assert result["walkability"]["score"] <= 100
    
    print("✓ analyze_neighborhood tool works")


async def test_market_analysis_tool():
    """Test market analysis tool."""
    from tools.market_tools import analyze_market_trends_tool
    from main import resources
    from services import MarketAnalysisService
    
    # Mock Elasticsearch
    mock_es = AsyncMock()
    mock_es.search = AsyncMock(return_value={
        "hits": {"total": {"value": 100}, "hits": []},
        "aggregations": {
            "price_stats": {
                "avg": 450000,
                "min": 200000,
                "max": 800000
            },
            "price_percentiles": {
                "values": {"50.0": 425000}
            }
        }
    })
    
    # Set up services
    resources.es = mock_es
    resources.market_service = MarketAnalysisService(mock_es)
    
    # Test the tool
    result = await analyze_market_trends_tool(
        location="Austin, TX",
        property_type="single_family",
        time_period_days=90
    )
    
    assert result["success"]
    assert "market_trends" in result
    assert "price_distribution" in result
    assert result["location"] == "Austin, TX"
    
    print("✓ analyze_market_trends tool works")


async def test_investment_metrics_tool():
    """Test investment metrics calculation tool."""
    from tools.market_tools import calculate_investment_metrics_tool
    from main import resources
    from services import SearchEngine, MarketAnalysisService
    
    # Mock Elasticsearch
    mock_es = AsyncMock()
    mock_es.get = AsyncMock(return_value={
        "found": True,
        "_id": "prop-1",
        "_source": {
            "id": "prop-1",
            "listing_id": "MLS001",
            "property_type": "single_family",
            "price": 450000,
            "bedrooms": 3,
            "bathrooms": 2.5,
            "square_feet": 2000,
            "address": {
                "street": "123 Main St",
                "city": "Austin",
                "state": "TX",
                "zip_code": "78701"
            }
        }
    })
    
    mock_es.search = AsyncMock(return_value={
        "hits": {"total": {"value": 50}, "hits": []},
        "aggregations": {
            "price_stats": {"avg": 450000}
        }
    })
    
    # Set up services
    resources.es = mock_es
    resources.search_engine = SearchEngine(mock_es)
    resources.market_service = MarketAnalysisService(mock_es)
    
    # Test the tool
    result = await calculate_investment_metrics_tool(
        property_id="prop-1",
        down_payment_percent=20.0,
        mortgage_rate=7.0
    )
    
    assert result["success"]
    assert "financing" in result
    assert "monthly_expenses" in result
    assert "cash_flow" in result
    assert "returns" in result
    assert result["property"]["id"] == "prop-1"
    
    print("✓ calculate_investment_metrics tool works")


async def test_property_comparison_tool():
    """Test property comparison tool."""
    from tools.market_tools import compare_properties_tool
    from main import resources
    from services import SearchEngine, MarketAnalysisService
    
    # Mock Elasticsearch
    mock_es = AsyncMock()
    
    # Mock get for two properties
    def mock_get_side_effect(index, id):
        properties = {
            "prop-1": {
                "found": True,
                "_id": "prop-1",
                "_source": {
                    "id": "prop-1",
                    "listing_id": "MLS001",
                    "property_type": "single_family",
                    "price": 450000,
                    "bedrooms": 3,
                    "bathrooms": 2.5,
                    "square_feet": 2000,
                    "address": {
                        "street": "123 Main St",
                        "city": "Austin",
                        "state": "TX",
                        "zip_code": "78701"
                    }
                }
            },
            "prop-2": {
                "found": True,
                "_id": "prop-2",
                "_source": {
                    "id": "prop-2",
                    "listing_id": "MLS002",
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
                    }
                }
            }
        }
        return properties.get(id, {"found": False})
    
    mock_es.get = AsyncMock(side_effect=mock_get_side_effect)
    mock_es.search = AsyncMock(return_value={
        "hits": {"total": {"value": 50}, "hits": []},
        "aggregations": {
            "price_stats": {"avg": 400000}
        }
    })
    
    # Set up services
    resources.es = mock_es
    resources.search_engine = SearchEngine(mock_es)
    resources.market_service = MarketAnalysisService(mock_es)
    
    # Test the tool
    result = await compare_properties_tool(
        property_ids=["prop-1", "prop-2"]
    )
    
    assert result["success"]
    assert result["property_count"] == 2
    assert len(result["properties"]) == 2
    assert "analysis" in result
    assert result["analysis"]["best_value"]["property_id"] == "prop-2"
    
    print("✓ compare_properties tool works")


async def run_all_tests():
    """Run all tool tests."""
    print("Running MCP tools tests...\n")
    
    await test_tool_registration()
    await test_search_properties_tool()
    await test_neighborhood_analysis_tool()
    await test_market_analysis_tool()
    await test_investment_metrics_tool()
    await test_property_comparison_tool()
    
    print("\n✅ All tool tests passed!")


if __name__ == "__main__":
    asyncio.run(run_all_tests())