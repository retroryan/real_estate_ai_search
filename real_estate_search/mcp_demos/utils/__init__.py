"""Utility modules for MCP demos."""

from .mcp_utils import (
    MCPResponse,
    MCPClientWrapper,
    create_mcp_client
)

from .models import (
    PropertySearchRequest,
    PropertySearchResponse,
    Property,
    Address,
    WikipediaSearchRequest,
    WikipediaSearchResponse,
    WikipediaArticle,
    HealthCheckResponse,
    ServiceHealth,
    HealthStatus,
    MCPError,
    SearchType,
    PropertyType,
    DemoResult
)

__all__ = [
    # MCP utilities
    'MCPResponse',
    'MCPClientWrapper',
    'create_mcp_client',
    
    # Models
    'PropertySearchRequest',
    'PropertySearchResponse',
    'Property',
    'Address',
    'WikipediaSearchRequest',
    'WikipediaSearchResponse',
    'WikipediaArticle',
    'HealthCheckResponse',
    'ServiceHealth',
    'HealthStatus',
    'MCPError',
    'SearchType',
    'PropertyType',
    'DemoResult'
]