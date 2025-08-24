"""
Configuration loading and management with data subsetting support.

This module handles loading configuration from YAML files and environment variables,
providing a centralized configuration management system for the pipeline with
advanced features like data subsetting and flexible embedding model selection.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import ValidationError

from data_pipeline.config.models import PipelineConfig


class ConfigurationManager:
    """Configuration manager with data subsetting and model selection."""
    
    def __init__(self, config_path: Optional[str] = None, environment: Optional[str] = None, 
                 sample_size: Optional[int] = None, output_destinations: Optional[str] = None,
                 output_path: Optional[str] = None, cores: Optional[int] = None,
                 embedding_provider: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration YAML file.
            environment: Environment name (development, staging, production)
            sample_size: Override sample size for data subsetting
            output_destinations: Comma-separated list of output destinations
            output_path: Custom output directory path
            cores: Number of cores to use
            embedding_provider: Embedding provider override
        """
        self.config_path = self._resolve_config_path(config_path)
        self.environment = environment or "development"
        self.sample_size_override = sample_size
        self.output_destinations_override = output_destinations
        self.output_path_override = output_path
        self.cores_override = cores
        self.embedding_provider_override = embedding_provider
        self._config: Optional[PipelineConfig] = None
        self._raw_config: Optional[Dict[str, Any]] = None
    
    def _resolve_config_path(self, config_path: Optional[str]) -> Path:
        """
        Resolve the configuration file path.
        
        Args:
            config_path: User-provided config path
            
        Returns:
            Resolved Path object
            
        Raises:
            FileNotFoundError: If config file doesn't exist
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
    
    def load_config(self) -> PipelineConfig:
        """
        Load and validate configuration with environment-specific overrides.
        
        Returns:
            Validated PipelineConfig object
            
        Raises:
            ValidationError: If configuration is invalid
            yaml.YAMLError: If YAML parsing fails
        """
        if self._config is not None:
            return self._config
        
        if self.config_path.exists():
            logger.info(f"Loading configuration from: {self.config_path}")
            
            try:
                with open(self.config_path, "r") as f:
                    self._raw_config = yaml.safe_load(f)
                
                # Apply direct argument overrides
                self._apply_argument_overrides()
                
                # Handle embedding model configuration
                self._configure_embedding_models()
                
                # Handle data subsetting configuration
                self._configure_data_subsetting()
                
                # Validate and create config object
                self._config = PipelineConfig(**self._raw_config)
                
                # Apply environment-specific overrides
                if hasattr(self._config, 'apply_environment_overrides'):
                    self._config.apply_environment_overrides(self.environment)
                    logger.info(f"Applied {self.environment} environment overrides")
                
                # Re-apply sample_size override if it was provided (takes precedence over environment)
                if self.sample_size_override is not None:
                    self._config.data_subset.enabled = True
                    self._config.data_subset.sample_size = self.sample_size_override
                
                logger.info(f"Configuration loaded successfully: {self._config.metadata.name} v{self._config.metadata.version}")
                logger.info(f"Environment: {self.environment}")
                
                # Log data subsetting status
                if self._config.data_subset.enabled:
                    logger.info(f"Data subsetting ENABLED: sample_size={self._config.data_subset.sample_size}")
                else:
                    logger.info("Data subsetting DISABLED - using full datasets")
                
                # Log embedding provider
                logger.info(f"Embedding provider: {self._config.embedding.provider}")
                
                return self._config
                
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
            return self._config
    
    def _apply_argument_overrides(self) -> None:
        """
        Apply direct argument overrides to configuration.
        
        Direct arguments take precedence over config file values.
        """
        if not self._raw_config:
            self._raw_config = {}
        
        # Spark configuration from arguments
        if self.cores_override:
            self._raw_config.setdefault("spark", {})["master"] = f"local[{self.cores_override}]"
        
        # Embedding configuration from arguments
        if self.embedding_provider_override:
            self._raw_config.setdefault("embedding", {})["provider"] = self.embedding_provider_override
        
        # Output configuration from arguments
        if self.output_path_override:
            self._raw_config.setdefault("output", {})["path"] = self.output_path_override
        
        # Output destinations configuration from arguments
        if self.output_destinations_override:
            destinations = self.output_destinations_override.split(",")
            self._raw_config.setdefault("output_destinations", {})["enabled_destinations"] = destinations
        
    
    
    def _configure_embedding_models(self) -> None:
        """
        Configure embedding models.
        """
        if not self._raw_config:
            return
        
        embedding_config = self._raw_config.get("embedding", {})
        
        # Handle models configuration
        if "models" in embedding_config:
            models = embedding_config["models"]
            
            # API keys should be provided directly in config or passed as arguments
            # No environment variable resolution needed
        
    
    def _configure_data_subsetting(self) -> None:
        """
        Configure data subsetting based on environment and flags.
        
        Automatically enables subsetting in development/test environments.
        """
        if not self._raw_config:
            return
        
        # Priority 1: Command-line sample_size override
        if self.sample_size_override is not None:
            if "data_subset" not in self._raw_config:
                self._raw_config["data_subset"] = {}
            self._raw_config["data_subset"]["enabled"] = True
            self._raw_config["data_subset"]["sample_size"] = self.sample_size_override
            return
        
        # Priority 2: Auto-enable subsetting in development/test modes
        if self.environment in ("development", "test"):
            if "data_subset" not in self._raw_config:
                self._raw_config["data_subset"] = {}
            
            # Set reasonable defaults for development
            if "enabled" not in self._raw_config["data_subset"]:
                self._raw_config["data_subset"]["enabled"] = True
            
            if "sample_size" not in self._raw_config["data_subset"]:
                self._raw_config["data_subset"]["sample_size"] = 20
        
        # Priority 3: Check for test mode flag
        if self._raw_config.get("development", {}).get("test_mode", False):
            if "data_subset" not in self._raw_config:
                self._raw_config["data_subset"] = {}
            
            self._raw_config["data_subset"]["enabled"] = True
            self._raw_config["data_subset"]["sample_size"] = self._raw_config.get("development", {}).get("test_record_limit", 10)
    
    def get_config(self) -> PipelineConfig:
        """
        Get the loaded configuration.
        
        Returns:
            PipelineConfig object
            
        Raises:
            RuntimeError: If configuration hasn't been loaded
        """
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load_config() first.")
        return self._config
    
    def reload_config(self) -> PipelineConfig:
        """
        Force reload configuration from file.
        
        Returns:
            Newly loaded PipelineConfig object
        """
        self._config = None
        self._raw_config = None
        return self.load_config()
    
    def save_config(self, path: Optional[str] = None) -> None:
        """
        Save current configuration to YAML file.
        
        Args:
            path: Output path. If None, overwrites original file.
        """
        if self._config is None:
            raise RuntimeError("No configuration to save")
        
        output_path = Path(path) if path else self.config_path
        
        logger.info(f"Saving configuration to: {output_path}")
        
        with open(output_path, "w") as f:
            yaml.safe_dump(
                self._config.model_dump(exclude_none=True),
                f,
                default_flow_style=False,
                sort_keys=False
            )
    
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
        if self._config.spark.master.startswith("local"):
            issues.append("Spark is configured for local mode")
        
        # Check data sources
        if not self._config.data_sources:
            issues.append("No data sources configured")
        
        # Check data subsetting
        if self._config.data_subset.enabled:
            issues.append("Data subsetting is enabled (should be disabled for production)")
        
        # Check output configuration
        if not self._config.output.path:
            issues.append("No output path configured")
        
        # Check embedding configuration
        if self._config.embedding.provider == "mock":
            issues.append("Mock embedding provider should not be used in production")
        
        # Check development settings
        if self._config.development.test_mode:
            issues.append("Test mode is enabled")
        
        if self._config.development.debug_mode:
            issues.append("Debug mode is enabled")
        
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
                "name": self._config.metadata.name,
                "version": self._config.metadata.version,
                "environment": self.environment
            },
            "spark": {
                "master": self._config.spark.master,
                "memory": self._config.spark.memory
            },
            "data_subsetting": {
                "enabled": self._config.data_subset.enabled,
                "sample_size": self._config.data_subset.sample_size if self._config.data_subset.enabled else "N/A",
                "method": self._config.data_subset.sample_method if self._config.data_subset.enabled else "N/A"
            },
            "embedding": {
                "provider": self._config.embedding.provider,
                "model": self._get_effective_model_name(),
                "batch_size": self._config.embedding.batch_size
            },
            "output": {
                "format": self._config.output.format,
                "path": self._config.output.path
            },
            "processing": {
                "quality_checks": self._config.processing.enable_quality_checks,
                "cache_enabled": self._config.processing.cache_intermediate_results,
                "parallel_tasks": self._config.processing.parallel_tasks
            }
        }
    
    def _get_effective_model_name(self) -> str:
        """Get the effective model name for the current provider."""
        if self._config.embedding.models:
            model_config = self._config.embedding.get_model_config()
            if model_config:
                return model_config.model
        
        # Default fallback
        return "default"


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
    sample_size: int = 10,
    provider: str = "mock"
) -> PipelineConfig:
    """
    Create a test configuration with minimal data.
    
    Args:
        sample_size: Number of records to sample
        provider: Embedding provider to use
        
    Returns:
        Test configuration
    """
    config = PipelineConfig()
    
    # Enable data subsetting
    config.data_subset.enabled = True
    config.data_subset.sample_size = sample_size
    
    # Use mock embeddings for speed
    config.embedding.provider = provider
    
    # Enable test mode
    config.development.test_mode = True
    config.development.test_record_limit = sample_size
    
    # Disable caching for tests
    config.processing.cache_intermediate_results = False
    
    return config