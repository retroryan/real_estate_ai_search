"""Quick start test script for MCP client."""

import asyncio
from pathlib import Path
import sys

# Add parent of mcp_demos to path for proper imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_demos.client import create_stdio_client, create_client_from_config

async def test_connection():
    """Test basic MCP client connection."""
    
    print("="*60)
    print("MCP Client Quick Start Test")
    print("="*60)
    
    # Create client with default stdio transport
    print("\n1. Creating client...")
    client = create_stdio_client()
    print("✓ Client created")
    
    # Test 1: Health check
    print("\n2. Testing health check...")
    is_healthy = await client.health_check()
    print(f"✓ Server is {'healthy' if is_healthy else 'unhealthy'}")
    
    # Test 2: List available tools
    print("\n3. Listing available tools...")
    tools = await client.list_tools()
    print(f"✓ Found {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool}")
    
    # Test 3: Search properties (using new main tool)
    print("\n4. Searching properties with AI...")
    response = await client.call_tool(
        "search_properties",
        {"query": "modern home in Oakland", "size": 2}
    )
    
    if response.success:
        data = response.data
        print(f"✓ Found {data['total_results']} properties")
        for prop in data['properties'][:2]:
            print(f"  - {prop['address']['street']}: ${prop['price']:,}")
    else:
        print(f"✗ Error: {response.error}")
    
    # Test 4: Search Wikipedia
    # Test 4.5: Search properties with filters
    print("\n5. Searching properties with explicit filters...")
    response = await client.call_tool(
        "search_properties_with_filters",
        {
            "query": "home",
            "min_bedrooms": 3,
            "max_price": 800000,
            "city": "Oakland",
            "size": 2
        }
    )
    
    if response.success:
        data = response.data
        print(f"✓ Found {data.get('total_results', 'N/A')} filtered properties")
        if 'properties' in data:
            for prop in data['properties'][:2]:
                print(f"  - {prop['bedrooms']} bed: ${prop['price']:,}")
    else:
        print(f"✗ Error: {response.error}")
    
    print("\n6. Searching Wikipedia...")
    response = await client.call_tool(
        "search_wikipedia",
        {"query": "San Francisco history", "size": 2}
    )
    
    if response.success:
        data = response.data
        print(f"✓ Found {data['total_results']} articles")
        for article in data['articles'][:2]:
            print(f"  - {article['title']}")
    else:
        print(f"✗ Error: {response.error}")
    
    # Test 5: Search Wikipedia by location  
    print("\n7. Searching Wikipedia by location...")
    response = await client.call_tool(
        "search_wikipedia_by_location",
        {"city": "Oakland", "query": "Temescal neighborhood", "size": 2}
    )
    
    if response.success:
        data = response.data
        print(f"✓ Found location-specific articles")
        if 'articles' in data:
            for article in data['articles'][:2]:
                print(f"  - {article['title']}")
    else:
        print(f"✗ Error: {response.error}")
    
    print("\n" + "="*60)
    print("✓ All tests completed successfully!")
    print("="*60)


async def test_with_config():
    """Test client with YAML configuration."""
    
    print("\n\nTesting with YAML Configuration")
    print("="*60)
    
    # Load client from YAML config
    config_path = Path(__file__).parent / "config" / "config_stdio.yaml"
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


async def main():
    """Run all tests."""
    await test_connection()
    await test_with_config()


if __name__ == "__main__":
    asyncio.run(main())