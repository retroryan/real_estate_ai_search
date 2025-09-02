# MCP Client for Real Estate Search - Quick Start Guide

## Overview

This is a high-quality MCP (Model Context Protocol) client implementation for the Real Estate Search demo system. It uses FastMCP Client to connect to the MCP server and provides real Elasticsearch data for property and Wikipedia searches.

## Directory Structure

```
mcp_demos/
├── client/           # MCP client implementation
│   ├── client.py     # Main client with mock removal pending
│   └── client_factory.py # Configuration-based client factory
├── config/           # Configuration files
│   ├── config.py     # Pydantic configuration models
│   ├── config_stdio.yaml  # STDIO transport config
│   └── config_http.yaml   # HTTP transport config
├── demos/            # Demo scripts
│   ├── property_search.py
│   ├── wikipedia_search.py
│   └── ...
├── utils/            # Utility modules
│   ├── mcp_utils.py  # MCP client wrapper
│   └── models.py     # Pydantic data models
└── tests/            # Test scripts
```

## Quick Start

### 1. Prerequisites

Ensure you have:
- Python 3.10+
- Elasticsearch running on localhost:9200
- The MCP server script available at project root

### 2. Install Dependencies

```bash
pip install fastmcp pydantic pyyaml rich
```

### 3. Test the Client Connection

```python
# test_client.py
import asyncio
from pathlib import Path
import sys

# Add mcp_demos to path
sys.path.insert(0, 'real_estate_search/mcp_demos')

from client import create_stdio_client

async def test_connection():
    """Test basic MCP client connection."""
    
    # Create client with default stdio transport
    client = create_stdio_client()
    
    # Test 1: Health check
    print("Testing health check...")
    is_healthy = await client.health_check()
    print(f"✓ Server is {'healthy' if is_healthy else 'unhealthy'}")
    
    # Test 2: List available tools
    print("\nListing available tools...")
    tools = await client.list_tools()
    print(f"✓ Found {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool}")
    
    # Test 3: Search properties
    print("\nSearching properties...")
    response = await client.call_tool(
        "search_properties_tool",
        {"query": "modern home", "size": 2}
    )
    
    if response.success:
        data = response.data
        print(f"✓ Found {data['total_results']} properties")
        for prop in data['properties'][:2]:
            print(f"  - {prop['address']['street']}: ${prop['price']:,}")
    else:
        print(f"✗ Error: {response.error}")
    
    # Test 4: Search Wikipedia
    print("\nSearching Wikipedia...")
    response = await client.call_tool(
        "search_wikipedia_tool",
        {"query": "San Francisco", "size": 2}
    )
    
    if response.success:
        data = response.data
        print(f"✓ Found {data['total_results']} articles")
        for article in data['articles'][:2]:
            print(f"  - {article['title']}")
    else:
        print(f"✗ Error: {response.error}")

if __name__ == "__main__":
    asyncio.run(test_connection())
```

### 4. Using YAML Configuration

```python
# test_with_config.py
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, 'real_estate_search/mcp_demos')

from client import create_client_from_config

async def test_with_config():
    """Test client with YAML configuration."""
    
    # Load client from YAML config
    config_path = Path("real_estate_search/mcp_demos/config/config_stdio.yaml")
    client = create_client_from_config(config_path=config_path)
    
    print(f"Client configured with transport: {client.config.transport}")
    print(f"Demo mode: {client.config.demo_mode}")
    print(f"Log level: {client.config.connection.log_level}")
    
    # Perform a search
    response = await client.call_tool(
        "search_properties_tool",
        {"query": "luxury condo", "size": 3}
    )
    
    if response.success:
        print(f"\n✓ Search successful!")
        print(f"Total results: {response.data['total_results']}")
        print(f"Execution time: {response.data['execution_time_ms']}ms")
    else:
        print(f"\n✗ Search failed: {response.error}")

if __name__ == "__main__":
    asyncio.run(test_with_config())
```

## Configuration

### YAML Configuration Files

Two pre-configured YAML files are provided:

1. **config_stdio.yaml** - For local development
   - Uses subprocess communication
   - Connects to local MCP server

2. **config_http.yaml** - For network connections
   - Uses HTTP/HTTPS transport
   - For remote server access

### Configuration Options

```yaml
# Transport selection
transport: stdio  # or 'http'

# STDIO settings
stdio:
  server_module: real_estate_search.mcp_server.main
  startup_timeout: 5

# Connection settings  
connection:
  request_timeout: 60
  init_timeout: 10
  enable_logging: true
  log_level: INFO

# Demo settings
demo_mode: true
rich_output: true
```

## Available Tools

The MCP server provides these tools:

1. **search_properties_tool** - Search properties with natural language
2. **get_property_details_tool** - Get details for a specific property
3. **search_wikipedia_tool** - Search Wikipedia articles
4. **search_wikipedia_by_location_tool** - Location-based Wikipedia search
5. **health_check_tool** - Check system health status

## Testing Checklist

Run these tests to verify the client works correctly:

- [ ] **Connection Test**: Client connects to server
- [ ] **Health Check**: Server reports healthy status
- [ ] **Tool Discovery**: All 5 tools are listed
- [ ] **Property Search**: Returns real property data
- [ ] **Wikipedia Search**: Returns real article data
- [ ] **Error Handling**: Graceful handling of invalid requests
- [ ] **Configuration Loading**: YAML config loads correctly
- [ ] **Transport Selection**: Both stdio and http configs work

## Common Issues and Solutions

### Issue: "Failed to connect to MCP server"
**Solution**: Ensure the MCP server script exists at the path specified in config

### Issue: "No tools found"
**Solution**: Check that Elasticsearch is running on localhost:9200

### Issue: "Timeout during initialization"
**Solution**: Increase `init_timeout` in configuration

## Next Steps

1. **Run a Demo**: Try the demo scripts in the `demos/` directory
2. **Customize Configuration**: Modify YAML files for your needs
3. **Build Your Own**: Use the client to create custom searches

## API Reference

### Client Creation

```python
from client import create_stdio_client, create_client_from_config

# Simple stdio client
client = create_stdio_client()

# From YAML configuration
client = create_client_from_config(config_path=Path("config.yaml"))
```

### Tool Invocation

```python
# Call any MCP tool
response = await client.call_tool(tool_name, arguments)

# Check response
if response.success:
    data = response.data  # Parsed JSON data
else:
    error = response.error  # Error message
```

### Response Structure

All responses follow the MCPResponse model:
- `success`: Boolean indicating success/failure
- `data`: Parsed JSON data from server
- `error`: Error message if failed
- `raw_content`: Raw MCP content for debugging