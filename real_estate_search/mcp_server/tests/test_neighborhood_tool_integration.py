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
        results=[
            NeighborhoodResult(
                name="Mission District",
                city="San Francisco", 
                state="CA",
                description="Vibrant neighborhood",
                score=0.92
            )
        ],
        total_hits=1,
        execution_time_ms=85,
        statistics=NeighborhoodStatistics(
            total_properties=500,
            avg_price=1200000.0,
            avg_bedrooms=2.5,
            avg_square_feet=1800.0,
            property_types={"House": 300, "Condo": 150, "Townhouse": 50}
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
        include_related_properties=True,
        include_related_wikipedia=True,
        size=10
    )
    
    # Verify it returns search_service response format directly
    assert "results" in result
    assert "total_hits" in result
    assert "execution_time_ms" in result
    
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