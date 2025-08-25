"""Test FastMCP Client API."""

import asyncio
from fastmcp import FastMCP
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioTransport
import json


async def test_client_api():
    """Test the Client API response format."""
    # Create a simple server
    server = FastMCP("test-server")
    
    @server.tool
    def test_tool() -> dict:
        """Test tool."""
        return {"message": "Hello", "value": 42}
    
    # For testing, we'll use the direct call
    # In production, FastMCP handles the client connection
    result = test_tool()
    print(f"Direct result: {result}")
    
    # The actual MCP client would use ClientSession with transport
    # but for in-memory testing with FastMCP, we use the pattern from docs
    print("\nFor MCP testing, use the pattern from FastMCP docs:")
    print("- Create server with FastMCP")
    print("- Add tools with @server.tool")
    print("- Tools return data directly")
    print("- FastMCP handles MCP protocol conversion")


if __name__ == "__main__":
    asyncio.run(test_client_api())