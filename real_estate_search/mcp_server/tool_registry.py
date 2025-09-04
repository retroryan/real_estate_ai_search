"""Tool registry for MCP server - separates tool registration logic."""

from typing import Dict, Any, Optional, List, Literal
from fastmcp import FastMCP
import logging

from .utils.context import ToolContext
from .utils.responses import (
    create_property_error_response,
    create_wikipedia_error_response,
    create_details_error_response
)
from .utils.tool_wrapper import with_error_handling
from .tools import property_tools, wikipedia_tools, hybrid_search_tool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Manages tool registration for the MCP server."""
    
    def __init__(self, app: FastMCP):
        """Initialize the tool registry.
        
        Args:
            app: FastMCP application instance
        """
        self.app = app
        
    def register_all_tools(self, server):
        """Register all MCP tools.
        
        Args:
            server: MCPServer instance to get context from
        """
        logger.info("Registering MCP tools")
        
        # Register each category of tools
        self._register_property_search_tools(server)
        self._register_property_detail_tools(server)
        self._register_wikipedia_tools(server)
        self._register_hybrid_search_tool(server)
        self._register_health_check_tool(server)
        
        logger.info("MCP tools registered successfully")
    
    def _register_property_search_tools(self, server):
        """Register property search tools."""
        
        @self.app.tool(
            name="search_properties_with_filters",
            description="Search properties when you have SPECIFIC filter requirements (price, bedrooms, location).",
            tags={"property", "search", "filters", "real_estate"}
        )
        @with_error_handling(
            tool_name="search_properties_with_filters",
            error_response_factory=lambda error, **kwargs: create_property_error_response(
                error, kwargs.get("query", ""), kwargs.get("search_type", "hybrid")
            )
        )
        async def search_properties_with_filters(
            query: str,
            property_type: Optional[str] = None,
            min_price: Optional[float] = None,
            max_price: Optional[float] = None,
            min_bedrooms: Optional[int] = None,
            max_bedrooms: Optional[int] = None,
            city: Optional[str] = None,
            state: Optional[str] = None,
            size: int = 20,
            search_type: Literal["hybrid", "semantic", "text"] = "hybrid"
        ) -> Dict[str, Any]:
            """Search properties with EXPLICIT filters."""
            context = ToolContext.from_server(server)
            return await property_tools.search_properties(
                context,
                query=query,
                property_type=property_type,
                min_price=min_price,
                max_price=max_price,
                min_bedrooms=min_bedrooms,
                max_bedrooms=max_bedrooms,
                city=city,
                state=state,
                size=size,
                search_type=search_type
            )
    
    def _register_property_detail_tools(self, server):
        """Register property detail tools."""
        
        @self.app.tool(
            name="get_property_details",
            description="Get detailed information for a specific property by its listing ID.",
            tags={"property", "details", "real_estate"}
        )
        @with_error_handling(
            tool_name="get_property_details",
            error_response_factory=lambda error, **kwargs: create_details_error_response(
                error, kwargs.get("listing_id", "")
            )
        )
        async def get_property_details(listing_id: str) -> Dict[str, Any]:
            """Get detailed information for a specific property."""
            context = ToolContext.from_server(server)
            return await property_tools.get_property_details(
                context,
                listing_id=listing_id
            )
        
        @self.app.tool(
            name="get_rich_property_details",
            description="Get comprehensive property listing with embedded neighborhood and Wikipedia data.",
            tags={"property", "details", "enriched", "real_estate"}
        )
        @with_error_handling(
            tool_name="get_rich_property_details",
            error_response_factory=lambda error, **kwargs: create_details_error_response(
                error, kwargs.get("listing_id", "")
            )
        )
        async def get_rich_property_details(
            listing_id: str,
            include_wikipedia: bool = True,
            include_neighborhood: bool = True,
            wikipedia_limit: int = 3
        ) -> Dict[str, Any]:
            """Get comprehensive property listing with embedded data."""
            context = ToolContext.from_server(server)
            return await property_tools.get_rich_property_details(
                context,
                listing_id=listing_id,
                include_wikipedia=include_wikipedia,
                include_neighborhood=include_neighborhood,
                wikipedia_limit=wikipedia_limit
            )
    
    def _register_wikipedia_tools(self, server):
        """Register Wikipedia search tools."""
        
        @self.app.tool(
            name="search_wikipedia",
            description="Search Wikipedia for general information about any topic or location.",
            tags={"wikipedia", "search", "knowledge"}
        )
        @with_error_handling(
            tool_name="search_wikipedia",
            error_response_factory=lambda error, **kwargs: create_wikipedia_error_response(
                error, kwargs.get("query"), kwargs.get("city")
            )
        )
        async def search_wikipedia(
            query: str,
            search_in: Literal["full", "summaries", "chunks"] = "full",
            city: Optional[str] = None,
            state: Optional[str] = None,
            categories: Optional[List[str]] = None,
            size: int = 10,
            search_type: Literal["hybrid", "semantic", "text"] = "hybrid"
        ) -> Dict[str, Any]:
            """Search Wikipedia for general information."""
            context = ToolContext.from_server(server)
            return await wikipedia_tools.search_wikipedia(
                context,
                query=query,
                search_in=search_in,
                city=city,
                state=state,
                categories=categories,
                size=size,
                search_type=search_type
            )
        
        @self.app.tool(
            name="search_wikipedia_by_location",
            description="Find Wikipedia articles about a SPECIFIC CITY or neighborhood.",
            tags={"wikipedia", "location", "city", "neighborhood"}
        )
        @with_error_handling(
            tool_name="search_wikipedia_by_location",
            error_response_factory=lambda error, **kwargs: create_wikipedia_error_response(
                error, city=kwargs.get("city")
            )
        )
        async def search_wikipedia_by_location(
            city: str,
            state: Optional[str] = None,
            query: Optional[str] = None,
            size: int = 10
        ) -> Dict[str, Any]:
            """Find Wikipedia articles about a specific location."""
            context = ToolContext.from_server(server)
            return await wikipedia_tools.search_wikipedia_by_location(
                context,
                city=city,
                state=state,
                query=query,
                size=size
            )
    
    def _register_hybrid_search_tool(self, server):
        """Register the main hybrid search tool."""
        
        @self.app.tool(
            name="search_properties",
            description="PREFERRED: Search properties using natural language queries with AI understanding.",
            tags={"property", "search", "hybrid", "ai", "real_estate", "preferred"}
        )
        @with_error_handling(
            tool_name="search_properties",
            error_response_factory=lambda error, **kwargs: create_property_error_response(
                error, kwargs.get("query", ""), "hybrid"
            )
        )
        async def search_properties(
            query: str,
            size: int = 10,
            include_location_extraction: bool = False
        ) -> Dict[str, Any]:
            """Search properties using natural language with AI understanding."""
            context = ToolContext.from_server(server)
            return await hybrid_search_tool.search_properties_hybrid(
                context,
                query=query,
                size=size,
                include_location_extraction=include_location_extraction
            )
    
    def _register_health_check_tool(self, server):
        """Register health check tool."""
        
        @self.app.tool(
            name="health_check",
            description="Check the health status of all system components.",
            tags={"system", "health", "monitoring"}
        )
        @with_error_handling(tool_name="health_check")
        async def health_check() -> Dict[str, Any]:
            """Check the health status of all system components."""
            if not server.health_check_service:
                return {"error": "Health check service not initialized", "success": False}
            
            health_response = server.health_check_service.perform_health_check()
            return {
                "status": health_response.status,
                "timestamp": health_response.timestamp.isoformat(),
                "services": health_response.services,
                "version": health_response.version,
                "success": health_response.status == "healthy"
            }