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
        params = request.model_dump(exclude_none=True, mode='json')
        
        # The search_properties tool only accepts query, size, and include_location_extraction
        # So we only pass those parameters
        search_params = {
            'query': params.get('query'),
            'size': params.get('size', 10)
        }
        
        # Always use search_properties_with_filters tool
        response = await self.mcp_client.call_tool("search_properties_with_filters", search_params)
        
        if not response.success:
            raise Exception(f"Property search failed: {response.error}")
        
        # Transform response from search_service format to demo format
        response_data = response.data
        
        # The search_service returns 'results' but demos expect 'properties'
        if "results" in response_data:
            # Direct mapping - no need to create intermediate objects
            properties = []
            for result in response_data["results"]:
                # Map result directly to expected format
                property_dict = {
                    "listing_id": result["listing_id"],
                    "property_type": result["property_type"],
                    "price": result["price"],
                    "bedrooms": result["bedrooms"],
                    "bathrooms": result["bathrooms"],
                    "square_feet": result.get("square_feet"),
                    "address": {
                        "street": result["address"]["street"],
                        "city": result["address"]["city"],
                        "state": result["address"]["state"],
                        "zip_code": result["address"]["zip_code"]
                    },
                    "description": result["description"],
                    "features": result.get("features", []),
                    "score": result["score"]
                }
                properties.append(property_dict)
            
            # Build response with mapped data
            response_dict = {
                "properties": properties,
                "total_results": response_data.get("total_hits", 0),
                "returned_results": len(properties),
                "execution_time_ms": response_data.get("execution_time_ms", 0),
                "query": params.get('query', ''),
                "location_extracted": None
            }
            return PropertySearchResponse(**response_dict)
        
        # Already in correct format
        return PropertySearchResponse(**response_data)
    
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
        response = await self.mcp_client.call_tool("search_wikipedia", params)
        
        if not response.success:
            raise Exception(f"Wikipedia search failed: {response.error}")
        
        # Transform response from search_service format to demo format
        response_data = response.data
        
        # The search_service returns 'results' but demos expect 'articles'
        # and 'total_hits' but demos expect 'total_results'
        if "results" in response_data:
            # Transform to expected format
            articles = response_data.get("results", [])
            transformed_response = {
                "articles": articles,
                "total_results": response_data.get("total_hits", 0),
                "returned_results": len(articles),
                "execution_time_ms": response_data.get("execution_time_ms", 0),
                "query": params.get("query", ""),
                "search_in": response_data.get("search_in", params.get("search_in", "full")),
                "search_type": response_data.get("search_type", "hybrid")
            }
            return WikipediaSearchResponse(**transformed_response)
        
        # Already in correct format
        return WikipediaSearchResponse(**response_data)
    
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
        response = await self.mcp_client.call_tool("search_wikipedia_by_location", params)
        
        if not response.success:
            raise Exception(f"Location-based Wikipedia search failed: {response.error}")
        
        # The server returns the response in the correct format already
        # with 'articles', 'total_results', 'returned_results', and 'execution_time_ms'
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
        response = await self.mcp_client.call_tool("get_property_details", params)
        
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
        response = await self.mcp_client.call_tool("health_check", {})
        
        if not response.success:
            raise Exception(f"Health check failed: {response.error}")
        
        # Parse and validate response with Pydantic
        return HealthCheckResponse(**response.data)
    
    async def search_properties_hybrid(
        self,
        query: str,
        size: int = 10,
        include_location_extraction: bool = False
    ) -> Dict[str, Any]:
        """Search for properties using hybrid search with location understanding.
        
        Args:
            query: Natural language property search query
            size: Number of results to return (1-50, default 10)
            include_location_extraction: Include location extraction details (not used)
            
        Returns:
            Dictionary with hybrid search results and metadata
            
        Raises:
            Exception: If the MCP call fails
        """
        params = {
            "query": query,
            "size": size
            # include_location_extraction is not supported by the new API
        }
        
        # Call the MCP tool
        response = await self.mcp_client.call_tool("search_properties_with_filters", params)
        
        if not response.success:
            raise Exception(f"Hybrid search failed: {response.error}")
        
        # Transform response from search_service format to hybrid format
        response_data = response.data
        
        if "results" in response_data:
            # Direct mapping without intermediate objects
            properties = [{
                "listing_id": result["listing_id"],
                "property_type": result["property_type"],
                "price": result["price"],
                "bedrooms": result["bedrooms"],
                "bathrooms": result["bathrooms"],
                "square_feet": result.get("square_feet"),
                "address": {
                    "street": result["address"]["street"],
                    "city": result["address"]["city"],
                    "state": result["address"]["state"],
                    "zip_code": result["address"]["zip_code"]
                },
                "description": result["description"],
                "features": result.get("features", []),
                "score": result["score"]
            } for result in response_data["results"]]
            
            # Return transformed response
            return {
                "properties": properties,
                "total_results": response_data.get("total_hits", 0),
                "returned_results": len(properties),
                "execution_time_ms": response_data.get("execution_time_ms", 0),
                "query": query,
                "location_extracted": None
            }
        
        return response_data
    
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generic tool calling method for flexibility.
        
        Args:
            tool_name: Name of the MCP tool to call
            params: Parameters to pass to the tool
            
        Returns:
            Tool response data
            
        Raises:
            Exception: If the MCP call fails
        """
        response = await self.mcp_client.call_tool(tool_name, params)
        
        if not response.success:
            raise Exception(f"Tool {tool_name} failed: {response.error}")
        
        return response.data
    
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