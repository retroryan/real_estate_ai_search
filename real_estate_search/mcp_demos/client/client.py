"""MCP Client for Real Estate Search demos.

This module provides a clean, Pydantic-based client for interacting with the MCP server.
It uses the FastMCP client under the hood and provides convenience methods for common operations.
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path

from pydantic import BaseModel, Field, ConfigDict

from .client_factory import create_stdio_client, create_client_from_config, ConfiguredMCPClient
from ..utils.models import (
    PropertySearchRequest,
    PropertySearchResponse,
    WikipediaSearchRequest,
    WikipediaSearchResponse,
    HealthCheckResponse,
    ServiceHealth,
    HealthStatus
)
from ..utils.mcp_utils import MCPResponse


class RealEstateSearchClient(BaseModel):
    """High-level client for Real Estate Search MCP operations.
    
    This client provides typed, async methods for all MCP tools with proper
    Pydantic model validation for requests and responses.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    mcp_client: ConfiguredMCPClient = Field(exclude=True)
    
    async def search_properties(self, request: PropertySearchRequest) -> PropertySearchResponse:
        """Search for properties using the MCP server.
        
        Args:
            request: Pydantic model with search parameters
            
        Returns:
            PropertySearchResponse with results
            
        Raises:
            Exception: If the MCP call fails
        """
        # Convert request to dict for MCP tool call
        params = request.model_dump(exclude_none=True)
        
        # Call the MCP tool
        response = await self.mcp_client.call_tool("search_properties_tool", params)
        
        if not response.success:
            raise Exception(f"Property search failed: {response.error}")
        
        # Parse and validate response with Pydantic
        return PropertySearchResponse(**response.data)
    
    async def search_wikipedia(self, request: WikipediaSearchRequest) -> WikipediaSearchResponse:
        """Search Wikipedia articles using the MCP server.
        
        Args:
            request: Pydantic model with search parameters
            
        Returns:
            WikipediaSearchResponse with results
            
        Raises:
            Exception: If the MCP call fails
        """
        # Convert request to dict for MCP tool call
        params = request.model_dump(exclude_none=True)
        
        # Call the MCP tool
        response = await self.mcp_client.call_tool("search_wikipedia_tool", params)
        
        if not response.success:
            raise Exception(f"Wikipedia search failed: {response.error}")
        
        # Parse and validate response with Pydantic
        return WikipediaSearchResponse(**response.data)
    
    async def search_wikipedia_by_location(
        self,
        city: str,
        state: Optional[str] = None,
        query: Optional[str] = None,
        size: int = 10
    ) -> Dict[str, Any]:
        """Search Wikipedia articles by location.
        
        Args:
            city: City to search in
            state: Optional state code
            query: Optional additional search terms
            size: Number of results to return
            
        Returns:
            Dictionary with location-based search results
            
        Raises:
            Exception: If the MCP call fails
        """
        params = {
            "city": city,
            "size": size
        }
        if state:
            params["state"] = state
        if query:
            params["query"] = query
        
        # Call the MCP tool
        response = await self.mcp_client.call_tool("search_wikipedia_by_location_tool", params)
        
        if not response.success:
            raise Exception(f"Location-based Wikipedia search failed: {response.error}")
        
        return response.data
    
    async def get_property_details(self, listing_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific property.
        
        Args:
            listing_id: The property listing ID
            
        Returns:
            Dictionary with property details
            
        Raises:
            Exception: If the MCP call fails
        """
        params = {"listing_id": listing_id}
        
        # Call the MCP tool
        response = await self.mcp_client.call_tool("get_property_details_tool", params)
        
        if not response.success:
            raise Exception(f"Failed to get property details: {response.error}")
        
        return response.data
    
    async def health_check(self) -> HealthCheckResponse:
        """Check the health status of the MCP server and its services.
        
        Returns:
            HealthCheckResponse with service status
            
        Raises:
            Exception: If the health check fails
        """
        # Call the MCP tool
        response = await self.mcp_client.call_tool("health_check_tool", {})
        
        if not response.success:
            raise Exception(f"Health check failed: {response.error}")
        
        # Parse and validate response with Pydantic
        return HealthCheckResponse(**response.data)
    
    async def list_tools(self) -> list[str]:
        """List all available MCP tools.
        
        Returns:
            List of tool names
        """
        return await self.mcp_client.list_tools()


# Global client instance
_client_instance: Optional[RealEstateSearchClient] = None


def get_mcp_client() -> RealEstateSearchClient:
    """Get or create the global MCP client instance.
    
    This function returns a singleton client instance. If MCP_CONFIG_PATH is set,
    it will use that configuration file, otherwise defaults to stdio transport.
    
    Returns:
        RealEstateSearchClient ready for use
    """
    global _client_instance
    
    if _client_instance is None:
        # Check for custom config path from environment
        config_path = os.getenv('MCP_CONFIG_PATH')
        
        if config_path:
            # Use the specified config file
            mcp_client = create_client_from_config(config_path=Path(config_path))
        else:
            # Default to consolidated config file (HTTP transport)
            default_config = Path(__file__).parent.parent / "config.yaml"
            mcp_client = create_client_from_config(config_path=default_config)
        
        # Wrap it in our high-level client
        _client_instance = RealEstateSearchClient(mcp_client=mcp_client)
    
    return _client_instance


def create_custom_client(
    server_path: Optional[Path] = None,
    config_path: Optional[Path] = None
) -> RealEstateSearchClient:
    """Create a custom MCP client with specific configuration.
    
    Args:
        server_path: Optional path to MCP server script
        config_path: Optional path to YAML configuration file
        
    Returns:
        RealEstateSearchClient with custom configuration
    """
    if config_path:
        from .client_factory import create_client_from_config
        mcp_client = create_client_from_config(config_path=config_path)
    else:
        mcp_client = create_stdio_client(server_path=server_path)
    
    return RealEstateSearchClient(mcp_client=mcp_client)