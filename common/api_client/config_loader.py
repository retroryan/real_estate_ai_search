"""Configuration loader for API clients."""

import os
from pathlib import Path
from typing import Dict, Any, Optional

import yaml
from pydantic import ValidationError as PydanticValidationError

from .config import APIClientConfig
from .exceptions import ValidationError


class ConfigLoader:
    """Utility class for loading API client configurations."""
    
    @staticmethod
    def load_from_yaml(
        file_path: Path, 
        client_name: str,
        env_prefix: Optional[str] = None
    ) -> APIClientConfig:
        """Load configuration from YAML file.
        
        Args:
            file_path: Path to YAML configuration file
            client_name: Name of the API client configuration section
            env_prefix: Optional prefix for environment variable overrides
            
        Returns:
            Validated API client configuration
            
        Raises:
            ValidationError: If configuration is invalid
            FileNotFoundError: If configuration file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        # Load YAML file
        try:
            with open(file_path, 'r') as f:
                yaml_data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML in {file_path}: {e}") from e
        
        # Get client-specific configuration
        client_config = yaml_data.get(client_name)
        if not client_config:
            raise ValidationError(
                f"No configuration found for client '{client_name}' in {file_path}"
            )
        
        # Apply environment variable overrides
        if env_prefix:
            client_config = ConfigLoader._apply_env_overrides(client_config, env_prefix)
        
        # Validate configuration
        try:
            return APIClientConfig(**client_config)
        except PydanticValidationError as e:
            raise ValidationError(f"Invalid configuration for {client_name}: {e}") from e
    
    @staticmethod
    def load_from_dict(config_data: Dict[str, Any]) -> APIClientConfig:
        """Load configuration from dictionary.
        
        Args:
            config_data: Configuration data
            
        Returns:
            Validated API client configuration
            
        Raises:
            ValidationError: If configuration is invalid
        """
        try:
            return APIClientConfig(**config_data)
        except PydanticValidationError as e:
            raise ValidationError(f"Invalid configuration: {e}") from e
    
    @staticmethod
    def _apply_env_overrides(config: Dict[str, Any], prefix: str) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration.
        
        Args:
            config: Original configuration
            prefix: Environment variable prefix (e.g., 'PROPERTY_API')
            
        Returns:
            Configuration with environment variable overrides applied
        """
        config = config.copy()
        
        # Override base_url
        env_base_url = os.getenv(f"{prefix}_BASE_URL")
        if env_base_url:
            config['base_url'] = env_base_url
        
        # Override timeout
        env_timeout = os.getenv(f"{prefix}_TIMEOUT")
        if env_timeout:
            try:
                config['timeout'] = int(env_timeout)
            except ValueError:
                pass  # Invalid timeout value, keep original
        
        return config