"""Test script for configuration system."""

import asyncio
from pathlib import Path
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp_demos.config import MCPConfig, TransportType, load_config
from mcp_demos.client import create_client_from_config, create_stdio_client


async def test_config_loading():
    """Test configuration loading from various sources."""
    print("Testing Configuration System")
    print("="*60)
    
    # Test 1: Default configuration
    print("\n1. Testing default configuration:")
    default_config = MCPConfig()
    print(f"   Transport: {default_config.transport}")
    print(f"   Demo mode: {default_config.demo_mode}")
    print(f"   Log level: {default_config.connection.log_level}")
    
    # Test 2: Load from YAML
    print("\n2. Testing YAML configuration:")
    yaml_path = Path(__file__).parent / "config_stdio.yaml"
    if yaml_path.exists():
        yaml_config = MCPConfig.from_yaml(yaml_path)
        print(f"   Transport: {yaml_config.transport}")
        print(f"   Server path: {yaml_config.stdio.server_path}")
        print(f"   Startup timeout: {yaml_config.stdio.startup_timeout}")
    else:
        print("   YAML file not found")
    
    # Test 3: Configuration validation
    print("\n3. Testing configuration validation:")
    try:
        # Valid config
        valid_config = MCPConfig(
            transport=TransportType.STDIO,
            connection={"request_timeout": 30}
        )
        print(f"   Valid config created: transport={valid_config.transport}")
        
        # Get transport-specific config
        transport_config = valid_config.get_transport_config()
        print(f"   Transport config type: {type(transport_config).__name__}")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: Environment variable loading
    print("\n4. Testing environment variable loading:")
    env_config = MCPConfig.from_env()
    print(f"   Transport from env: {env_config.transport}")
    print(f"   Demo mode from env: {env_config.demo_mode}")
    
    # Test 5: Save configuration to YAML
    print("\n5. Testing configuration export:")
    test_config = MCPConfig(
        transport=TransportType.HTTP,
        http={"base_url": "http://example.com/mcp"},
        demo_mode=False
    )
    export_path = Path(__file__).parent / "test_export.yaml"
    test_config.to_yaml(export_path)
    print(f"   Config exported to: {export_path}")
    
    # Clean up
    export_path.unlink()
    
    print("\n" + "="*60)
    print("Configuration tests completed!")


async def test_client_creation():
    """Test client creation with configuration."""
    print("\n\nTesting Client Factory")
    print("="*60)
    
    # Test 1: Create stdio client
    print("\n1. Creating STDIO client:")
    try:
        stdio_client = create_stdio_client()
        print(f"   Client created: {type(stdio_client).__name__}")
        print(f"   Transport type: {stdio_client.config.transport}")
        
        # Test connection
        is_healthy = await stdio_client.health_check()
        print(f"   Health check: {'✓ Healthy' if is_healthy else '✗ Not healthy'}")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Create client from YAML config
    print("\n2. Creating client from YAML:")
    yaml_path = Path(__file__).parent / "config_stdio.yaml"
    if yaml_path.exists():
        try:
            yaml_client = create_client_from_config(config_path=yaml_path)
            print(f"   Client created from: {yaml_path.name}")
            print(f"   Transport: {yaml_client.config.transport}")
            print(f"   Log level: {yaml_client.config.connection.log_level}")
            
            # Test tool listing
            tools = await yaml_client.list_tools()
            print(f"   Available tools: {len(tools)}")
            
        except Exception as e:
            print(f"   Error: {e}")
    
    print("\n" + "="*60)
    print("Client factory tests completed!")


async def test_tool_invocation():
    """Test tool invocation with configured client."""
    print("\n\nTesting Tool Invocation with Config")
    print("="*60)
    
    # Create client with configuration
    config = MCPConfig(
        transport=TransportType.STDIO,
        connection={
            "enable_logging": False,
            "request_timeout": 30
        },
        demo_mode=True
    )
    
    client = create_client_from_config(config)
    
    # Test property search
    print("\n1. Testing property search:")
    response = await client.call_tool(
        "search_properties_tool",
        {"query": "test property", "size": 1}
    )
    
    print(f"   Success: {response.success}")
    if response.data:
        print(f"   Results: {response.data.get('total_results', 0)} properties found")
    if response.error:
        print(f"   Error: {response.error}")
    
    print("\n" + "="*60)
    print("All tests completed!")


async def main():
    """Run all configuration tests."""
    await test_config_loading()
    await test_client_creation()
    await test_tool_invocation()


if __name__ == "__main__":
    asyncio.run(main())