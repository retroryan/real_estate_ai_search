"""Test the MCP utilities module."""

import asyncio
from pathlib import Path
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp_demos.utils.mcp_utils import create_mcp_client, MCPResponse


async def test_mcp_utils():
    """Test the MCP utilities."""
    print("Testing MCP Utilities")
    print("="*60)
    
    # Create client
    client = create_mcp_client()
    
    # Test 1: List tools
    print("\n1. Testing list_tools():")
    tools = await client.list_tools()
    print(f"   Found {len(tools)} tools: {tools[:3]}...")
    
    # Test 2: Health check
    print("\n2. Testing health_check():")
    is_healthy = await client.health_check()
    print(f"   Server healthy: {is_healthy}")
    
    # Test 3: Property search
    print("\n3. Testing property search:")
    response = await client.call_tool(
        "search_properties_tool",
        {"query": "modern home", "size": 2}
    )
    print(f"   Success: {response.success}")
    if response.data:
        print(f"   Found {response.data.get('total_results', 0)} properties")
        print(f"   Returned {response.data.get('returned_results', 0)} results")
    
    # Test 4: Wikipedia search
    print("\n4. Testing Wikipedia search:")
    response = await client.call_tool(
        "search_wikipedia_tool",
        {"query": "San Francisco", "size": 2}
    )
    print(f"   Success: {response.success}")
    if response.data:
        print(f"   Found {response.data.get('total_results', 0)} articles")
    
    # Test 5: Error handling
    print("\n5. Testing error handling:")
    response = await client.call_tool(
        "invalid_tool_name",
        {}
    )
    print(f"   Success: {response.success}")
    print(f"   Error: {response.error}")
    
    print("\n" + "="*60)
    print("All tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_mcp_utils())