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
    from real_estate_search.mcp_server.tool_registry import ToolRegistry
    from real_estate_search.embeddings import QueryEmbeddingService
else:
    # Running as module
    from .settings import MCPServerConfig
    from .services.elasticsearch_client import ElasticsearchClient
    from ..search_service.properties import PropertySearchService
    from ..search_service.wikipedia import WikipediaSearchService
    from ..search_service.neighborhoods import NeighborhoodSearchService
    from .services.health_check import HealthCheckService
    from .utils.logging import setup_logging, get_logger
    from .tool_registry import ToolRegistry
    from ..embeddings import QueryEmbeddingService


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
        self.neighborhood_search_service: Optional[NeighborhoodSearchService] = None
        self.health_check_service: Optional[HealthCheckService] = None
        
        # Initialize FastMCP app
        self.app = FastMCP(self.config.server_name)
        
        # Initialize tool registry
        self.tool_registry = ToolRegistry(self.app)
    
    def _initialize_services(self):
        """Initialize all services."""
        logger.info("Initializing services")
        
        try:
            # Elasticsearch client
            self.es_client = ElasticsearchClient(self.config.elasticsearch)
            logger.info("Elasticsearch client initialized")
            
            # Embedding service - use config directly from AppConfig
            self.embedding_service = QueryEmbeddingService(config=self.config.embedding)
            self.embedding_service.initialize()  # Initialize the embedding model
            logger.info("Embedding service initialized")
            
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
        """Register MCP tools using ToolRegistry."""
        self.tool_registry.register_all_tools(self)
    
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
            
            # Register tools after services are initialized
            self._register_tools()
            
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
    print("  • search_properties - Natural language property search")
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