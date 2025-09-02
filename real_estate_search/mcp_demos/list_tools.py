"""Simple tool discovery script for MCP server.

Lists all available tools with complete metadata including descriptions and parameters.
"""

import asyncio
from typing import Dict, Any, List
from pathlib import Path
from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
import json

from fastmcp import Client

from .client.client_factory import create_client_from_config
from .config.config import load_config


class ToolInfo(BaseModel):
    """Information about a discovered tool."""
    
    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters schema")


class ToolDiscovery(BaseModel):
    """Results from tool discovery."""
    
    tools: List[ToolInfo] = Field(default_factory=list)
    total_count: int = Field(default=0)
    server_name: str = Field(default="MCP Server")
    discovery_time_ms: float = Field(default=0)


async def discover_tools() -> ToolDiscovery:
    """Discover all available tools from the MCP server.
    
    Returns:
        ToolDiscovery with all tool information
    """
    import time
    start_time = time.time()
    
    discovery = ToolDiscovery()
    
    # Load config and create client
    config_path = Path(__file__).parent / "config.yaml"
    config = load_config(config_path)
    
    # Create configured client
    mcp_client = create_client_from_config(config)
    
    # Build transport based on config
    if config.transport == "stdio":
        transport = mcp_client._build_stdio_transport()
    else:
        transport = mcp_client._build_http_transport()
    
    # Connect and get tools
    async with Client(transport) as client:
        if not client.is_connected():
            raise Exception("Failed to connect to MCP server")
        
        # Get server info if available
        try:
            server_info = await client.get_server_info()
            if server_info and hasattr(server_info, 'name'):
                discovery.server_name = server_info.name
        except:
            pass  # Server info not critical
        
        # Get all tools
        tools = await client.list_tools()
        
        for tool in tools:
            # Extract tool information
            tool_info = ToolInfo(
                name=tool.name,
                description=tool.description or "No description available",
                parameters={}
            )
            
            # Parse input schema if available
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                schema = tool.inputSchema
                if isinstance(schema, dict):
                    tool_info.parameters = schema
                elif hasattr(schema, 'model_dump'):
                    tool_info.parameters = schema.model_dump()
                else:
                    tool_info.parameters = {"raw": str(schema)}
            
            discovery.tools.append(tool_info)
        
        discovery.total_count = len(discovery.tools)
        discovery.discovery_time_ms = (time.time() - start_time) * 1000
    
    return discovery


def display_tools(discovery: ToolDiscovery):
    """Display discovered tools in a formatted table.
    
    Args:
        discovery: Tool discovery results
    """
    console = Console()
    
    # Header
    console.print(Panel.fit(
        f"[bold cyan]MCP Tool Discovery - {discovery.server_name}[/bold cyan]\n"
        f"[dim]Found {discovery.total_count} tools in {discovery.discovery_time_ms:.1f}ms[/dim]",
        border_style="cyan"
    ))
    
    # Create table
    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("#", style="cyan", no_wrap=True, width=3)
    table.add_column("Tool Name", style="green", width=30)
    table.add_column("Description", style="yellow")
    table.add_column("Parameters", style="blue")
    
    for idx, tool in enumerate(discovery.tools, 1):
        # Format parameters
        params_str = ""
        if tool.parameters:
            if "properties" in tool.parameters:
                # Standard JSON schema format
                props = tool.parameters.get("properties", {})
                required = tool.parameters.get("required", [])
                param_list = []
                for name, schema in props.items():
                    param_type = schema.get("type", "any")
                    is_required = name in required
                    req_marker = "*" if is_required else ""
                    param_list.append(f"{name}{req_marker}: {param_type}")
                params_str = "\n".join(param_list)
            else:
                # Raw display
                params_str = json.dumps(tool.parameters, indent=2)[:200]
                if len(json.dumps(tool.parameters)) > 200:
                    params_str += "..."
        else:
            params_str = "No parameters"
        
        table.add_row(
            str(idx),
            tool.name,
            tool.description,
            params_str
        )
    
    console.print(table)
    
    # Footer with details
    console.print("\n[dim]* = required parameter[/dim]")
    console.print("[dim]Use individual tools via the MCP client for detailed operations[/dim]")


async def main():
    """Main entry point for tool discovery."""
    console = Console()
    
    try:
        console.print("[yellow]Discovering MCP server tools...[/yellow]\n")
        
        # Discover tools
        discovery = await discover_tools()
        
        # Display results
        display_tools(discovery)
        
        # Optional: Save to file for reference
        output_file = Path(__file__).parent / "discovered_tools.json"
        with open(output_file, "w") as f:
            json.dump(discovery.model_dump(), f, indent=2)
        
        console.print(f"\n[green]✓[/green] Tool discovery complete!")
        console.print(f"[dim]Results saved to: {output_file}[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error discovering tools: {e}[/red]")
        raise


if __name__ == "__main__":
    asyncio.run(main())