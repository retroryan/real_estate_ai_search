"""
Test to verify MCP duplicate services are deleted.
This test MUST fail initially as we haven't deleted the duplicate services yet.
"""

import os
import pytest
import importlib
import sys


def test_mcp_duplicate_services_deleted():
    """Verify MCP duplicate service files are deleted."""
    
    mcp_services_dir = "real_estate_search/mcp_server/services"
    
    # These duplicate service files should NOT exist after deletion
    files_that_should_not_exist = [
        os.path.join(mcp_services_dir, "property_search.py"),
        os.path.join(mcp_services_dir, "wikipedia_search.py"),
    ]
    
    # These files should still exist (not duplicates)
    files_that_should_exist = [
        os.path.join(mcp_services_dir, "elasticsearch_client.py"),  # Keep - connection management
        os.path.join(mcp_services_dir, "health_check.py"),  # Keep - health monitoring
    ]
    
    for file_path in files_that_should_not_exist:
        assert not os.path.exists(file_path), f"Duplicate service file still exists: {file_path}"
    
    for file_path in files_that_should_exist:
        assert os.path.exists(file_path), f"Required service file missing: {file_path}"


def test_only_search_service_used():
    """Verify only search_service implementations are used."""
    
    # Clear cached imports
    for module in list(sys.modules.keys()):
        if 'mcp_server' in module:
            del sys.modules[module]
    
    # These imports should fail
    with pytest.raises(ImportError):
        from real_estate_search.mcp_server.services.property_search import PropertySearchService
    
    with pytest.raises(ImportError):
        from real_estate_search.mcp_server.services.wikipedia_search import WikipediaSearchService
    
    # These imports should succeed
    from real_estate_search.search_service.properties import PropertySearchService
    from real_estate_search.search_service.wikipedia import WikipediaSearchService
    from real_estate_search.search_service.neighborhoods import NeighborhoodSearchService
    
    assert PropertySearchService is not None
    assert WikipediaSearchService is not None
    assert NeighborhoodSearchService is not None


def test_main_server_uses_search_service():
    """Verify main.py uses search_service directly."""
    
    # Read main.py source
    main_path = "real_estate_search/mcp_server/main.py"
    
    if os.path.exists(main_path):
        with open(main_path, 'r') as f:
            source = f.read()
        
        # Check for correct imports
        assert ("from real_estate_search.search_service.properties import PropertySearchService" in source or
                "from ..search_service.properties import PropertySearchService" in source), \
                "main.py doesn't import PropertySearchService from search_service"
        
        assert ("from real_estate_search.search_service.wikipedia import WikipediaSearchService" in source or
                "from ..search_service.wikipedia import WikipediaSearchService" in source), \
                "main.py doesn't import WikipediaSearchService from search_service"
        
        # Check for wrong imports
        assert "from .services.property_search import" not in source, \
            "main.py still imports from MCP property_search service"
        assert "from .services.wikipedia_search import" not in source, \
            "main.py still imports from MCP wikipedia_search service"


def test_no_service_wrappers_or_adapters():
    """Verify there are no wrapper services or adapter layers."""
    
    # Check tools don't have service wrappers
    tools_dir = "real_estate_search/mcp_server/tools"
    
    if os.path.exists(tools_dir):
        for filename in os.listdir(tools_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                filepath = os.path.join(tools_dir, filename)
                with open(filepath, 'r') as f:
                    source = f.read()
                
                # Check for wrapper/adapter patterns
                assert "ServiceWrapper" not in source, f"{filename} contains wrapper class"
                assert "ServiceAdapter" not in source, f"{filename} contains adapter class"
                assert "class Enhanced" not in source, f"{filename} contains Enhanced class"
                assert "class Improved" not in source, f"{filename} contains Improved class"