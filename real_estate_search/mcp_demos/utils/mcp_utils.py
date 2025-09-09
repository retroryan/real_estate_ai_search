"""Utilities for working with FastMCP Client and MCP types."""

import json
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from fastmcp import Client
from fastmcp.client import PythonStdioTransport
from mcp.types import TextContent, ImageContent, AudioContent, EmbeddedResource
from pydantic import BaseModel, Field


class MCPResponse(BaseModel):
    """Standardized MCP response wrapper."""
    
    success: bool = Field(description="Whether the call was successful")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Parsed response data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    raw_content: Optional[List[Any]] = Field(default=None, description="Raw MCP content objects")


class MCPClientWrapper:
    """Wrapper for FastMCP Client with simplified interface."""
    
    def __init__(self, server_module: Optional[str] = None):
        """Initialize the MCP client wrapper.
        
        Args:
            server_module: Python module path for the MCP server
        """
        if server_module is None:
            server_module = "real_estate_search.mcp_server.main"
        
        self.server_module = server_module
        self.transport = PythonStdioTransport(self.server_module, python_path=[str(Path(__file__).parent.parent.parent)])
    
    @staticmethod
    def parse_mcp_content(content: List[Any]) -> Dict[str, Any]:
        """Parse MCP content objects to dictionary.
        
        Args:
            content: List of MCP content objects (TextContent, etc.)
            
        Returns:
            Parsed dictionary from the content
        """
        if not content:
            return {}
        
        # Handle TextContent (most common)
        if isinstance(content[0], TextContent):
            try:
                # Parse JSON from text content
                return json.loads(content[0].text)
            except json.JSONDecodeError:
                # Return as text if not JSON
                return {"text": content[0].text}
        
        # Handle other content types if needed
        if isinstance(content[0], ImageContent):
            return {"image": {"data": content[0].data, "mimeType": content[0].mimeType}}
        
        if isinstance(content[0], AudioContent):
            return {"audio": {"data": content[0].data, "mimeType": content[0].mimeType}}
        
        if isinstance(content[0], EmbeddedResource):
            return {"resource": str(content[0].resource)}
        
        # Fallback for unknown types
        return {"raw": str(content[0])}
    
    async def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> MCPResponse:
        """Call an MCP tool with simplified response handling.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments for the tool
            
        Returns:
            MCPResponse with parsed data
        """
        response = MCPResponse(success=False)
        
        try:
            async with Client(self.transport) as client:
                if not client.is_connected():
                    response.error = "Failed to connect to MCP server"
                    return response
                
                # Call the tool
                result = await client.call_tool(tool_name, arguments=arguments or {})
                
                # Store raw content
                response.raw_content = result
                
                # Parse the content
                response.data = self.parse_mcp_content(result)
                response.success = True
                
                return response
                
        except Exception as e:
            response.error = str(e)
            return response
    
    async def list_tools(self) -> List[str]:
        """Get list of available tool names.
        
        Returns:
            List of tool names
        """
        try:
            async with Client(self.transport) as client:
                if not client.is_connected():
                    return []
                
                tools = await client.list_tools()
                return [tool.name for tool in tools]
                
        except Exception:
            return []
    
    async def health_check(self) -> bool:
        """Check if the MCP server is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        response = await self.call_tool("health_check")
        return response.success and response.data and response.data.get("status") == "healthy"


def create_mcp_client(server_module: Optional[str] = None) -> MCPClientWrapper:
    """Factory function to create an MCP client wrapper.
    
    Args:
        server_module: Optional Python module path for the MCP server
        
    Returns:
        Configured MCPClientWrapper instance
    """
    return MCPClientWrapper(server_module)