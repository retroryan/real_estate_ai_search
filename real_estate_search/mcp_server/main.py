"""Main MCP server application."""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from fastmcp import FastMCP, Context

# Handle both module and script execution
if __name__ == "__main__" and __package__ is None:
    # Running as script, add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from real_estate_search.mcp_server.config.settings import MCPServerConfig
    from real_estate_search.mcp_server.services.elasticsearch_client import ElasticsearchClient
    from real_estate_search.mcp_server.services.embedding_service import EmbeddingService
    from real_estate_search.mcp_server.services.property_search import PropertySearchService
    from real_estate_search.mcp_server.services.wikipedia_search import WikipediaSearchService
    from real_estate_search.mcp_server.services.health_check import HealthCheckService
    from real_estate_search.mcp_server.utils.logging import setup_logging, get_logger
    from real_estate_search.mcp_server.tools.property_tools import search_properties, get_property_details
    from real_estate_search.mcp_server.tools.wikipedia_tools import search_wikipedia, get_wikipedia_article, search_wikipedia_by_location
else:
    # Running as module
    from .config.settings import MCPServerConfig
    from .services.elasticsearch_client import ElasticsearchClient
    from .services.embedding_service import EmbeddingService
    from .services.property_search import PropertySearchService
    from .services.wikipedia_search import WikipediaSearchService
    from .services.health_check import HealthCheckService
    from .utils.logging import setup_logging, get_logger
    from .tools.property_tools import search_properties, get_property_details
    from .tools.wikipedia_tools import search_wikipedia, get_wikipedia_article, search_wikipedia_by_location


logger = get_logger(__name__)


class MCPServer:
    """Real Estate Search MCP Server."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the MCP server.
        
        Args:
            config_path: Optional path to configuration file
        """
        # Load configuration
        if config_path and config_path.exists():
            self.config = MCPServerConfig.from_yaml(config_path)
        else:
            self.config = MCPServerConfig.from_env()
        
        # Setup logging
        setup_logging(self.config.logging)
        logger.info(f"Starting MCP Server {self.config.server_name} v{self.config.server_version}")
        
        # Initialize services
        self.es_client: Optional[ElasticsearchClient] = None
        self.embedding_service: Optional[EmbeddingService] = None
        self.property_search_service: Optional[PropertySearchService] = None
        self.wikipedia_search_service: Optional[WikipediaSearchService] = None
        self.health_check_service: Optional[HealthCheckService] = None
        
        # Initialize FastMCP app
        self.app = FastMCP(self.config.server_name)
        
        # Register tools
        self._register_tools()
    
    def _initialize_services(self):
        """Initialize all services."""
        logger.info("Initializing services")
        
        try:
            # Elasticsearch client
            self.es_client = ElasticsearchClient(self.config.elasticsearch)
            logger.info("Elasticsearch client initialized")
            
            # Embedding service
            self.embedding_service = EmbeddingService(self.config.embedding)
            logger.info(f"Embedding service initialized with {self.config.embedding.provider}")
            
            # Search services
            self.property_search_service = PropertySearchService(
                self.config,
                self.es_client,
                self.embedding_service
            )
            logger.info("Property search service initialized")
            
            self.wikipedia_search_service = WikipediaSearchService(
                self.config,
                self.es_client,
                self.embedding_service
            )
            logger.info("Wikipedia search service initialized")
            
            # Health check service
            self.health_check_service = HealthCheckService(
                self.config,
                self.es_client
            )
            logger.info("Health check service initialized")
            
            logger.info("All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise
    
    def _register_tools(self):
        """Register MCP tools."""
        logger.info("Registering MCP tools")
        
        # Property search tool
        @self.app.tool()
        async def search_properties_tool(
            query: str,
            property_type: str = None,
            min_price: float = None,
            max_price: float = None,
            min_bedrooms: int = None,
            max_bedrooms: int = None,
            city: str = None,
            state: str = None,
            size: int = 20,
            search_type: str = "hybrid"
        ) -> Dict[str, Any]:
            """Search for properties using natural language queries.
            
            Find properties that match your criteria using semantic search. You can describe
            what you're looking for in natural language and optionally add specific filters.
            
            Args:
                query: Natural language description (e.g., "modern home with pool near parks")
                property_type: Filter by type (House, Condo, Townhouse, etc.)
                min_price: Minimum price filter
                max_price: Maximum price filter
                min_bedrooms: Minimum bedrooms
                max_bedrooms: Maximum bedrooms
                city: Filter by city
                state: Filter by state (2-letter code like CA, NY)
                size: Number of results (1-100, default 20)
                search_type: "hybrid" (best), "semantic" (AI), or "text" (keyword)
                
            Returns:
                List of matching properties with details and relevance scores
            """
            return await search_properties(
                self._create_context(),
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
        
        # Property details tool
        @self.app.tool()
        async def get_property_details_tool(listing_id: str) -> Dict[str, Any]:
            """Get detailed information for a specific property.
            
            Args:
                listing_id: The unique property listing ID
                
            Returns:
                Complete property information including all available details
            """
            return await get_property_details(
                self._create_context(),
                listing_id=listing_id
            )
        
        # Wikipedia search tool
        @self.app.tool()
        async def search_wikipedia_tool(
            query: str,
            search_in: str = "full",
            city: str = None,
            state: str = None,
            categories: list = None,
            size: int = 10,
            search_type: str = "hybrid"
        ) -> Dict[str, Any]:
            """Search Wikipedia for location and topic information.
            
            Find information about neighborhoods, landmarks, history, and local context
            to better understand areas and locations.
            
            Args:
                query: What you're looking for (e.g., "Mission District culture", "Golden Gate Bridge")
                search_in: "full" (complete articles), "summaries" (shorter), or "chunks" (sections)
                city: Filter by city name
                state: Filter by state (2-letter code)
                categories: List of Wikipedia categories to filter by
                size: Number of results (1-50, default 10)
                search_type: "hybrid" (best), "semantic" (AI), or "text" (keyword)
                
            Returns:
                Wikipedia articles with summaries, topics, and location information
            """
            return await search_wikipedia(
                self._create_context(),
                query=query,
                search_in=search_in,
                city=city,
                state=state,
                categories=categories,
                size=size,
                search_type=search_type
            )
        
        # Wikipedia by location tool
        @self.app.tool()
        async def search_wikipedia_by_location_tool(
            city: str,
            state: str = None,
            query: str = None,
            size: int = 10
        ) -> Dict[str, Any]:
            """Find Wikipedia articles about a specific location.
            
            Discover information about neighborhoods, landmarks, attractions, and local
            context for any city or area.
            
            Args:
                city: City name to search for
                state: Optional state filter (2-letter code like CA, NY)
                query: Optional additional search terms
                size: Number of results (1-20, default 10)
                
            Returns:
                Location-specific Wikipedia articles with local information
            """
            return await search_wikipedia_by_location(
                self._create_context(),
                city=city,
                state=state,
                query=query,
                size=size
            )
        
        # Health check tool
        @self.app.tool()
        async def health_check_tool() -> Dict[str, Any]:
            """Check the health status of all system components.
            
            Returns:
                System health information including service statuses
            """
            if not self.health_check_service:
                return {"error": "Health check service not initialized"}
            
            try:
                health_response = self.health_check_service.perform_health_check()
                return {
                    "status": health_response.status,
                    "timestamp": health_response.timestamp.isoformat(),
                    "services": health_response.services,
                    "version": health_response.version
                }
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return {"error": str(e)}
        
        logger.info("MCP tools registered successfully")
    
    def _create_context(self) -> Context:
        """Create a context object with services for tools.
        
        Returns:
            Context with all services available
        """
        # Create a mock context object with our services
        class MCPContext:
            def __init__(self, services):
                self._services = services
            
            def get(self, key):
                return self._services.get(key)
        
        return MCPContext({
            "config": self.config,
            "es_client": self.es_client,
            "embedding_service": self.embedding_service,
            "property_search_service": self.property_search_service,
            "wikipedia_search_service": self.wikipedia_search_service,
            "health_check_service": self.health_check_service
        })
    
    def start(self):
        """Start the MCP server."""
        logger.info("Starting MCP server")
        
        try:
            # Initialize services
            self._initialize_services()
            
            # Perform initial health check
            health_response = self.health_check_service.perform_health_check()
            if health_response.status == "unhealthy":
                logger.error("System is unhealthy, but starting anyway")
                logger.error(f"Health check details: {health_response.services}")
            else:
                logger.info(f"System health: {health_response.status}")
            
            # Start FastMCP server (synchronous)
            logger.info(f"MCP server ready: {self.config.server_name} v{self.config.server_version}")
            self.app.run(transport="stdio")  # Use stdio transport by default
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise
    
    async def stop(self):
        """Stop the MCP server."""
        logger.info("Stopping MCP server")
        
        try:
            # Close services
            if self.es_client:
                self.es_client.close()
            
            logger.info("MCP server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping server: {e}")


def main():
    """Main entry point."""
    # Get config path from command line or use default
    config_path = None
    if len(sys.argv) > 1:
        config_path = Path(sys.argv[1])
    else:
        # Try default config locations
        default_configs = [
            Path(__file__).parent / "config" / "config.yaml",
            Path.cwd() / "config.yaml"
        ]
        for path in default_configs:
            if path.exists():
                config_path = path
                break
    
    # Create and start server
    server = MCPServer(config_path)
    
    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        # Stop is async, so we need to run it in an event loop
        asyncio.run(server.stop())


if __name__ == "__main__":
    main()