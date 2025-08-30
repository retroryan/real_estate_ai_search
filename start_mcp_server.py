#!/usr/bin/env python
"""Start the Real Estate MCP Server.

This script provides a convenient way to start the MCP server from the project root.
It handles module imports correctly and provides helpful startup messages.
"""

import sys
import asyncio
from pathlib import Path

# Add the current directory to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from real_estate_search.mcp_server.main import MCPServer


def print_startup_banner():
    """Print a nice startup banner."""
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
    print("  • search_wikipedia_tool - Search Wikipedia content")
    print("  • get_wikipedia_article_tool - Get Wikipedia article by ID")
    print("  • search_wikipedia_by_location_tool - Location-based Wikipedia search")
    print("  • health_check_tool - Check system health status")
    print("-"*60)


def run_server():
    """Run the MCP server."""
    print_startup_banner()
    
    # Check for config file argument
    config_path = None
    if len(sys.argv) > 1:
        config_path = Path(sys.argv[1])
        if not config_path.exists():
            print(f"⚠️  Warning: Config file not found at {config_path}")
            config_path = None
        else:
            print(f"✅ Using config file: {config_path}")
    else:
        # Look for config in default locations
        possible_configs = [
            Path("real_estate_search/mcp_server/config/config.yaml"),
            Path("mcp_server/config/config.yaml"),
            Path("config.yaml")
        ]
        for cfg in possible_configs:
            if cfg.exists():
                config_path = cfg
                print(f"✅ Found config file: {config_path}")
                break
    
    try:
        # Initialize the server
        print("\n🚀 Initializing MCP Server...")
        server = MCPServer(config_path)
        
        print(f"✅ Server initialized: {server.config.server_name} v{server.config.server_version}")
        print(f"📡 Elasticsearch: {server.config.elasticsearch.url}")
        print(f"🧠 Embedding provider: {server.config.embedding.provider}")
        
        print_available_tools()
        
        print("\n✨ MCP Server is ready!")
        print("="*60)
        print("\nServer is running. Press Ctrl+C to stop.\n")
        
        # Start the server (synchronous)
        server.start()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Received shutdown signal...")
        if 'server' in locals():
            # Stop is async, so run it in an event loop
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


def main():
    """Main entry point."""
    try:
        run_server()
    except KeyboardInterrupt:
        pass  # Handled in run_server


if __name__ == "__main__":
    main()