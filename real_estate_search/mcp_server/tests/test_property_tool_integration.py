"""
Integration test for property search tool using search_service directly.
This test MUST fail initially as we haven't updated the implementation yet.
"""

import pytest
from unittest.mock import Mock, patch
from real_estate_search.search_service.models import PropertySearchRequest, PropertySearchResponse, PropertyResult, PropertyAddress
from real_estate_search.search_service.properties import PropertySearchService


@pytest.mark.asyncio
async def test_property_tool_uses_search_service_directly():
    """Test that MCP property tool uses search_service models and service directly."""
    
    # This test expects the property tool to:
    # 1. Import from search_service.models (not mcp_server.models)
    # 2. Use PropertySearchService from search_service (not mcp_server.services)
    # 3. Return PropertySearchResponse.model_dump() directly
    
    from real_estate_search.mcp_server.tools import property_tools
    
    # Create mock context with search_service
    mock_property_service = Mock(spec=PropertySearchService)
    mock_response = PropertySearchResponse(
        results=[
            PropertyResult(
                listing_id="123",
                property_type="single_family",
                price=1000000.0,
                bedrooms=3,
                bathrooms=2.0,
                square_feet=1200,
                address=PropertyAddress(
                    street="123 Main St",
                    city="San Francisco",
                    state="CA",
                    zip_code="94102"
                ),
                description="Test property",
                score=0.95
            )
        ],
        total_hits=1,
        execution_time_ms=100
    )
    mock_property_service.search.return_value = mock_response
    
    context = Mock()
    context.get.return_value = mock_property_service
    
    # Call the tool
    result = await property_tools.search_properties(
        context=context,
        query="San Francisco",
        search_type="text",
        size=10
    )
    
    # Verify it returns search_service response format directly
    assert "results" in result
    assert "total_hits" in result
    assert "execution_time_ms" in result
    
    # Verify the service was called with search_service models
    mock_property_service.search.assert_called_once()
    call_args = mock_property_service.search.call_args[0][0]
    assert isinstance(call_args, PropertySearchRequest)
    assert call_args.query == "San Francisco"
    
    # Verify no transformation - should be direct model_dump()
    assert result == mock_response.model_dump()


@pytest.mark.asyncio
async def test_property_tool_no_adapters_or_transformations():
    """Verify there are no adapter functions or transformations."""
    
    from real_estate_search.mcp_server.tools import property_tools
    
    # Check that module doesn't have adapter functions
    module_attrs = dir(property_tools)
    
    # These should NOT exist
    assert "adapter" not in str(module_attrs).lower()
    assert "convert" not in str(module_attrs).lower()
    assert "transform" not in str(module_attrs).lower()
    assert "MCPToSearchServiceAdapter" not in module_attrs
    assert "SearchServiceToMCPAdapter" not in module_attrs