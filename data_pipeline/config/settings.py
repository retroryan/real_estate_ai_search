"""
Simple configuration loading and management.

This module handles loading configuration from YAML files,
providing a centralized configuration management system for the pipeline.
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import ValidationError

from data_pipeline.config.pipeline_config import PipelineConfig

# Try to import dotenv, but don't fail if it's not available
try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

logger = logging.getLogger(__name__)


class ConfigurationManager:
    """Simple configuration manager for pipeline settings."""
    
    def __init__(self, config_path: Optional[str] = None, environment: Optional[str] = None, 
                 sample_size: Optional[int] = None, output_destinations: Optional[str] = None,
                 output_path: Optional[str] = None, cores: Optional[int] = None,
                 embedding_provider: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration YAML file.
            environment: Environment name (development, staging, production)
            sample_size: Number of records to sample from each source
            output_destinations: Comma-separated list of output destinations
            output_path: Custom output directory path
            cores: Number of cores to use
            embedding_provider: Embedding provider override
        """
        self.config_path = self._resolve_config_path(config_path)
        self.environment = environment or "development"
        self.sample_size = sample_size
        self.output_destinations_override = output_destinations
        self.output_path_override = output_path
        self.cores_override = cores
        self.embedding_provider_override = embedding_provider
        self._config: Optional[PipelineConfig] = None
        self._raw_config: Optional[Dict[str, Any]] = None
    
    def _substitute_env_vars(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively substitute environment variables in configuration.
        
        Supports ${VAR_NAME} syntax for environment variable substitution.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            Configuration with environment variables substituted
        """
        def substitute_value(value):
            if isinstance(value, str):
                # Find all ${VAR_NAME} patterns
                pattern = re.compile(r'\$\{([^}]+)\}')
                matches = pattern.findall(value)
                
                for var_name in matches:
                    env_value = os.environ.get(var_name)
                    if env_value is not None:
                        value = value.replace(f'${{{var_name}}}', env_value)
                    else:
                        logger.warning(f"Environment variable {var_name} not found, keeping placeholder")
                
                return value
            elif isinstance(value, dict):
                return {k: substitute_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_value(item) for item in value]
            else:
                return value
        
        return substitute_value(config_dict)
    
    def _resolve_config_path(self, config_path: Optional[str]) -> Path:
        """
        Resolve the configuration file path.
        
        Args:
            config_path: User-provided config path
            
        Returns:
            Resolved Path object
        """
        if config_path:
            path = Path(config_path)
        else:
            # Try default locations
            possible_paths = [
                Path("data_pipeline/config.yaml"),
                Path("config.yaml"),  # Current directory
            ]
            
            for possible_path in possible_paths:
                if possible_path.exists():
                    path = possible_path
                    break
            else:
                # Use first default if none exist
                path = possible_paths[0]
        
        if not path.exists():
            logger.warning(f"Configuration file not found: {path}, will use defaults")
        
        return path
    
    def _load_env_file(self) -> None:
        """
        Load environment variables from .env file if it exists.
        
        Looks for .env in the parent directory (project root).
        """
        if not HAS_DOTENV:
            return
        
        # Look for .env in parent directory (project root)
        parent_env = Path(__file__).parent.parent.parent / ".env"
        if parent_env.exists():
            load_dotenv(parent_env, override=False)
            logger.info(f"Loaded environment variables from: {parent_env}")
        else:
            logger.debug(f"No .env file found at: {parent_env}")
    
    def load_config(self) -> PipelineConfig:
        """
        Load and validate configuration with argument overrides.
        
        Returns:
            Validated PipelineConfig object
        """
        if self._config is not None:
            return self._config
        
        # Load environment variables from .env file
        self._load_env_file()
        
        if self.config_path.exists():
            logger.info(f"Loading configuration from: {self.config_path}")
            
            try:
                with open(self.config_path, "r") as f:
                    self._raw_config = yaml.safe_load(f)
                
                # Substitute environment variables
                self._raw_config = self._substitute_env_vars(self._raw_config)
                
                # Apply direct argument overrides
                self._apply_argument_overrides()
                
                # Validate and create config object
                self._config = PipelineConfig(**self._raw_config)
                
            except yaml.YAMLError as e:
                logger.error(f"Failed to parse YAML configuration: {e}")
                raise
            except ValidationError as e:
                logger.error(f"Configuration validation failed: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error loading configuration: {e}")
                raise
        else:
            logger.info("Using default configuration")
            self._config = PipelineConfig()
            
            # Still apply argument overrides for default config
            if self.cores_override:
                self._config.master = f"local[{self.cores_override}]"
            if self.embedding_provider_override:
                self._config.provider = self.embedding_provider_override
            if self.output_path_override:
                self._config.path = self.output_path_override
            if self.output_destinations_override:
                self._config.enabled_destinations = self.output_destinations_override.split(",")
        
        logger.info(f"Configuration loaded successfully: {self._config.name} v{self._config.version}")
        logger.info(f"Environment: {self.environment}")
        
        # Log sample size if specified
        if self.sample_size:
            logger.info(f"Sample size set to: {self.sample_size} records per source")
        
        # Log embedding provider
        logger.info(f"Embedding provider: {self._config.provider}")
        
        return self._config
    
    def _apply_argument_overrides(self) -> None:
        """
        Apply direct argument overrides to configuration.
        """
        if not self._raw_config:
            self._raw_config = {}
        
        # Spark configuration from arguments
        if self.cores_override:
            self._raw_config["master"] = f"local[{self.cores_override}]"
        
        # Embedding configuration from arguments
        if self.embedding_provider_override:
            self._raw_config["provider"] = self.embedding_provider_override
        
        # Output configuration from arguments
        if self.output_path_override:
            self._raw_config["path"] = self.output_path_override
        
        # Output destinations configuration from arguments
        if self.output_destinations_override:
            destinations = self.output_destinations_override.split(",")
            self._raw_config["enabled_destinations"] = destinations
    
    def get_config(self) -> PipelineConfig:
        """
        Get the loaded configuration.
        
        Returns:
            PipelineConfig object
        """
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load_config() first.")
        return self._config
    
    def validate_for_production(self) -> bool:
        """
        Validate configuration for production use.
        
        Returns:
            True if configuration is production-ready
        """
        if self._config is None:
            return False
        
        issues = []
        
        # Check Spark configuration
        if self._config.master.startswith("local"):
            issues.append("Spark is configured for local mode")
        
        # Check data sources
        if not self._config.properties and not self._config.neighborhoods:
            issues.append("No data sources configured")
        
        # Check output configuration
        if not self._config.path:
            issues.append("No output path configured")
        
        # Check embedding configuration
        if self._config.provider == "mock":
            issues.append("Mock embedding provider should not be used in production")
        
        # Check development settings removed - no longer in config
        
        if issues:
            logger.warning(f"Configuration issues for production: {issues}")
            return False
        
        logger.info("Configuration validated for production use")
        return True
    
    def get_effective_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the effective configuration.
        
        Returns:
            Dictionary with configuration summary
        """
        if self._config is None:
            return {}
        
        return {
            "pipeline": {
                "name": self._config.name,
                "version": self._config.version,
                "environment": self.environment
            },
            "spark": {
                "master": self._config.master,
                "memory": self._config.memory
            },
            "embedding": {
                "provider": self._config.provider,
                "model": self._config.provider,
                "batch_size": self._config.batch_size
            },
            "output": {
                "format": self._config.format,
                "path": self._config.path
            },
            "destinations": {
                "enabled": self._config.enabled_destinations
            }
        }


def load_configuration(
    config_path: Optional[str] = None,
    environment: Optional[str] = None
) -> PipelineConfig:
    """
    Convenience function to load configuration.
    
    Args:
        config_path: Optional path to configuration file
        environment: Optional environment name
        
    Returns:
        Loaded and validated PipelineConfig
    """
    manager = ConfigurationManager(config_path, environment)
    return manager.load_config()


def create_test_configuration(
    provider: str = "mock"
) -> PipelineConfig:
    """
    Create a test configuration.
    
    Args:
        provider: Embedding provider to use
        
    Returns:
        Test configuration
    """
    config = PipelineConfig()
    
    # Use mock embeddings for speed
    config.provider = provider
    
    return config