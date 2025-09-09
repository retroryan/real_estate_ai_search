"""Configuration settings for MCP Server using Pydantic.

Uses AppConfig as the base configuration source with proper Pydantic models.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml

# Import configurations from the main app
from ..config import AppConfig, ElasticsearchConfig, LoggingConfig, SearchConfig, DSPyConfig
from ..embeddings.models import EmbeddingConfig


class TransportConfig(BaseModel):
    """Transport configuration for MCP server."""
    
    model_config = ConfigDict(
        extra='forbid',
        validate_default=True,
        validate_assignment=True
    )
    
    mode: Literal["stdio", "http", "streamable-http"] = Field(
        default="http",
        description="Transport mode"
    )
    host: str = Field(
        default="localhost",
        min_length=1,
        description="Host for HTTP transport"
    )
    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Port for HTTP transport"
    )


class MCPServerConfig(BaseSettings):
    """MCP Server configuration using Pydantic Settings.
    
    Combines MCP-specific settings with shared AppConfig settings.
    """
    
    model_config = SettingsConfigDict(
        env_prefix="MCP_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra='ignore',
        validate_default=True,
        validate_assignment=True
    )
    
    # MCP-specific settings
    server_name: str = Field(
        default="real-estate-search-mcp",
        min_length=1,
        description="Server name"
    )
    server_version: str = Field(
        default="0.1.0",
        pattern=r'^\d+\.\d+\.\d+$',
        description="Server version"
    )
    transport: TransportConfig = Field(
        default_factory=TransportConfig,
        description="Transport configuration"
    )
    debug: bool = Field(
        default=False,
        description="Debug mode"
    )
    
    # Placeholder fields - will be loaded from AppConfig
    elasticsearch: ElasticsearchConfig = Field(default=None)
    embedding: EmbeddingConfig = Field(default=None)
    search: SearchConfig = Field(default=None)
    logging: LoggingConfig = Field(default=None)
    dspy_config: DSPyConfig = Field(default=None)
    
    def __init__(self, **kwargs):
        """Initialize with AppConfig values."""
        # Load AppConfig first
        app_config = AppConfig.load()
        
        # Set default values from AppConfig if not provided
        if 'elasticsearch' not in kwargs:
            kwargs['elasticsearch'] = app_config.elasticsearch
        if 'embedding' not in kwargs:
            kwargs['embedding'] = app_config.embedding
        if 'search' not in kwargs:
            kwargs['search'] = app_config.search
        if 'logging' not in kwargs:
            kwargs['logging'] = app_config.logging
        if 'dspy_config' not in kwargs:
            kwargs['dspy_config'] = app_config.dspy_config
        if 'debug' not in kwargs:
            kwargs['debug'] = app_config.debug
        
        super().__init__(**kwargs)
    
    @classmethod
    def from_yaml(cls, config_path: Path) -> MCPServerConfig:
        """Load configuration from YAML file.
        
        Creates MCPServerConfig with YAML values for MCP-specific settings.
        Shared configurations still come from AppConfig.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            Configured MCPServerConfig instance
        """
        if not config_path.exists():
            return cls()
        
        with open(config_path, 'r') as f:
            yaml_data = yaml.safe_load(f) or {}
        
        # Create config with YAML data
        # Pydantic will validate and only use recognized fields
        return cls(
            server_name=yaml_data.get('server_name', 'real-estate-search-mcp'),
            server_version=yaml_data.get('server_version', '0.1.0'),
            transport=yaml_data.get('transport', {}),
            debug=yaml_data.get('debug', False)
        )
    
    @classmethod
    def from_env(cls) -> MCPServerConfig:
        """Load configuration from environment variables.
        
        Creates MCPServerConfig with environment values and AppConfig.
        
        Returns:
            Configured MCPServerConfig instance
        """
        return cls()
    
    @property
    def config(self) -> AppConfig:
        """Get a full AppConfig instance for compatibility.
        
        Some parts of the code expect a full AppConfig object.
        This creates one with our current settings.
        """
        # Create AppConfig directly without calling load() to avoid recursion
        from ..config.config import AppConfig as AppConfigClass
        return AppConfigClass(
            elasticsearch=self.elasticsearch,
            embedding=self.embedding,
            search=self.search,
            logging=self.logging,
            dspy_config=self.dspy_config,
            debug=self.debug
        )