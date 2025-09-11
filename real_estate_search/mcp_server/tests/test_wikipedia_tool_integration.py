"""
Integration test for Wikipedia search tool using search_service directly.
This test verifies the MCP integration without importing heavy dependencies.
"""

import os
import pytest


def test_wikipedia_tool_uses_search_service_directly():
    """Test that MCP Wikipedia tool imports from search_service directly."""
    
    # Check the source code of wikipedia_tools to verify correct imports
    wikipedia_tools_file = "real_estate_search/mcp_server/tools/wikipedia_tools.py"
    
    # Verify the file exists
    assert os.path.exists(wikipedia_tools_file), "wikipedia_tools.py should exist"
    
    # Read the source code
    with open(wikipedia_tools_file, 'r') as f:
        source = f.read()
    
    # Check for correct imports from search_service
    assert "from ...search_service.models import" in source, \
        "Should import from search_service.models"
    assert "from ...search_service.wikipedia import WikipediaSearchService" in source, \
        "Should import WikipediaSearchService from search_service"
    
    # Check that it doesn't import from old MCP models
    assert "from ..models" not in source, \
        "Should not import from mcp_server.models"
    assert "from ..services" not in source, \
        "Should not import from mcp_server.services"


def test_wikipedia_tool_no_duplicate_models():
    """Verify there are no adapter functions or transformations."""
    
    wikipedia_tools_file = "real_estate_search/mcp_server/tools/wikipedia_tools.py"
    
    # Read the source code
    with open(wikipedia_tools_file, 'r') as f:
        source = f.read()
    
    # These patterns should NOT exist in the source
    assert "def convert_" not in source, "Should not have convert_ functions"
    assert "def transform_" not in source, "Should not have transform_ functions"
    assert "Adapter" not in source, "Should not have Adapter classes"
    assert "MCPToSearchService" not in source, "Should not have MCP to SearchService adapters"
    assert "SearchServiceToMCP" not in source, "Should not have SearchService to MCP adapters"