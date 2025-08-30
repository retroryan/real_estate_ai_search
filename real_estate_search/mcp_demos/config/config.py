"""Configuration for MCP demos."""

import os
from enum import Enum
from pathlib import Path
from typing import Optional, Union
from pydantic import BaseModel, Field


class TransportType(str, Enum):
    """Transport type enumeration."""
    STDIO = "stdio"
    HTTP = "http"


class MCPConfig(BaseModel):
    """Main MCP configuration - simplified."""
    transport: TransportType = Field(default=TransportType.HTTP)
    
    # HTTP settings (flat structure)
    base_url: str = Field(default="http://localhost:8000/mcp")
    timeout: int = Field(default=30)
    
    # STDIO settings (flat structure)
    server_module: str = Field(default="real_estate_search.mcp_server.main")
    
    # Display settings
    rich_output: bool = Field(default=True)
    
    # Legacy support - create nested objects when accessed
    @property
    def http(self):
        """Legacy HTTP config access."""
        from types import SimpleNamespace
        return SimpleNamespace(
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=3,
            verify_ssl=True
        )
    
    @property
    def stdio(self):
        """Legacy STDIO config access."""
        from types import SimpleNamespace
        return SimpleNamespace(
            server_module=self.server_module,
            python_executable=None,
            startup_timeout=5
        )
    
    @property
    def connection(self):
        """Legacy connection config access."""
        from types import SimpleNamespace
        return SimpleNamespace(
            request_timeout=60,
            init_timeout=10,
            enable_logging=True,
            log_level="INFO"
        )


def load_config(config_path: Optional[Path] = None) -> MCPConfig:
    """Load configuration from YAML file or use defaults.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        Loaded configuration
    """
    if config_path and config_path.exists():
        import yaml
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Allow environment variable override for transport
        transport_override = os.getenv('MCP_TRANSPORT')
        if transport_override:
            config_data['transport'] = transport_override
            
        return MCPConfig(**config_data)
    else:
        # Return default configuration (HTTP transport)
        return MCPConfig(transport=TransportType.HTTP)