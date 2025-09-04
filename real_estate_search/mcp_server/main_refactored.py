"""Refactored MCP server application with clean architecture."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

# Handle both module and script execution
if __name__ == "__main__" and __package__ is None:
    # Running as script, add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from real_estate_search.mcp_server.settings import MCPServerConfig
    from real_estate_search.mcp_server.services.elasticsearch_client import ElasticsearchClient
    from real_estate_search.embeddings import QueryEmbeddingService, EmbeddingConfig
    from real_estate_search.mcp_server.services.property_search import PropertySearchService
    from real_estate_search.mcp_server.services.wikipedia_search import WikipediaSearchService
    from real_estate_search.mcp_server.services.health_check import HealthCheckService
    from real_estate_search.mcp_server.utils.logging import setup_logging, get_logger
    from real_estate_search.mcp_server.tool_registry import ToolRegistry
    from real_estate_search.mcp_server.utils.context import ToolContext
    from real_estate_search.hybrid import HybridSearchEngine
else:
    # Running as module
    from .settings import MCPServerConfig
    from .services.elasticsearch_client import ElasticsearchClient
    from ..embeddings import QueryEmbeddingService, EmbeddingConfig
    from .services.property_search import PropertySearchService
    from .services.wikipedia_search import WikipediaSearchService
    from .services.health_check import HealthCheckService
    from .utils.logging import setup_logging, get_logger
    from .tool_registry import ToolRegistry
    from .utils.context import ToolContext
    from ..hybrid import HybridSearchEngine


logger = get_logger(__name__)


class MCPServer:
    """Real Estate Search MCP Server with clean architecture."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the MCP server.
        
        Args:
            config_path: Optional path to configuration file
        """
        # Load configuration
        self.config = self._load_configuration(config_path)
        
        # Setup logging
        setup_logging(self.config.logging)
        logger.info(f"Starting MCP Server {self.config.server_name} v{self.config.server_version}")
        
        # Initialize service containers
        self.services = ServiceContainer()
        
        # Initialize FastMCP app
        self.app = FastMCP(self.config.server_name)
        
        # Initialize tool registry
        self.tool_registry = ToolRegistry(self.app)
        
        # Register tools
        self.tool_registry.register_all_tools(self)
    
    def _load_configuration(self, config_path: Optional[Path]) -> MCPServerConfig:
        """Load server configuration.
        
        Args:
            config_path: Optional path to configuration file
            
        Returns:
            Loaded configuration
        """
        if config_path and config_path.exists():
            return MCPServerConfig.from_yaml(config_path)
        return MCPServerConfig.from_env()
    
    def _initialize_services(self):
        """Initialize all services with proper error handling."""
        logger.info("Initializing services")
        
        try:
            self.services.initialize_all(self.config)
            logger.info("All services initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise
    
    # Service accessors for backward compatibility
    @property
    def es_client(self):
        return self.services.es_client
    
    @property
    def embedding_service(self):
        return self.services.embedding_service
    
    @property
    def property_search_service(self):
        return self.services.property_search_service
    
    @property
    def wikipedia_search_service(self):
        return self.services.wikipedia_search_service
    
    @property
    def health_check_service(self):
        return self.services.health_check_service
    
    @property
    def hybrid_search_engine(self):
        return self.services.hybrid_search_engine
    
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
            self._perform_health_check()
            
            # Start server with specified transport
            self._start_server(transport, host, port)
            
            logger.info(f"MCP server ready: {self.config.server_name} v{self.config.server_version}")
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise
    
    def _perform_health_check(self):
        """Perform initial health check."""
        health_response = self.services.health_check_service.perform_health_check()
        
        if health_response.status == "unhealthy":
            logger.error("System is unhealthy, but starting anyway")
            logger.error(f"Health check details: {health_response.services}")
        else:
            logger.info(f"System health: {health_response.status}")
    
    def _start_server(self, transport: str, host: str, port: int):
        """Start the server with specified transport."""
        if transport in ["http", "streamable-http"]:
            logger.info(f"Starting HTTP server on {host}:{port}")
            logger.info(f"MCP endpoint will be available at: http://{host}:{port}/mcp")
            self.app.run(transport="streamable-http", host=host, port=port)
        else:
            logger.info("Starting STDIO server")
            self.app.run(transport="stdio")
    
    async def stop(self):
        """Stop the MCP server gracefully."""
        logger.info("Stopping MCP server")
        
        try:
            await self.services.close_all()
            logger.info("MCP server stopped")
        except Exception as e:
            logger.error(f"Error stopping server: {e}")


class ServiceContainer:
    """Container for all MCP server services."""
    
    def __init__(self):
        """Initialize empty service container."""
        self.es_client: Optional[ElasticsearchClient] = None
        self.embedding_service: Optional[QueryEmbeddingService] = None
        self.property_search_service: Optional[PropertySearchService] = None
        self.wikipedia_search_service: Optional[WikipediaSearchService] = None
        self.health_check_service: Optional[HealthCheckService] = None
        self.hybrid_search_engine: Optional[HybridSearchEngine] = None
    
    def initialize_all(self, config: MCPServerConfig):
        """Initialize all services.
        
        Args:
            config: Server configuration
        """
        # Elasticsearch client
        self.es_client = ElasticsearchClient(config.elasticsearch)
        logger.info("Elasticsearch client initialized")
        
        # Embedding service
        embedding_config = EmbeddingConfig()  # Uses defaults and loads API key from env
        self.embedding_service = QueryEmbeddingService(config=embedding_config)
        self.embedding_service.initialize()
        logger.info(f"Embedding service initialized with {embedding_config.provider}")
        
        # Search services
        self.property_search_service = PropertySearchService(
            config,
            self.es_client,
            self.embedding_service
        )
        logger.info("Property search service initialized")
        
        self.wikipedia_search_service = WikipediaSearchService(
            config,
            self.es_client,
            self.embedding_service
        )
        logger.info("Wikipedia search service initialized")
        
        # Health check service
        self.health_check_service = HealthCheckService(
            config,
            self.es_client
        )
        logger.info("Health check service initialized")
        
        # Hybrid search engine
        self.hybrid_search_engine = HybridSearchEngine(
            es_client=self.es_client.client,
            config=None  # Uses default AppConfig
        )
        logger.info("Hybrid search engine initialized")
    
    async def close_all(self):
        """Close all services gracefully."""
        if self.es_client:
            self.es_client.close()


# CLI utilities
class CLIInterface:
    """Command-line interface utilities."""
    
    @staticmethod
    def print_startup_banner():
        """Print startup banner."""
        print("\n" + "="*60)
        print("🏠 Real Estate Search MCP Server")
        print("="*60)
        print("Starting Model Context Protocol server...")
        print("Configuration: Looking for config.yaml in multiple locations")
        print("-"*60)
    
    @staticmethod
    def print_available_tools():
        """Print information about available tools."""
        print("\n📦 Available MCP Tools:")
        print("  • search_properties - ⭐ PREFERRED: Natural language property search with AI")
        print("  • search_properties_with_filters - Property search with explicit filters")
        print("  • get_property_details - Get property details by ID")
        print("  • get_rich_property_details - Get rich property listing with embedded data")
        print("  • search_wikipedia - Search Wikipedia content")
        print("  • search_wikipedia_by_location - Location-based Wikipedia search")
        print("  • health_check - Check system health status")
        print("-"*60)
    
    @staticmethod
    def print_error_tips():
        """Print troubleshooting tips."""
        print("\nTroubleshooting tips:")
        print("1. Ensure Elasticsearch is running on localhost:9200")
        print("2. Check that API keys are set in environment variables or .env file")
        print("3. Verify config.yaml exists and is valid")
        print("4. Run with DEBUG=true for more details")
        print("\nTo start Elasticsearch:")
        print("  docker run -d -p 9200:9200 -e 'discovery.type=single-node' \\")
        print("    -e 'xpack.security.enabled=false' elasticsearch:8.11.0")


class ArgumentParser:
    """Command-line argument parser."""
    
    @staticmethod
    def parse_arguments():
        """Parse command line arguments.
        
        Returns:
            Tuple of (config_path, transport, host, port, transport_explicitly_set)
        """
        config_path = None
        transport = None
        host = None
        port = None
        transport_explicitly_set = False
        
        args = sys.argv[1:]
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
                ArgumentParser.print_help()
                sys.exit(0)
            elif not config_path and not arg.startswith("--"):
                config_path = Path(arg)
                i += 1
            else:
                print(f"⚠️  Warning: Unknown argument '{arg}'")
                i += 1
        
        # Validate and find config file
        config_path = ArgumentParser.find_config_file(config_path)
        
        return config_path, transport, host, port, transport_explicitly_set
    
    @staticmethod
    def print_help():
        """Print help message."""
        print("Usage: python -m real_estate_search.mcp_server.main [options]")
        print("Options:")
        print("  --transport <stdio|http|streamable-http>  Transport mode")
        print("  --host <host>                            Host for HTTP server")
        print("  --port <port>                            Port for HTTP server")
        print("  --config <path>                          Path to config file")
        print("  --help, -h                               Show this help")
    
    @staticmethod
    def find_config_file(config_path: Optional[Path]) -> Optional[Path]:
        """Find configuration file.
        
        Args:
            config_path: Provided config path or None
            
        Returns:
            Valid config path or None
        """
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
        
        return config_path


def main():
    """Main entry point."""
    cli = CLIInterface()
    cli.print_startup_banner()
    
    parser = ArgumentParser()
    config_path, transport, host, port, transport_explicitly_set = parser.parse_arguments()
    
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
        
        cli.print_available_tools()
        
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
        cli.print_error_tips()
        sys.exit(1)


if __name__ == "__main__":
    main()