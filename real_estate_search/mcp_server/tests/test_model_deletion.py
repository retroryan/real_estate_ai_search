"""
Test to verify all MCP models are deleted and only search_service models exist.
This test MUST fail initially as we haven't deleted the duplicate models yet.
"""

import os
import pytest
import importlib
import sys


def test_mcp_models_deleted():
    """Verify all MCP model files are deleted."""
    
    mcp_models_dir = "real_estate_search/mcp_server/models"
    
    # These files should NOT exist after deletion
    files_that_should_not_exist = [
        os.path.join(mcp_models_dir, "property.py"),
        os.path.join(mcp_models_dir, "wikipedia.py"),
        os.path.join(mcp_models_dir, "search.py"),
        os.path.join(mcp_models_dir, "hybrid.py"),
        os.path.join(mcp_models_dir, "responses.py"),
    ]
    
    for file_path in files_that_should_not_exist:
        assert not os.path.exists(file_path), f"Duplicate model file still exists: {file_path}"


def test_only_search_service_models_imported():
    """Verify only search_service models are used throughout MCP server."""
    
    # Clear any cached imports
    modules_to_check = [
        'real_estate_search.mcp_server.tools.property_tools',
        'real_estate_search.mcp_server.tools.wikipedia_tools',
        'real_estate_search.mcp_server.tools.hybrid_search_tool',
    ]
    
    # Remove from cache if present
    for module in list(sys.modules.keys()):
        if module.startswith('real_estate_search.mcp_server'):
            del sys.modules[module]
    
    # Try to import MCP tools and check they don't use MCP models
    for module_name in modules_to_check:
        try:
            module = importlib.import_module(module_name)
            
            # Get the source code
            import inspect
            source = inspect.getsource(module)
            
            # Check for bad imports
            assert "from ..models." not in source, f"{module_name} still imports from MCP models"
            assert "from real_estate_search.mcp_server.models" not in source, f"{module_name} still imports from MCP models"
            
            # Check for good imports
            assert ("from real_estate_search.search_service.models" in source or
                   "from ...search_service.models" in source), f"{module_name} doesn't import from search_service.models"
                   
        except ImportError:
            # Module might not exist yet or might be renamed
            pass


def test_no_model_duplication():
    """Verify there's no duplication between MCP and search_service models."""
    
    # Import search_service models
    from real_estate_search.search_service import models as search_models
    
    # Try to import MCP models (should fail)
    with pytest.raises(ImportError):
        from real_estate_search.mcp_server.models import property
    
    with pytest.raises(ImportError):
        from real_estate_search.mcp_server.models import wikipedia
    
    with pytest.raises(ImportError):
        from real_estate_search.mcp_server.models import search
    
    # Verify search_service models exist and are complete
    assert hasattr(search_models, 'PropertySearchRequest')
    assert hasattr(search_models, 'PropertySearchResponse')
    assert hasattr(search_models, 'WikipediaSearchRequest')
    assert hasattr(search_models, 'WikipediaSearchResponse')
    assert hasattr(search_models, 'NeighborhoodSearchRequest')
    assert hasattr(search_models, 'NeighborhoodSearchResponse')