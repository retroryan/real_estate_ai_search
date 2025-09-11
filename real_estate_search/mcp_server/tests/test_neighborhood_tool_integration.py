"""
Integration test for neighborhood search tool using search_service directly.
This test verifies the MCP integration without importing heavy dependencies.
"""

import os
import pytest


def test_neighborhood_tool_uses_search_service_directly():
    """Test that MCP neighborhood tool imports from search_service directly."""
    
    # Check the source code of neighborhood_tools to verify correct imports
    neighborhood_tools_file = "real_estate_search/mcp_server/tools/neighborhood_tools.py"
    
    # Verify the file exists
    assert os.path.exists(neighborhood_tools_file), "neighborhood_tools.py should exist"
    
    # Read the source code
    with open(neighborhood_tools_file, 'r') as f:
        source = f.read()
    
    # Check for correct imports from search_service
    assert "from ...search_service.models import" in source, \
        "Should import from search_service.models"
    assert "from ...search_service.neighborhoods import NeighborhoodSearchService" in source, \
        "Should import NeighborhoodSearchService from search_service"
    
    # Check that it doesn't import from old MCP models
    assert "from ..models" not in source, \
        "Should not import from mcp_server.models"
    assert "from ..services" not in source, \
        "Should not import from mcp_server.services"


def test_neighborhood_tool_direct_service_usage():
    """Verify there are no adapter functions or transformations."""
    
    neighborhood_tools_file = "real_estate_search/mcp_server/tools/neighborhood_tools.py"
    
    # Read the source code
    with open(neighborhood_tools_file, 'r') as f:
        source = f.read()
    
    # These patterns should NOT exist in the source
    assert "def convert_" not in source, "Should not have convert_ functions"
    assert "def transform_" not in source, "Should not have transform_ functions"
    assert "Adapter" not in source, "Should not have Adapter classes"
    assert "MCPToSearchService" not in source, "Should not have MCP to SearchService adapters"
    assert "SearchServiceToMCP" not in source, "Should not have SearchService to MCP adapters"