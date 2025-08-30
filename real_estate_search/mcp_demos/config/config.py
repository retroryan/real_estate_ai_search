"""Configuration management for MCP demos using Pydantic and YAML."""

from typing import Literal, Optional
from pathlib import Path
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class TransportType(str, Enum):
    """Available transport types for MCP connection."""
    
    STDIO = "stdio"
    HTTP = "http"


class StdioConfig(BaseModel):
    """Configuration for stdio transport."""
    
    server_path: Path = Field(
        default=Path("start_mcp_server.py"),
        description="Path to the MCP server script"
    )
    python_executable: Optional[str] = Field(
        default=None,
        description="Python executable to use (defaults to sys.executable)"
    )
    startup_timeout: int = Field(
        default=5,
        description="Timeout in seconds for server startup"
    )
    
    @field_validator('server_path')
    @classmethod
    def validate_server_path(cls, v: Path) -> Path:
        """Convert to absolute path if relative."""
        if not v.is_absolute():
            # Try to resolve relative to project root
            project_root = Path(__file__).parent.parent.parent
            absolute_path = project_root / v
            if absolute_path.exists():
                return absolute_path
        return v


class HttpConfig(BaseModel):
    """Configuration for HTTP transport."""
    
    base_url: str = Field(
        default="http://localhost:8000/mcp",
        description="Base URL for MCP HTTP endpoint"
    )
    timeout: int = Field(
        default=30,
        description="Request timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts"
    )
    verify_ssl: bool = Field(
        default=True,
        description="Whether to verify SSL certificates"
    )


class ConnectionConfig(BaseModel):
    """General connection configuration."""
    
    request_timeout: int = Field(
        default=60,
        description="Timeout for individual MCP requests in seconds"
    )
    init_timeout: int = Field(
        default=10,
        description="Timeout for client initialization in seconds"
    )
    enable_logging: bool = Field(
        default=True,
        description="Enable detailed logging for debugging"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level"
    )


class MCPConfig(BaseModel):
    """Main configuration for MCP demo client."""
    
    # Transport selection
    transport: TransportType = Field(
        default=TransportType.STDIO,
        description="Transport type to use for MCP connection"
    )
    
    # Transport-specific configs
    stdio: StdioConfig = Field(
        default_factory=StdioConfig,
        description="Configuration for stdio transport"
    )
    http: HttpConfig = Field(
        default_factory=HttpConfig,
        description="Configuration for HTTP transport"
    )
    
    # Connection settings
    connection: ConnectionConfig = Field(
        default_factory=ConnectionConfig,
        description="General connection configuration"
    )
    
    # Demo settings
    demo_mode: bool = Field(
        default=True,
        description="Enable demo mode with extra output"
    )
    rich_output: bool = Field(
        default=True,
        description="Use rich console for formatted output"
    )
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "MCPConfig":
        """Load configuration from YAML file.
        
        Args:
            yaml_path: Path to YAML configuration file
            
        Returns:
            Configured MCPConfig instance
        """
        import yaml
        
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls(**data)
    
    def get_transport_config(self) -> BaseModel:
        """Get the active transport configuration.
        
        Returns:
            Transport-specific configuration
        """
        if self.transport == TransportType.STDIO:
            return self.stdio
        else:
            return self.http
    
    def to_yaml(self, yaml_path: Path):
        """Save configuration to YAML file.
        
        Args:
            yaml_path: Path to save YAML configuration
        """
        import yaml
        
        data = self.model_dump(exclude_none=True)
        with open(yaml_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def load_config(config_path: Optional[Path] = None) -> MCPConfig:
    """Load configuration from YAML file or use defaults.
    
    Args:
        config_path: Optional path to YAML configuration file
        
    Returns:
        Loaded MCPConfig instance
    """
    if config_path and config_path.exists():
        if config_path.suffix in ['.yaml', '.yml']:
            return MCPConfig.from_yaml(config_path)
        elif config_path.suffix == '.json':
            import json
            with open(config_path, 'r') as f:
                data = json.load(f)
            return MCPConfig(**data)
    
    # Return default configuration
    return MCPConfig()


def get_default_config() -> MCPConfig:
    """Get default configuration instance.
    
    Returns:
        Default MCPConfig with standard settings
    """
    return MCPConfig()