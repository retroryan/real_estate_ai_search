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
    from real_estate_search.mcp_server.settings import MCPServerConfig
    from real_estate_search.mcp_server.services.elasticsearch_client import ElasticsearchClient
    from real_estate_search.embeddings import QueryEmbeddingService, EmbeddingConfig
    from real_estate_search.mcp_server.services.property_search import PropertySearchService
    from real_estate_search.mcp_server.services.wikipedia_search import WikipediaSearchService
    from real_estate_search.mcp_server.services.natural_language_search import NaturalLanguageSearchService
    from real_estate_search.mcp_server.services.health_check import HealthCheckService
    from real_estate_search.mcp_server.utils.logging import setup_logging, get_logger
    from real_estate_search.mcp_server.tools.property_tools import search_properties, get_property_details, get_rich_property_details
    from real_estate_search.mcp_server.tools.wikipedia_tools import search_wikipedia, get_wikipedia_article, search_wikipedia_by_location
    from real_estate_search.mcp_server.tools.hybrid_search_tool import search_properties_hybrid
    from real_estate_search.hybrid import HybridSearchEngine
else:
    # Running as module
    from .settings import MCPServerConfig
    from .services.elasticsearch_client import ElasticsearchClient
    from ..embeddings import QueryEmbeddingService, EmbeddingConfig
    from .services.property_search import PropertySearchService
    from .services.wikipedia_search import WikipediaSearchService
    from .services.natural_language_search import NaturalLanguageSearchService
    from .services.health_check import HealthCheckService
    from .utils.logging import setup_logging, get_logger
    from .tools.property_tools import search_properties, get_property_details, get_rich_property_details
    from .tools.wikipedia_tools import search_wikipedia, get_wikipedia_article, search_wikipedia_by_location
    from .tools.hybrid_search_tool import search_properties_hybrid
    from ..hybrid import HybridSearchEngine


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
        self.embedding_service: Optional[QueryEmbeddingService] = None
        self.property_search_service: Optional[PropertySearchService] = None
        self.wikipedia_search_service: Optional[WikipediaSearchService] = None
        self.natural_language_search_service: Optional[NaturalLanguageSearchService] = None
        self.health_check_service: Optional[HealthCheckService] = None
        self.hybrid_search_engine: Optional[HybridSearchEngine] = None
        
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
            embedding_config = EmbeddingConfig()  # Uses defaults and loads API key from env
            self.embedding_service = QueryEmbeddingService(config=embedding_config)
            self.embedding_service.initialize()
            logger.info(f"Embedding service initialized with {embedding_config.provider}")
            
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
            
            self.natural_language_search_service = NaturalLanguageSearchService(
                self.config,
                self.es_client,
                self.embedding_service
            )
            logger.info("Natural language search service initialized")
            
            # Health check service
            self.health_check_service = HealthCheckService(
                self.config,
                self.es_client
            )
            logger.info("Health check service initialized")
            
            # Hybrid search engine
            self.hybrid_search_engine = HybridSearchEngine(
                es_client=self.es_client.client,
                config=None  # Uses default AppConfig
            )
            logger.info("Hybrid search engine initialized")
            
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
        
        # Rich property details tool
        @self.app.tool()
        async def get_rich_property_details_tool(
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
            return await get_rich_property_details(
                self._create_context(),
                listing_id=listing_id,
                include_wikipedia=include_wikipedia,
                include_neighborhood=include_neighborhood,
                wikipedia_limit=wikipedia_limit
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
        
        # Natural language semantic search tool
        @self.app.tool()
        async def natural_language_search_tool(
            query: str,
            search_type: str = "semantic",
            size: int = 10
        ) -> Dict[str, Any]:
            """Advanced natural language semantic search with AI embeddings.
            
            Perform sophisticated natural language search using AI embeddings that understand
            intent and context beyond simple keyword matching. Choose from different search types
            to explore semantic understanding capabilities.
            
            Args:
                query: Natural language query (e.g., "cozy family home near good schools")
                search_type: Type of search:
                    - "semantic": Pure AI embedding search (default)
                    - "examples": Run 5 diverse example queries to show capabilities
                    - "comparison": Compare semantic vs keyword search side-by-side
                size: Number of results to return (1-50, default 10)
                
            Returns:
                Advanced search results with AI-powered semantic understanding
            """
            if not self.natural_language_search_service:
                return {"error": "Natural language search service not initialized"}
            
            try:
                if __name__ == "__main__" and __package__ is None:
                    from real_estate_search.mcp_server.models.search import NaturalLanguageSearchRequest
                else:
                    from .models.search import NaturalLanguageSearchRequest
                
                request = NaturalLanguageSearchRequest(
                    query=query,
                    search_type=search_type,
                    size=size
                )
                
                return await self.natural_language_search_service.search(request)
            except Exception as e:
                logger.error(f"Natural language search failed: {e}")
                return {"error": str(e)}
        
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
        
        # Hybrid search tool
        @self.app.tool()
        async def search_properties_hybrid_tool(
            query: str,
            size: int = 10,
            include_location_extraction: bool = False
        ) -> Dict[str, Any]:
            """Search properties using hybrid search with location understanding.
            
            Advanced property search that combines semantic vector search, traditional text matching,
            and intelligent location extraction from natural language queries. Uses Elasticsearch's
            RRF (Reciprocal Rank Fusion) for optimal result ranking.
            
            Args:
                query: Natural language property search query (e.g., "luxury waterfront condo in San Francisco")
                size: Number of results to return (1-50, default 10)
                include_location_extraction: Include location extraction details in response (default false)
                
            Returns:
                Structured property results with hybrid relevance scores and execution metadata
            """
            return await search_properties_hybrid(
                self._create_context(),
                query=query,
                size=size,
                include_location_extraction=include_location_extraction
            )
        
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
            "natural_language_search_service": self.natural_language_search_service,
            "health_check_service": self.health_check_service,
            "hybrid_search_engine": self.hybrid_search_engine
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
    print("  • search_properties_tool - Natural language property search")
    print("  • get_property_details_tool - Get property details by ID")
    print("  • get_rich_property_details_tool - Get rich property listing with embedded data")
    print("  • search_wikipedia_tool - Search Wikipedia content")
    print("  • get_wikipedia_article_tool - Get Wikipedia article by ID")
    print("  • search_wikipedia_by_location_tool - Location-based Wikipedia search")
    print("  • natural_language_search_tool - Advanced AI semantic search with examples")
    print("  • health_check_tool - Check system health status")
    print("  • search_properties_hybrid_tool - Hybrid property search with location extraction")
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