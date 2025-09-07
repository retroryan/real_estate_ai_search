"""
Integration test for neighborhood search tool using search_service directly.
This test MUST fail initially as we haven't updated the implementation yet.
"""

import pytest
from unittest.mock import Mock
from real_estate_search.search_service.models import (
    NeighborhoodSearchRequest, 
    NeighborhoodSearchResponse, 
    NeighborhoodResult,
    NeighborhoodStatistics
)
from real_estate_search.search_service.neighborhoods import NeighborhoodSearchService


@pytest.mark.asyncio
async def test_neighborhood_tool_uses_search_service_directly():
    """Test that MCP neighborhood tool uses search_service models and service directly."""
    
    # This test expects the neighborhood tool to:
    # 1. Import from search_service.models (not mcp_server.models)
    # 2. Use NeighborhoodSearchService from search_service
    # 3. Return NeighborhoodSearchResponse.model_dump() directly
    
    # Try to import - this might be in hybrid_search_tool or a new neighborhood_tools
    try:
        from real_estate_search.mcp_server.tools import neighborhood_tools
        search_func = neighborhood_tools.search_neighborhoods
    except ImportError:
        from real_estate_search.mcp_server.tools import hybrid_search_tool
        search_func = hybrid_search_tool.search_neighborhoods
    
    # Create mock context with search_service
    mock_neighborhood_service = Mock(spec=NeighborhoodSearchService)
    mock_response = NeighborhoodSearchResponse(
        neighborhoods=[
            NeighborhoodResult(
                name="Mission District",
                city="San Francisco",
                state="CA",
                population=45000,
                median_income=85000,
                description="Vibrant neighborhood"
            )
        ],
        total_hits=1,
        statistics=NeighborhoodStatistics(
            avg_price=1200000,
            median_price=1100000,
            total_properties=500,
            price_range={"min": 500000, "max": 5000000}
        ),
        request=NeighborhoodSearchRequest(
            city="San Francisco",
            state="CA",
            include_properties=True,
            include_wikipedia=True
        )
    )
    mock_neighborhood_service.search.return_value = mock_response
    
    context = Mock()
    context.get.return_value = mock_neighborhood_service
    
    # Call the tool
    result = await search_func(
        context=context,
        city="San Francisco",
        state="CA",
        include_properties=True,
        include_wikipedia=True,
        size=10
    )
    
    # Verify it returns search_service response format directly
    assert "neighborhoods" in result
    assert "total_hits" in result
    assert "property_stats" in result
    assert "request" in result
    
    # Verify the service was called with search_service models
    mock_neighborhood_service.search.assert_called_once()
    call_args = mock_neighborhood_service.search.call_args[0][0]
    assert isinstance(call_args, NeighborhoodSearchRequest)
    assert call_args.city == "San Francisco"
    assert call_args.state == "CA"
    
    # Verify no transformation - should be direct model_dump()
    assert result == mock_response.model_dump()


@pytest.mark.asyncio
async def test_neighborhood_tool_direct_service_usage():
    """Verify neighborhood tool uses search_service directly without wrappers."""
    
    # Import the appropriate module
    try:
        from real_estate_search.mcp_server.tools import neighborhood_tools as tool_module
    except ImportError:
        from real_estate_search.mcp_server.tools import hybrid_search_tool as tool_module
    
    # Check imports
    import inspect
    source = inspect.getsource(tool_module)
    
    # Should import from search_service
    assert ("from real_estate_search.search_service.neighborhoods import" in source or
            "from ...search_service.neighborhoods import" in source)
    
    # Should NOT have wrapper functions
    assert "def convert_" not in source
    assert "def transform_" not in source
    assert "Adapter" not in source