"""MCP Demo queries for Real Estate Search application."""

# Export main client interfaces
from .client import (
    create_stdio_client,
    create_client_from_config,
    create_http_client,
    ConfiguredMCPClient
)

# Export demo functions
from .demos import (
    demo_basic_property_search,
    demo_property_filter,
    demo_wikipedia_search,
    demo_wikipedia_location_context
)

__all__ = [
    # Client functions
    'create_stdio_client',
    'create_client_from_config', 
    'create_http_client',
    'ConfiguredMCPClient',
    # Demo functions
    'demo_basic_property_search',
    'demo_property_filter',
    'demo_wikipedia_search',
    'demo_wikipedia_location_context'
]