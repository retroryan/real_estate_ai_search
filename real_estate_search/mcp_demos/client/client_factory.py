"""Factory for creating configured MCP clients."""

import sys
import logging
from typing import Optional
from pathlib import Path

from fastmcp import Client
from fastmcp.client import PythonStdioTransport
from pydantic import BaseModel

from ..config.config import MCPConfig, TransportType, load_config
from ..utils.mcp_utils import MCPClientWrapper, MCPResponse


class ConfiguredMCPClient(MCPClientWrapper):
    """MCP Client wrapper with configuration support."""
    
    def __init__(self, config: MCPConfig):
        """Initialize with configuration.
        
        Args:
            config: MCP configuration instance
        """
        self.config = config
        self._setup_logging()
        
        # Build transport based on configuration
        if config.transport == TransportType.STDIO:
            self.transport = self._build_stdio_transport()
        else:
            self.transport = self._build_http_transport()
    
    def _setup_logging(self):
        """Configure logging based on settings."""
        # Suppress verbose HTTP logs
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("mcp.client").setLevel(logging.WARNING)
        
        # Set up logger for this module only
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.WARNING)
    
    def _build_stdio_transport(self) -> PythonStdioTransport:
        """Build stdio transport from configuration.
        
        Returns:
            Configured PythonStdioTransport instance
        """
        # Resolve server path from simplified config
        server_path = self.config.server_path
        if not server_path.is_absolute():
            # Try to find it relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            server_path = project_root / server_path
            if not server_path.exists():
                # Fall back to original path
                server_path = self.config.server_path
        
        if self.logger:
            self.logger.info(f"Creating STDIO transport with server: {server_path}")
        
        # Use current Python interpreter
        python_cmd = sys.executable
        
        # Create the transport with stdio argument
        return PythonStdioTransport(
            str(server_path),
            python_cmd=python_cmd,
            args=["--transport", "stdio"]
        )
    
    def _build_http_transport(self) -> str:
        """Build HTTP transport configuration.
        
        Returns:
            HTTP URL for the MCP server
        """
        if self.logger:
            self.logger.info(f"Creating HTTP transport with URL: {self.config.base_url}")
        
        # For HTTP, FastMCP Client accepts the URL directly
        # FastMCP automatically detects HTTP transport from URL
        return self.config.base_url
    
    async def call_tool_with_config(
        self,
        tool_name: str,
        arguments: Optional[dict] = None
    ) -> MCPResponse:
        """Call a tool with configuration-based settings.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            MCPResponse with results
        """
        response = MCPResponse(success=False)
        
        try:
            # Build Client kwargs with simplified config
            client_kwargs = {
                "timeout": self.config.timeout,
                "init_timeout": 10  # Fixed reasonable default
            }
            
            # Create client with configuration
            async with Client(self.transport, **client_kwargs) as client:
                if not client.is_connected():
                    response.error = "Failed to connect to MCP server"
                    if self.logger:
                        self.logger.error(response.error)
                    return response
                
                if self.logger:
                    self.logger.debug(f"Calling tool: {tool_name} with args: {arguments}")
                
                # Call the tool
                result = await client.call_tool(tool_name, arguments=arguments or {})
                
                # Store raw content
                response.raw_content = result
                
                # Parse the content
                response.data = self.parse_mcp_content(result)
                response.success = True
                
                if self.logger:
                    self.logger.debug(f"Tool call successful: {tool_name}")
                
                return response
                
        except Exception as e:
            response.error = str(e)
            if self.logger:
                self.logger.error(f"Tool call failed: {tool_name} - {e}")
            return response
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[dict] = None
    ) -> MCPResponse:
        """Call a tool (delegates to config-aware method).
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            MCPResponse with results
        """
        return await self.call_tool_with_config(tool_name, arguments)


def create_client_from_config(
    config: Optional[MCPConfig] = None,
    config_path: Optional[Path] = None
) -> ConfiguredMCPClient:
    """Create an MCP client from configuration.
    
    Args:
        config: Optional MCPConfig instance
        config_path: Optional path to YAML configuration file
        
    Returns:
        Configured MCP client ready to use
    """
    if config is None:
        config = load_config(config_path)
    
    return ConfiguredMCPClient(config)


def create_stdio_client(
    server_path: Optional[Path] = None
) -> ConfiguredMCPClient:
    """Create a stdio transport client with minimal configuration.
    
    Args:
        server_path: Optional path to server script
        
    Returns:
        Configured MCP client using stdio transport
    """
    config = MCPConfig(transport=TransportType.STDIO)
    if server_path:
        config.stdio.server_path = server_path
    
    return ConfiguredMCPClient(config)


def create_http_client(
    base_url: str = "http://localhost:8000/mcp"
) -> ConfiguredMCPClient:
    """Create an HTTP transport client with minimal configuration.
    
    Args:
        base_url: URL of the MCP HTTP endpoint
        
    Returns:
        Configured MCP client using HTTP transport
    """
    config = MCPConfig(
        transport=TransportType.HTTP,
        http={"base_url": base_url}
    )
    
    return ConfiguredMCPClient(config)