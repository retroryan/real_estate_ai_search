"""Main MCP server application."""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Literal

from fastmcp import FastMCP, Context

# Handle both module and script execution
if __name__ == "__main__" and __package__ is None:
    # Running as script, add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from real_estate_search.mcp_server.settings import MCPServerConfig
    from real_estate_search.mcp_server.services.elasticsearch_client import ElasticsearchClient
    from real_estate_search.search_service.properties import PropertySearchService
    from real_estate_search.search_service.wikipedia import WikipediaSearchService
    from real_estate_search.search_service.neighborhoods import NeighborhoodSearchService
    from real_estate_search.mcp_server.services.health_check import HealthCheckService
    from real_estate_search.mcp_server.utils.logging import setup_logging, get_logger
    from real_estate_search.mcp_server.tools import property_tools
    from real_estate_search.mcp_server.tools import wikipedia_tools
    from real_estate_search.mcp_server.tools import neighborhood_tools
else:
    # Running as module
    from .settings import MCPServerConfig
    from .services.elasticsearch_client import ElasticsearchClient
    from ..search_service.properties import PropertySearchService
    from ..search_service.wikipedia import WikipediaSearchService
    from ..search_service.neighborhoods import NeighborhoodSearchService
    from .services.health_check import HealthCheckService
    from .utils.logging import setup_logging, get_logger
    from .tools import property_tools
    from .tools import wikipedia_tools
    from .tools import neighborhood_tools


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
        self.property_search_service: Optional[PropertySearchService] = None
        self.wikipedia_search_service: Optional[WikipediaSearchService] = None
        self.neighborhood_search_service: Optional[NeighborhoodSearchService] = None
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
            
            # Search services - directly use search_service implementations
            self.property_search_service = PropertySearchService(
                es_client=self.es_client.client
            )
            logger.info("Property search service initialized")
            
            self.wikipedia_search_service = WikipediaSearchService(
                es_client=self.es_client.client
            )
            logger.info("Wikipedia search service initialized")
            
            self.neighborhood_search_service = NeighborhoodSearchService(
                es_client=self.es_client.client
            )
            logger.info("Neighborhood search service initialized")
            
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
        
        # Property search with explicit filters tool
        @self.app.tool(
            name="search_properties_with_filters",
            description="Search properties when you have SPECIFIC filter requirements (price, bedrooms, location).",
            tags={"property", "search", "filters", "real_estate"}
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
            """Search properties with EXPLICIT filters.
            
            USE THIS TOOL ONLY WHEN:
            • You have specific price ranges, bedroom counts, or property types
            • You need precise filter control
            • The user explicitly provides filter values
            
            For general natural language searches, use 'search_properties' instead.
            
            Args:
                query: Search description (can be simple since you're using filters)
                property_type: Specific type filter (House, Condo, Townhouse, etc.)
                min_price: Minimum price requirement
                max_price: Maximum price requirement
                min_bedrooms: Minimum bedrooms required
                max_bedrooms: Maximum bedrooms required
                city: Specific city filter
                state: Specific state filter (2-letter code)
                size: Number of results (1-100, default 20)
                search_type: "hybrid", "semantic", or "text"
                
            Returns:
                Properties matching your filters and query
            """
            try:
                return await property_tools.search_properties(
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
            except Exception as e:
                logger.error(f"Property search with filters failed: {e}")
                # Return standardized error response with required fields
                return {
                    "query": query,
                    "search_type": search_type,
                    "total_results": 0,
                    "returned_results": 0,
                    "execution_time_ms": 0,
                    "properties": [],
                    "error": str(e)
                }
        
        # Property details tool
        @self.app.tool(
            name="get_property_details",
            description="Get detailed information for a specific property by its listing ID.",
            tags={"property", "details", "real_estate"}
        )
        async def get_property_details(listing_id: str) -> Dict[str, Any]:
            """Get detailed information for a specific property.
            
            Args:
                listing_id: The unique property listing ID
                
            Returns:
                Complete property information including all available details
            """
            return await property_tools.get_property_details(
                self._create_context(),
                listing_id=listing_id
            )
        
        # Rich property details tool
        @self.app.tool(
            name="get_rich_property_details",
            description="Get comprehensive property listing with embedded neighborhood and Wikipedia data.",
            tags={"property", "details", "enriched", "real_estate"}
        )
        async def get_rich_property_details(
            listing_id: str,
            include_wikipedia: bool = True,
            include_neighborhood: bool = True,
            wikipedia_limit: int = 3
        ) -> Dict[str, Any]:
            """Get comprehensive property listing with embedded neighborhood and Wikipedia data.
            
            Retrieves complete property information from the denormalized property_relationships
            index in a single high-performance query. Returns all property details along with
            embedded neighborhood demographics and relevant Wikipedia articles.
            
            Args:
                listing_id: The unique property listing ID
                include_wikipedia: Include Wikipedia articles about the area (default True)
                include_neighborhood: Include detailed neighborhood information (default True)
                wikipedia_limit: Maximum Wikipedia articles to return (1-10, default 3)
                
            Returns:
                Rich property listing with embedded neighborhood and Wikipedia context
            """
            return await property_tools.get_rich_property_details(
                self._create_context(),
                listing_id=listing_id,
                include_wikipedia=include_wikipedia,
                include_neighborhood=include_neighborhood,
                wikipedia_limit=wikipedia_limit
            )
        
        # Wikipedia search tool
        @self.app.tool(
            name="search_wikipedia",
            description="Search Wikipedia for general information about any topic or location. Use for general searches when you don't have a specific city.",
            tags={"wikipedia", "search", "knowledge"}
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
            """Search Wikipedia for general information about any topic or location.
            
            Use this tool for general Wikipedia searches when you DON'T have a specific city/location,
            or when searching for concepts, history, or general topics. The query parameter is REQUIRED.
            All filter parameters are OPTIONAL - only use them if you want to narrow results.
            
            IMPORTANT: For location-specific searches where you KNOW the city name, use 
            search_wikipedia_by_location instead - it's optimized for that use case.
            
            Args:
                query: REQUIRED - What to search for (e.g., "Oakland culture", "California history", "Victorian architecture")
                search_in: OPTIONAL - Search scope: "full" (default, complete articles), "summaries" (shorter), or "chunks" (sections)
                city: OPTIONAL - Filter results to this city (only if you want to filter, not for primary location searches)
                state: OPTIONAL - Filter results to this state (2-letter code like "CA", only for filtering)
                categories: OPTIONAL - Filter by Wikipedia category names (rarely needed)
                size: OPTIONAL - Number of results (1-50, default 10)
                search_type: OPTIONAL - "hybrid" (default, recommended), "semantic" (AI-based), or "text" (keyword matching)
                
            Examples:
                - General search: query="Victorian architecture San Francisco"
                - Topic search: query="Golden Gate Bridge history"
                - Filtered search: query="parks", city="Oakland", state="CA"
                
            Returns:
                Wikipedia articles with summaries, topics, and location information
            """
            try:
                return await wikipedia_tools.search_wikipedia(
                    self._create_context(),
                    query=query,
                    search_in=search_in,
                    city=city,
                    state=state,
                    categories=categories,
                    size=size,
                    search_type=search_type
                )
            except Exception as e:
                logger.error(f"Wikipedia search failed: {e}")
                return {"error": str(e), "query": query}
        
        # Wikipedia by location tool
        @self.app.tool(
            name="search_wikipedia_by_location",
            description="Find Wikipedia articles about a SPECIFIC CITY or neighborhood. PREFERRED for location searches.",
            tags={"wikipedia", "location", "city", "neighborhood"}
        )
        async def search_wikipedia_by_location(
            city: str,
            state: Optional[str] = None,
            query: Optional[str] = None,
            size: int = 10
        ) -> Dict[str, Any]:
            """Find Wikipedia articles about a SPECIFIC CITY or neighborhood.
            
            PREFERRED TOOL for location-based searches when you KNOW the city name.
            This tool is optimized for finding information about neighborhoods, landmarks,
            attractions, and local context for a specific city.
            
            USE THIS TOOL WHEN:
            - You have a specific city name (e.g., "Oakland", "San Francisco")
            - You want information about a neighborhood (e.g., "Temescal" in Oakland)
            - You need local context about an area
            
            Args:
                city: REQUIRED - City or neighborhood name (e.g., "Oakland", "Temescal", "San Francisco")
                state: OPTIONAL - State code for disambiguation (e.g., "CA", "NY", "TX") - only needed if city name is ambiguous
                query: OPTIONAL - Additional search terms to refine results (e.g., "restaurants", "parks", "history")
                size: OPTIONAL - Number of results (1-20, default 10)
                
            Examples:
                - Neighborhood info: city="Oakland", query="Temescal neighborhood amenities culture"
                - City overview: city="San Francisco", state="CA"
                - Local attractions: city="Berkeley", query="attractions landmarks"
                
            Returns:
                Wikipedia articles specifically about the requested location with local information,
                landmarks, neighborhoods, and cultural context
            """
            try:
                return await wikipedia_tools.search_wikipedia_by_location(
                    self._create_context(),
                    city=city,
                    state=state,
                    query=query,
                    size=size
                )
            except Exception as e:
                logger.error(f"Location Wikipedia search failed: {e}")
                return {"error": str(e), "city": city}
        
        # Health check tool
        @self.app.tool(
            name="health_check",
            description="Check the health status of all system components.",
            tags={"system", "health", "monitoring"}
        )
        async def health_check() -> Dict[str, Any]:
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
        
        # Neighborhood search tools
        @self.app.tool(
            name="search_neighborhoods",
            description="Search for neighborhoods and related information using Wikipedia data.",
            tags={"neighborhood", "search", "wikipedia", "location"}
        )
        async def search_neighborhoods(
            query: Optional[str] = None,
            city: Optional[str] = None,
            state: Optional[str] = None,
            include_statistics: bool = False,
            include_related_properties: bool = False,
            include_related_wikipedia: bool = False,
            size: int = 10
        ) -> Dict[str, Any]:
            """Search for neighborhoods and related information.
            
            This tool searches Wikipedia articles categorized as neighborhoods, districts, or communities.
            It can optionally include aggregated property statistics and related entities.
            
            Args:
                query: Optional text query for neighborhood search
                city: Filter by city name
                state: Filter by state name
                include_statistics: Include aggregated property statistics
                include_related_properties: Include related property listings
                include_related_wikipedia: Include related Wikipedia articles
                size: Number of results to return (1-50, default 10)
                
            Returns:
                Dict containing NeighborhoodSearchResponse with neighborhood results and metadata
            """
            try:
                return await neighborhood_tools.search_neighborhoods(
                    self._create_context(),
                    query=query,
                    city=city,
                    state=state,
                    include_statistics=include_statistics,
                    include_related_properties=include_related_properties,
                    include_related_wikipedia=include_related_wikipedia,
                    size=size
                )
            except Exception as e:
                logger.error(f"Neighborhood search failed: {e}")
                return {"error": str(e), "query": query}
        
        @self.app.tool(
            name="search_neighborhoods_by_location",
            description="Search for neighborhoods in a specific city with property statistics.",
            tags={"neighborhood", "location", "statistics", "city"}
        )
        async def search_neighborhoods_by_location(
            city: str,
            state: Optional[str] = None,
            include_statistics: bool = True,
            size: int = 10
        ) -> Dict[str, Any]:
            """Search for neighborhoods in a specific city with property statistics.
            
            This is a convenience function for location-based neighborhood searches.
            It automatically includes property statistics for the discovered neighborhoods.
            
            Args:
                city: City name to search in (required)
                state: Optional state filter for disambiguation
                include_statistics: Include property statistics (default true)
                size: Number of results to return (1-20, default 10)
                
            Returns:
                Dict containing NeighborhoodSearchResponse with neighborhood results and statistics
            """
            try:
                return await neighborhood_tools.search_neighborhoods_by_location(
                    self._create_context(),
                    city=city,
                    state=state,
                    include_statistics=include_statistics,
                    size=size
                )
            except Exception as e:
                logger.error(f"Location-based neighborhood search failed: {e}")
                return {"error": str(e), "city": city}
        
        # Wikipedia article tool
        @self.app.tool(
            name="get_wikipedia_article",
            description="Get complete Wikipedia article details by page ID.",
            tags={"wikipedia", "article", "details"}
        )
        async def get_wikipedia_article(page_id: str) -> Dict[str, Any]:
            """Get complete Wikipedia article details by page ID.
            
            Args:
                page_id: Wikipedia page ID
                
            Returns:
                Complete Wikipedia article information
            """
            try:
                return await wikipedia_tools.get_wikipedia_article(
                    self._create_context(),
                    page_id=page_id
                )
            except Exception as e:
                logger.error(f"Get Wikipedia article failed: {e}")
                return {"error": str(e), "page_id": page_id}
        
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
            "property_search_service": self.property_search_service,
            "wikipedia_search_service": self.wikipedia_search_service,
            "neighborhood_search_service": self.neighborhood_search_service,
            "health_check_service": self.health_check_service
        })
    
    def start(self, transport: str = None, host: str = None, port: int = None):
        """Start the MCP server.
        
        Args:
            transport: Transport mode override - if None, uses config
            host: Host override - if None, uses config
            port: Port override - if None, uses config
        """
        # Use config values if not overridden
        transport = transport or self.config.transport.mode
        host = host or self.config.transport.host  
        port = port or self.config.transport.port
        
        logger.info(f"Starting MCP server with {transport} transport")
        
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
            
            # Start FastMCP server with specified transport
            if transport == "http" or transport == "streamable-http":
                logger.info(f"Starting HTTP server on {host}:{port}")
                logger.info(f"MCP endpoint will be available at: http://{host}:{port}/mcp")
                self.app.run(transport="streamable-http", host=host, port=port)
            else:
                logger.info("Starting STDIO server")
                self.app.run(transport="stdio")
            
            logger.info(f"MCP server ready: {self.config.server_name} v{self.config.server_version}")
            
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


def print_startup_banner():
    """Print startup banner."""
    print("\n" + "="*60)
    print("🏠 Real Estate Search MCP Server")
    print("="*60)
    print("Starting Model Context Protocol server...")
    print("Configuration: Looking for config.yaml in multiple locations")
    print("-"*60)


def print_available_tools():
    """Print information about available tools."""
    print("\n📦 Available MCP Tools:")
    print("  • search_properties_with_filters - Property search with explicit filters")
    print("  • get_property_details - Get property details by ID")
    print("  • get_rich_property_details - Get rich property listing with embedded data")
    print("  • search_wikipedia - Search Wikipedia content")
    print("  • search_wikipedia_by_location - Location-based Wikipedia search")
    print("  • get_wikipedia_article - Get Wikipedia article by ID")
    print("  • search_neighborhoods - Search neighborhoods with optional statistics")
    print("  • search_neighborhoods_by_location - Location-based neighborhood search")
    print("  • health_check - Check system health status")
    print("-"*60)


def parse_arguments():
    """Parse command line arguments."""
    config_path = None
    transport = None
    host = None
    port = None
    
    args = sys.argv[1:]
    transport_explicitly_set = False
    i = 0
    
    while i < len(args):
        arg = args[i]
        if arg == "--transport" and i + 1 < len(args):
            transport = args[i + 1]
            transport_explicitly_set = True
            i += 2
        elif arg == "--host" and i + 1 < len(args):
            host = args[i + 1]
            i += 2
        elif arg == "--port" and i + 1 < len(args):
            try:
                port = int(args[i + 1])
            except ValueError:
                print(f"⚠️  Warning: Invalid port '{args[i + 1]}', using default")
            i += 2
        elif arg == "--config" and i + 1 < len(args):
            config_path = Path(args[i + 1])
            i += 2
        elif arg == "--help" or arg == "-h":
            print("Usage: python -m real_estate_search.mcp_server.main [options]")
            print("Options:")
            print("  --transport <stdio|http|streamable-http>  Transport mode")
            print("  --host <host>                            Host for HTTP server")
            print("  --port <port>                            Port for HTTP server")
            print("  --config <path>                          Path to config file")
            print("  --help, -h                               Show this help")
            sys.exit(0)
        elif not config_path and not arg.startswith("--"):
            config_path = Path(arg)
            i += 1
        else:
            print(f"⚠️  Warning: Unknown argument '{arg}'")
            i += 1
    
    # Validate config file
    if config_path and not config_path.exists():
        print(f"⚠️  Warning: Config file not found at {config_path}")
        config_path = None
    elif config_path:
        print(f"✅ Using config file: {config_path}")
    else:
        # Look for config in default locations
        possible_configs = [
            Path(__file__).parent / "config.yaml",
            Path.cwd() / "config.yaml"
        ]
        for cfg in possible_configs:
            if cfg.exists():
                config_path = cfg
                print(f"✅ Found config file: {config_path}")
                break
    
    return config_path, transport, host, port, transport_explicitly_set


def main():
    """Main entry point."""
    print_startup_banner()
    
    config_path, transport, host, port, transport_explicitly_set = parse_arguments()
    
    try:
        # Initialize the server
        print("\n🚀 Initializing MCP Server...")
        server = MCPServer(config_path)
        
        print(f"✅ Server initialized: {server.config.server_name} v{server.config.server_version}")
        print(f"📡 Elasticsearch: {server.config.elasticsearch.url}")
        print(f"🧠 Embedding provider: {server.config.embedding.provider}")
        print(f"🚀 Transport: {server.config.transport.mode} (config)")
        
        if server.config.transport.mode in ["http", "streamable-http"]:
            print(f"🌐 HTTP Server: http://{server.config.transport.host}:{server.config.transport.port}/mcp")
        
        print_available_tools()
        
        print("\n✨ MCP Server is ready!")
        print("="*60)
        if server.config.transport.mode in ["http", "streamable-http"]:
            print(f"\nHTTP server starting on http://{server.config.transport.host}:{server.config.transport.port}/mcp")
            print("Press Ctrl+C to stop.\n")
        else:
            print("\nSTDIO server is running. Press Ctrl+C to stop.\n")
        
        # Start the server with appropriate transport
        if transport_explicitly_set and transport == "stdio":
            server.start(transport="stdio")
        elif len(sys.argv) == 1:
            server.start()
        else:
            server.start(transport=transport, host=host, port=port)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Received shutdown signal...")
        if 'server' in locals():
            asyncio.run(server.stop())
        print("👋 MCP Server stopped gracefully.")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        print("\nTroubleshooting tips:")
        print("1. Ensure Elasticsearch is running on localhost:9200")
        print("2. Check that API keys are set in environment variables or .env file")
        print("3. Verify config.yaml exists and is valid")
        print("4. Run with DEBUG=true for more details")
        print("\nTo start Elasticsearch:")
        print("  docker run -d -p 9200:9200 -e 'discovery.type=single-node' \\")
        print("    -e 'xpack.security.enabled=false' elasticsearch:8.11.0")
        sys.exit(1)


if __name__ == "__main__":
    main()