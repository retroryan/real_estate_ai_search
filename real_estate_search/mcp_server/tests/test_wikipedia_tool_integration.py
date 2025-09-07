"""
Integration test for Wikipedia search tool using search_service directly.
This test MUST fail initially as we haven't updated the implementation yet.
"""

import pytest
from unittest.mock import Mock
from real_estate_search.search_service.models import WikipediaSearchRequest, WikipediaSearchResponse, WikipediaResult, WikipediaSearchType
from real_estate_search.search_service.wikipedia import WikipediaSearchService


@pytest.mark.asyncio
async def test_wikipedia_tool_uses_search_service_directly():
    """Test that MCP Wikipedia tool uses search_service models and service directly."""
    
    # This test expects the Wikipedia tool to:
    # 1. Import from search_service.models (not mcp_server.models)
    # 2. Use WikipediaSearchService from search_service (not mcp_server.services)
    # 3. Return WikipediaSearchResponse.model_dump() directly
    
    from real_estate_search.mcp_server.tools import wikipedia_tools
    
    # Create mock context with search_service
    mock_wikipedia_service = Mock(spec=WikipediaSearchService)
    mock_response = WikipediaSearchResponse(
        results=[
            WikipediaResult(
                page_id="2139218",
                title="San Francisco",
                url="https://en.wikipedia.org/wiki/San_Francisco",
                summary="San Francisco is a city in California",
                categories=["Cities in California"],
                content_length=25000,
                score=0.89
            )
        ],
        total_hits=1,
        execution_time_ms=120,
        search_type=WikipediaSearchType.FULL_TEXT
    )
    mock_wikipedia_service.search.return_value = mock_response
    
    context = Mock()
    context.get.return_value = mock_wikipedia_service
    
    # Call the tool
    result = await wikipedia_tools.search_wikipedia(
        context=context,
        query="San Francisco",
        search_in="full",
        search_type="hybrid",
        size=10
    )
    
    # Verify it returns search_service response format directly
    assert "results" in result
    assert "total_hits" in result
    assert "execution_time_ms" in result
    assert "search_type" in result
    
    # Verify the service was called with search_service models
    mock_wikipedia_service.search.assert_called_once()
    call_args = mock_wikipedia_service.search.call_args[0][0]
    assert isinstance(call_args, WikipediaSearchRequest)
    assert call_args.query == "San Francisco"
    
    # Verify no transformation - should be direct model_dump()
    assert result == mock_response.model_dump()


@pytest.mark.asyncio
async def test_wikipedia_tool_no_duplicate_models():
    """Verify Wikipedia tool doesn't use MCP server models."""
    
    # This should fail if the tool is still importing from mcp_server.models
    import importlib
    import sys
    
    # Remove any cached imports
    modules_to_remove = [m for m in sys.modules if 'mcp_server.models.wikipedia' in m]
    for m in modules_to_remove:
        del sys.modules[m]
    
    # Import the tool
    from real_estate_search.mcp_server.tools import wikipedia_tools
    
    # Check imports - should NOT have mcp_server.models
    import inspect
    source = inspect.getsource(wikipedia_tools)
    
    assert "from ..models.wikipedia" not in source
    assert "from real_estate_search.mcp_server.models" not in source
    assert "from ...search_service.models import" in source or "from real_estate_search.search_service.models import" in source